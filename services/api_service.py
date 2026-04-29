"""
API Service - Replit backend ile iletişim modülü
Tüm HTTP isteklerini yönetir
"""

import requests
import json
import threading
import os
import tempfile
from kivy.app import App


def _normalize_base_url(raw_url):
    raw = (raw_url or "").strip().rstrip("/")
    if not raw:
        return "https://your-replit-app.replit.app/api"
    if raw.endswith("/api"):
        return raw
    return f"{raw}/api"


# Replit entegrasyonu icin:
# - PHYSIO_API_BASE_URL varsa onu kullanir
# - yoksa asagidaki varsayilan adres devreye girer
BASE_URL = _normalize_base_url(
    os.getenv("PHYSIO_API_BASE_URL", "https://your-replit-app.replit.app/api")
)


class APIService:
    """Singleton API servisi"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.token = None
            cls._instance.user = None
            cls._instance.local_exercises = []
            cls._instance.local_pose_data = {}
            cls._instance.local_video_paths = {}
            cls._instance._next_local_exercise_id = 1000
        return cls._instance
    
    def _get_headers(self):
        headers = {'Content-Type': 'application/json'}
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'
        return headers

    def test_connection(self, callback):
        """Replit backend baglantisini test et - callback(success, message)"""
        def _run():
            try:
                r = requests.get(
                    f"{BASE_URL}/health",
                    headers=self._get_headers(),
                    timeout=8
                )
                if r.status_code == 200:
                    callback(True, f"Baglanti basarili: {BASE_URL}")
                else:
                    callback(False, f"Baglanti var ama health={r.status_code}")
            except Exception as e:
                callback(False, f"Baglanti hatasi: {e}")

        threading.Thread(target=_run, daemon=True).start()

    def _is_assigned_to_user(self, assigned_patient_id, user_id):
        """Hasta atamasini id tip farklarina ragmen guvenli karsilastir."""
        if assigned_patient_id is None:
            return True
        if user_id is None:
            return False
        if assigned_patient_id == user_id:
            return True
        return str(assigned_patient_id) == str(user_id)

    def _is_exercise_visible_for_current_user(self, exercise):
        """
        Hasta tarafinda atamayi id ve isim uzerinden eslestir.
        Bazi ortamlarda id tip/format farki oldugundan isim fallback'i gerekir.
        """
        if not self.user:
            return True
        if self.user.get('role') != 'patient':
            return True
        # Demo modunda (lokal atama testi) hasta tum lokal atamalari gorebilsin.
        if isinstance(self.token, str) and self.token.startswith('demo_token'):
            return True

        assigned_id = exercise.get('assigned_patient_id')
        user_id = self.user.get('id')
        if self._is_assigned_to_user(assigned_id, user_id):
            return True

        assigned_name = (exercise.get('assigned_patient_name') or '').strip().lower()
        user_name = (self.user.get('name') or '').strip().lower()
        if assigned_name and user_name and assigned_name == user_name:
            return True

        return False
    
    # ─── AUTH ────────────────────────────────────────────────
    def login(self, email, password, callback):
        """Giriş yap - callback(success, data)"""
        def _run():
            try:
                r = requests.post(
                    f"{BASE_URL}/auth/login",
                    json={"email": email, "password": password},
                    headers=self._get_headers(),
                    timeout=10
                )
                data = r.json()
                if r.status_code == 200:
                    self.token = data.get('token') or data.get('access_token')
                    self.user = data.get('user')
                    callback(True, data)
                else:
                    callback(False, data.get('message', 'Giriş başarısız'))
            except Exception as e:
                callback(False, f"Bağlantı hatası: {str(e)}")
        
        threading.Thread(target=_run, daemon=True).start()
    
    def logout(self):
        self.token = None
        self.user = None
    
    # ─── EGZERSİZLER ─────────────────────────────────────────
    def get_exercises(self, callback):
        """Hastanın egzersiz listesini getir"""
        def _run():
            if self.local_exercises:
                items = list(self.local_exercises)
                if self.user and self.user.get('role') == 'patient':
                    items = [
                        ex for ex in items
                        if self._is_exercise_visible_for_current_user(ex)
                    ]
                callback(True, items)
                return
            try:
                r = requests.get(
                    f"{BASE_URL}/exercises",
                    headers=self._get_headers(),
                    timeout=10
                )
                if r.status_code == 200:
                    callback(True, r.json())
                else:
                    fallback = list(self.local_exercises)
                    if self.user and self.user.get('role') == 'patient':
                        fallback = [
                            ex for ex in fallback
                            if self._is_exercise_visible_for_current_user(ex)
                        ]
                    callback(False, fallback)
            except Exception:
                fallback = list(self.local_exercises)
                if self.user and self.user.get('role') == 'patient':
                    fallback = [
                        ex for ex in fallback
                        if self._is_exercise_visible_for_current_user(ex)
                    ]
                callback(False, fallback)
        
        threading.Thread(target=_run, daemon=True).start()
    
    def get_exercise_detail(self, exercise_id, callback):
        """Egzersiz detayını ve referans pose verilerini getir"""
        def _run():
            try:
                r = requests.get(
                    f"{BASE_URL}/exercises/{exercise_id}",
                    headers=self._get_headers(),
                    timeout=10
                )
                if r.status_code == 200:
                    callback(True, r.json())
                else:
                    callback(False, None)
            except Exception as e:
                callback(False, None)
        
        threading.Thread(target=_run, daemon=True).start()
    
    def get_exercise_video_url(self, exercise_id):
        """Egzersiz video URL'ini döndür"""
        return f"{BASE_URL}/exercises/{exercise_id}/video"

    def get_exercise_video_source(self, exercise_id, callback):
        """
        Egzersiz videosu kaynagini dondurur.
        callback(success, source_path_or_url, is_temp_file)
        """
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

            def _on_downloaded(success, downloaded_path):
                if success and downloaded_path:
                    callback(True, downloaded_path, True)
                else:
                    callback(False, None, False)

            self.download_exercise_video(ex_id, _on_downloaded)

        threading.Thread(target=_run, daemon=True).start()

    def download_exercise_video(self, exercise_id, callback):
        """Egzersiz referans videosunu indir - callback(success, local_path)"""
        def _run():
            try:
                url = self.get_exercise_video_url(exercise_id)
                r = requests.get(
                    url,
                    headers=self._get_headers(),
                    timeout=30,
                    stream=True
                )
                if r.status_code != 200:
                    callback(False, None)
                    return

                tmp_dir = tempfile.gettempdir()
                filename = f"exercise_{exercise_id}_reference.mp4"
                local_path = os.path.join(tmp_dir, filename)

                with open(local_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)

                callback(True, local_path)
            except Exception:
                callback(False, None)

        threading.Thread(target=_run, daemon=True).start()
    
    def get_exercise_pose_data(self, exercise_id, callback):
        """Doktorun kaydeddiği referans pose verilerini getir (JSON)"""
        def _run():
            local_pose = self.local_pose_data.get(int(exercise_id))
            if local_pose:
                callback(True, local_pose)
                return
            try:
                r = requests.get(
                    f"{BASE_URL}/exercises/{exercise_id}/pose-data",
                    headers=self._get_headers(),
                    timeout=15
                )
                if r.status_code == 200:
                    callback(True, r.json())
                else:
                    callback(False, None)
            except Exception:
                callback(False, None)
        
        threading.Thread(target=_run, daemon=True).start()
    
    # ─── SONUÇLAR ────────────────────────────────────────────
    def submit_session_result(self, exercise_id, result_data, callback):
        """
        Egzersiz seansı sonucunu gönder
        result_data = {
            'total_reps': int,
            'correct_reps': int,
            'accuracy_score': float,
            'duration_seconds': int,
            'joint_errors': dict,
            'completed_at': str (ISO datetime)
        }
        """
        def _run():
            for ex in self.local_exercises:
                if int(ex.get('id')) == int(exercise_id):
                    ex['status'] = 'completed'
                    ex['last_result'] = {
                        'accuracy_score': result_data.get('accuracy_score', 0),
                        'correct_reps': result_data.get('correct_reps', 0),
                        'total_reps': result_data.get('total_reps', 0),
                        'completed_at': result_data.get('completed_at'),
                    }
                    callback(True, {'ok': True, 'local': True})
                    return
            try:
                r = requests.post(
                    f"{BASE_URL}/exercises/{exercise_id}/results",
                    json=result_data,
                    headers=self._get_headers(),
                    timeout=15
                )
                if r.status_code in (200, 201):
                    callback(True, r.json())
                else:
                    callback(False, None)
            except Exception:
                callback(False, None)
        
        threading.Thread(target=_run, daemon=True).start()

    def get_doctor_assignments(self, callback):
        """Doktorun atadığı egzersizleri hasta ve durum bilgisiyle getir."""
        def _run():
            local_items = [ex for ex in self.local_exercises if ex.get('assigned_by') == 'doctor']
            if local_items:
                callback(True, local_items)
                return
            try:
                r = requests.get(
                    f"{BASE_URL}/doctor/assignments",
                    headers=self._get_headers(),
                    timeout=10
                )
                if r.status_code == 200:
                    callback(True, r.json())
                else:
                    callback(False, [])
            except Exception:
                callback(False, [])

        threading.Thread(target=_run, daemon=True).start()
    
    def get_progress(self, callback):
        """Hastanın ilerleme istatistiklerini getir"""
        def _run():
            try:
                r = requests.get(
                    f"{BASE_URL}/patient/progress",
                    headers=self._get_headers(),
                    timeout=10
                )
                if r.status_code == 200:
                    callback(True, r.json())
                else:
                    callback(False, {})
            except Exception as e:
                callback(False, {})
        
        threading.Thread(target=_run, daemon=True).start()
    
    # ─── DOKTOR PANELİ ───────────────────────────────────────
    def get_patients(self, callback):
        """Doktorun hasta listesini getir"""
        def _run():
            try:
                r = requests.get(
                    f"{BASE_URL}/doctor/patients",
                    headers=self._get_headers(),
                    timeout=10
                )
                if r.status_code == 200:
                    callback(True, r.json())
                else:
                    callback(False, [])
            except Exception as e:
                callback(False, [])
        
        threading.Thread(target=_run, daemon=True).start()
    
    def get_patient_results(self, patient_id, callback):
        """Belirli hastanın egzersiz sonuçlarını getir"""
        def _run():
            try:
                r = requests.get(
                    f"{BASE_URL}/doctor/patients/{patient_id}/results",
                    headers=self._get_headers(),
                    timeout=10
                )
                if r.status_code == 200:
                    callback(True, r.json())
                else:
                    callback(False, [])
            except Exception:
                callback(False, [])
        
        threading.Thread(target=_run, daemon=True).start()

    def create_exercise_from_video(self, exercise_payload, pose_sequence, video_path, callback):
        """Doktorun videodan oluşturduğu egzersizi lokal olarak hastaya atar."""
        def _run():
            try:
                ex_id = self._next_local_exercise_id
                self._next_local_exercise_id += 1

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
                self.local_pose_data[ex_id] = pose_sequence or []
                self.local_video_paths[ex_id] = video_path
                callback(True, exercise)
            except Exception as e:
                callback(False, str(e))

        threading.Thread(target=_run, daemon=True).start()


# Global singleton instance
api = APIService()
