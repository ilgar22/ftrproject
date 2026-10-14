"""
API Service — HTTP + kalici yerel depolama.
"""

import json
import os
import shutil
import threading
import tempfile

import requests

from services import local_store


def _normalize_base_url(raw_url):
    raw = (raw_url or '').strip().rstrip('/')
    if not raw:
        return None
    if raw.endswith('/api'):
        return raw
    return f'{raw}/api'


BASE_URL = _normalize_base_url(os.getenv('PHYSIO_API_BASE_URL', ''))


class APIService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_state()
        return cls._instance

    def _init_state(self):
        self.token = None
        self.user = None
        store = local_store.load()
        self.local_exercises = store.get('exercises', [])
        self.local_pose_data = store.get('pose_data', {})
        self.local_video_paths = store.get('video_paths', {})
        self.local_session_recordings = store.get('session_recordings', {})
        self._next_local_exercise_id = int(store.get('next_exercise_id', 1000))

    def _persist(self):
        local_store.save({
            'version': 1,
            'next_exercise_id': self._next_local_exercise_id,
            'exercises': self.local_exercises,
            'pose_data': self.local_pose_data,
            'video_paths': self.local_video_paths,
            'session_recordings': self.local_session_recordings,
        })

    def _get_headers(self):
        headers = {'Content-Type': 'application/json'}
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'
        return headers

    def is_online(self):
        return BASE_URL is not None

    def test_connection(self, callback):
        def _run():
            if not BASE_URL:
                callback(False, 'PHYSIO_API_BASE_URL ayarlanmadi — yerel mod aktif')
                return
            try:
                r = requests.get(f'{BASE_URL}/health', headers=self._get_headers(), timeout=8)
                if r.status_code == 200:
                    callback(True, f'Baglanti basarili: {BASE_URL}')
                else:
                    callback(False, f'Health check: HTTP {r.status_code}')
            except Exception as exc:
                callback(False, f'Baglanti hatasi: {exc}')
        threading.Thread(target=_run, daemon=True).start()

    def _is_assigned_to_user(self, assigned_patient_id, user_id):
        if assigned_patient_id is None:
            return True
        if user_id is None:
            return False
        return str(assigned_patient_id) == str(user_id)

    def _is_exercise_visible_for_current_user(self, exercise):
        if not self.user or self.user.get('role') != 'patient':
            return True
        if isinstance(self.token, str) and self.token.startswith('demo_token'):
            return True
        assigned_id = exercise.get('assigned_patient_id')
        user_id = self.user.get('id')
        if self._is_assigned_to_user(assigned_id, user_id):
            return True
        assigned_name = (exercise.get('assigned_patient_name') or '').strip().lower()
        user_name = (self.user.get('name') or '').strip().lower()
        return bool(assigned_name and user_name and assigned_name == user_name)

    def _filter_for_patient(self, items):
        if not self.user or self.user.get('role') != 'patient':
            return items
        return [ex for ex in items if self._is_exercise_visible_for_current_user(ex)]

    def _local_exercises_for_user(self):
        return self._filter_for_patient(list(self.local_exercises))

    # ─── AUTH ────────────────────────────────────────────────────────────────

    def login(self, email, password, callback):
        def _run():
            if not BASE_URL:
                callback(False, 'Sunucu adresi yok. Demo modunu kullanin.')
                return
            try:
                r = requests.post(
                    f'{BASE_URL}/auth/login',
                    json={'email': email, 'password': password},
                    headers=self._get_headers(),
                    timeout=10,
                )
                data = r.json()
                if r.status_code == 200:
                    self.token = data.get('token') or data.get('access_token')
                    self.user = data.get('user')
                    callback(True, data)
                else:
                    callback(False, data.get('message', 'Giris basarisiz'))
            except Exception as exc:
                callback(False, f'Baglanti hatasi: {exc}')
        threading.Thread(target=_run, daemon=True).start()

    def logout(self):
        self.token = None
        self.user = None

    # ─── EGZERSIZLER ─────────────────────────────────────────────────────────

    def get_exercises(self, callback):
        def _run():
            local = self._local_exercises_for_user()
            if local:
                callback(True, local)
                return
            if not BASE_URL:
                callback(True, [])
                return
            try:
                r = requests.get(f'{BASE_URL}/exercises', headers=self._get_headers(), timeout=10)
                if r.status_code == 200:
                    callback(True, r.json())
                else:
                    callback(True, local)
            except Exception:
                callback(True, local)
        threading.Thread(target=_run, daemon=True).start()

    def get_exercise_detail(self, exercise_id, callback):
        def _run():
            for ex in self.local_exercises:
                if int(ex.get('id')) == int(exercise_id):
                    callback(True, ex)
                    return
            if not BASE_URL:
                callback(False, None)
                return
            try:
                r = requests.get(
                    f'{BASE_URL}/exercises/{exercise_id}',
                    headers=self._get_headers(),
                    timeout=10,
                )
                callback(r.status_code == 200, r.json() if r.status_code == 200 else None)
            except Exception:
                callback(False, None)
        threading.Thread(target=_run, daemon=True).start()

    def get_exercise_video_url(self, exercise_id):
        return f'{BASE_URL}/exercises/{exercise_id}/video' if BASE_URL else ''

    def get_exercise_video_source(self, exercise_id, callback):
        def _run():
            try:
                ex_id = int(exercise_id)
            except Exception:
                callback(False, None, False)
                return
            local_path = self.local_video_paths.get(ex_id)
            if local_path and os.path.exists(local_path):
                callback(True, local_path, False)
                return
            if not BASE_URL:
                callback(False, None, False)
                return
            self.download_exercise_video(ex_id, lambda ok, path: callback(ok, path, bool(ok)))
        threading.Thread(target=_run, daemon=True).start()

    def download_exercise_video(self, exercise_id, callback):
        def _run():
            if not BASE_URL:
                callback(False, None)
                return
            try:
                url = self.get_exercise_video_url(exercise_id)
                r = requests.get(url, headers=self._get_headers(), timeout=30, stream=True)
                if r.status_code != 200:
                    callback(False, None)
                    return
                local_path = os.path.join(tempfile.gettempdir(), f'exercise_{exercise_id}_reference.mp4')
                with open(local_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                callback(True, local_path)
            except Exception:
                callback(False, None)
        threading.Thread(target=_run, daemon=True).start()

    def get_exercise_pose_data(self, exercise_id, callback):
        def _run():
            ex_id = int(exercise_id)
            if ex_id in self.local_pose_data:
                callback(True, self.local_pose_data[ex_id])
                return
            if not BASE_URL:
                callback(False, None)
                return
            try:
                r = requests.get(
                    f'{BASE_URL}/exercises/{exercise_id}/pose-data',
                    headers=self._get_headers(),
                    timeout=15,
                )
                callback(r.status_code == 200, r.json() if r.status_code == 200 else None)
            except Exception:
                callback(False, None)
        threading.Thread(target=_run, daemon=True).start()

    # ─── SONUCLAR ────────────────────────────────────────────────────────────

    def submit_session_result(self, exercise_id, result_data, callback):
        def _run():
            for ex in self.local_exercises:
                if int(ex.get('id')) != int(exercise_id):
                    continue
                recording_path = result_data.get('patient_recording_path')
                target = int(result_data.get('target_reps', ex.get('daily_reps', 0)))
                correct = int(result_data.get('correct_reps', 0))
                accuracy = float(result_data.get('accuracy_score', 0))
                passed = result_data.get('session_passed')
                if passed is None:
                    passed = correct >= target and accuracy >= 50.0
                ex['status'] = 'completed' if (passed and target > 0) else 'in_progress'
                if recording_path:
                    ex['patient_recording_path'] = recording_path
                    self.local_session_recordings[int(exercise_id)] = recording_path
                ex['last_result'] = {
                    'accuracy_score': accuracy,
                    'correct_reps': correct,
                    'total_reps': result_data.get('total_reps', 0),
                    'completed_at': result_data.get('completed_at'),
                    'patient_recording_path': recording_path,
                    'session_passed': passed,
                }
                self._persist()
                callback(True, {'ok': True, 'local': True, 'session_passed': passed})
                return
            if not BASE_URL:
                callback(False, None)
                return
            try:
                r = requests.post(
                    f'{BASE_URL}/exercises/{exercise_id}/results',
                    json=result_data,
                    headers=self._get_headers(),
                    timeout=15,
                )
                callback(r.status_code in (200, 201), r.json() if r.status_code in (200, 201) else None)
            except Exception:
                callback(False, None)
        threading.Thread(target=_run, daemon=True).start()

    def get_doctor_assignments(self, callback):
        def _run():
            items = [ex for ex in self.local_exercises if ex.get('assigned_by') == 'doctor']
            if items:
                callback(True, items)
                return
            if not BASE_URL:
                callback(True, [])
                return
            try:
                r = requests.get(f'{BASE_URL}/doctor/assignments', headers=self._get_headers(), timeout=10)
                callback(r.status_code == 200, r.json() if r.status_code == 200 else [])
            except Exception:
                callback(True, [])
        threading.Thread(target=_run, daemon=True).start()

    def get_progress(self, callback):
        def _run():
            stats = self._compute_local_progress()
            if stats:
                callback(True, stats)
                return
            if not BASE_URL:
                callback(True, stats)
                return
            try:
                r = requests.get(f'{BASE_URL}/patient/progress', headers=self._get_headers(), timeout=10)
                if r.status_code == 200:
                    callback(True, r.json())
                else:
                    callback(True, stats)
            except Exception:
                callback(True, stats)
        threading.Thread(target=_run, daemon=True).start()

    def _compute_local_progress(self):
        visible = self._local_exercises_for_user()
        if not visible:
            return {}
        completed = sum(1 for ex in visible if ex.get('status') == 'completed')
        accuracies = [
            float(ex['last_result']['accuracy_score'])
            for ex in visible
            if ex.get('last_result') and ex['last_result'].get('accuracy_score') is not None
        ]
        return {
            'total_sessions': sum(
                ex.get('last_result', {}).get('total_reps', 0) for ex in visible
            ),
            'weekly_streak': min(completed, 7),
            'avg_accuracy': int(sum(accuracies) / len(accuracies)) if accuracies else 0,
            'completed_today': completed,
        }

    # ─── DOKTOR ──────────────────────────────────────────────────────────────

    def get_patients(self, callback):
        def _run():
            if not BASE_URL:
                callback(True, [])
                return
            try:
                r = requests.get(f'{BASE_URL}/doctor/patients', headers=self._get_headers(), timeout=10)
                callback(r.status_code == 200, r.json() if r.status_code == 200 else [])
            except Exception:
                callback(True, [])
        threading.Thread(target=_run, daemon=True).start()

    def get_patient_results(self, patient_id, callback):
        def _run():
            results = [
                ex.get('last_result', {})
                for ex in self.local_exercises
                if self._is_assigned_to_user(ex.get('assigned_patient_id'), patient_id)
                and ex.get('last_result')
            ]
            if results:
                callback(True, results)
                return
            if not BASE_URL:
                callback(True, [])
                return
            try:
                r = requests.get(
                    f'{BASE_URL}/doctor/patients/{patient_id}/results',
                    headers=self._get_headers(),
                    timeout=10,
                )
                callback(r.status_code == 200, r.json() if r.status_code == 200 else [])
            except Exception:
                callback(True, [])
        threading.Thread(target=_run, daemon=True).start()

    def create_exercise_from_video(self, exercise_payload, pose_sequence, video_path, callback):
        def _run():
            try:
                ex_id = self._next_local_exercise_id
                self._next_local_exercise_id += 1

                data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'videos')
                os.makedirs(data_dir, exist_ok=True)
                dest = os.path.join(data_dir, f'exercise_{ex_id}.mp4')
                if video_path and os.path.exists(video_path):
                    if os.path.abspath(video_path) != os.path.abspath(dest):
                        shutil.copy2(video_path, dest)

                exercise = {
                    'id': ex_id,
                    'name': exercise_payload.get('name', 'Yeni Egzersiz'),
                    'daily_reps': int(exercise_payload.get('daily_reps', 10)),
                    'schedule': exercise_payload.get('schedule', 'Gunluk'),
                    'status': 'pending',
                    'description': exercise_payload.get('description', 'Doktor tarafindan yuklendi'),
                    'assigned_by': 'doctor',
                    'assigned_patient_id': exercise_payload.get('assigned_patient_id'),
                    'assigned_patient_name': exercise_payload.get('assigned_patient_name'),
                }
                self.local_exercises.insert(0, exercise)
                self.local_pose_data[ex_id] = pose_sequence or {'frames': [], 'profile': {}}
                self.local_video_paths[ex_id] = dest
                self._persist()
                callback(True, exercise)
            except Exception as exc:
                callback(False, str(exc))
        threading.Thread(target=_run, daemon=True).start()


api = APIService()
