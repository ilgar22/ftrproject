"""
Pose Engine v2 — MediaPipe + faz senkronlu referans karsilastirma.

Mimari:
  1. Referans videodan normalize edilmis hareket modeli
  2. Canli kare → aci + vektor ozellikleri
  3. Faz senkronu (ardisik kare, hileli atlama yok)
  4. Canli skor 0-100 (yumusatilmis)
  5. Tekrar yalnizca tam dongu + yuksek kalite ile sayilir
"""

import json
import os
import time
import urllib.request
from collections import deque
from types import SimpleNamespace

import cv2
import mediapipe as mp
import numpy as np

from services.rep_counter import DEBUG_REP, RepCounter, build_joint_model

# ─── MediaPipe Tasks API ─────────────────────────────────────────────────────
PoseLandmarker = mp.tasks.vision.PoseLandmarker
PoseLandmarkerOpts = mp.tasks.vision.PoseLandmarkerOptions
RunningMode = mp.tasks.vision.RunningMode
BaseOptions = mp.tasks.BaseOptions
MPImage = mp.Image
MPImageFormat = mp.ImageFormat

MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pose_landmarker.task')
MODEL_URL = (
    'https://storage.googleapis.com/mediapipe-models/'
    'pose_landmarker/pose_landmarker_lite/float16/latest/'
    'pose_landmarker_lite.task'
)

# ─── Sabitler ────────────────────────────────────────────────────────────────
class LM:
    NOSE = 0
    LEFT_SHOULDER = 11
    RIGHT_SHOULDER = 12
    LEFT_ELBOW = 13
    RIGHT_ELBOW = 14
    LEFT_WRIST = 15
    RIGHT_WRIST = 16
    LEFT_HIP = 23
    RIGHT_HIP = 24
    LEFT_KNEE = 25
    RIGHT_KNEE = 26
    LEFT_ANKLE = 27
    RIGHT_ANKLE = 28


JOINT_ANGLES = {
    'sol_dirsek': (LM.LEFT_SHOULDER, LM.LEFT_ELBOW, LM.LEFT_WRIST),
    'sag_dirsek': (LM.RIGHT_SHOULDER, LM.RIGHT_ELBOW, LM.RIGHT_WRIST),
    'sol_omuz': (LM.LEFT_ELBOW, LM.LEFT_SHOULDER, LM.LEFT_HIP),
    'sag_omuz': (LM.RIGHT_ELBOW, LM.RIGHT_SHOULDER, LM.RIGHT_HIP),
    'sol_kalca': (LM.LEFT_SHOULDER, LM.LEFT_HIP, LM.LEFT_KNEE),
    'sag_kalca': (LM.RIGHT_SHOULDER, LM.RIGHT_HIP, LM.RIGHT_KNEE),
    'sol_diz': (LM.LEFT_HIP, LM.LEFT_KNEE, LM.LEFT_ANKLE),
    'sag_diz': (LM.RIGHT_HIP, LM.RIGHT_KNEE, LM.RIGHT_ANKLE),
}

JOINT_NAMES_TR = {
    'sol_dirsek': 'Sol Dirsek', 'sag_dirsek': 'Sag Dirsek',
    'sol_omuz': 'Sol Omuz', 'sag_omuz': 'Sag Omuz',
    'sol_kalca': 'Sol Kalca', 'sag_kalca': 'Sag Kalca',
    'sol_diz': 'Sol Diz', 'sag_diz': 'Sag Diz',
}

POSE_CONNECTIONS = [
    (11, 12), (11, 13), (13, 15), (12, 14), (14, 16),
    (11, 23), (12, 24), (23, 24),
    (23, 25), (25, 27), (24, 26), (26, 28),
]

# Gorsel
COLOR_OK = (80, 220, 80)
COLOR_WARN = (0, 200, 255)
COLOR_ERROR = (0, 60, 255)
COLOR_BONE = (160, 160, 160)

# Esikler
ANGLE_OK = 14.0
ANGLE_WARN = 24.0
ANGLE_FAIL = 42.0
MIN_JOINTS = 4
LIVE_MATCH_MIN = 0.68
REP_PERFECT = 0.93
REP_CYCLE_QUALITY = 0.74
REP_MIN_JOINT = 0.58
SYNC_ADVANCE = 0.50
SYNC_LOOKAHEAD = 10
DISPLAY_SMOOTH = 0.50
REP_RESET = 0.42
COMPLETION_ACCURACY_MIN = 50.0
CYCLE_MIN_PROGRESS = 0.22


def _ensure_model():
    if os.path.exists(MODEL_PATH):
        return True
    print('[PoseEngine] Model indiriliyor...')
    try:
        urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
        return True
    except Exception as exc:
        print(f'[PoseEngine] Model indirilemedi: {exc}')
        return False


def calculate_angle(a, b, c):
    a, b, c = np.array(a), np.array(b), np.array(c)
    ba, bc = a - b, c - b
    cos_a = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-8)
    return float(np.degrees(np.arccos(np.clip(cos_a, -1.0, 1.0))))


def preprocess_frame(frame_bgr):
    """Hasta kamerasi ile ayni donusum — referans video ve yardimci onizleme icin."""
    frame = cv2.rotate(frame_bgr, cv2.ROTATE_90_CLOCKWISE)
    return cv2.flip(frame, 1)


def _frame_aspect(frame_shape):
    if not frame_shape or len(frame_shape) < 2:
        return 1.0
    height, width = float(frame_shape[0]), float(frame_shape[1])
    if height <= 0:
        return 1.0
    return width / height


def _point(landmark, aspect):
    return [landmark.x * aspect, landmark.y]


def extract_angles(landmarks, frame_shape=None, min_visibility=0.35):
    if not landmarks or len(landmarks) < 33:
        return {}
    aspect = _frame_aspect(frame_shape)
    angles = {}
    for name, (a_i, b_i, c_i) in JOINT_ANGLES.items():
        la, lb, lc = landmarks[a_i], landmarks[b_i], landmarks[c_i]
        va = getattr(la, 'visibility', 1.0) or 1.0
        vb = getattr(lb, 'visibility', 1.0) or 1.0
        vc = getattr(lc, 'visibility', 1.0) or 1.0
        if va > min_visibility and vb > min_visibility and vc > min_visibility:
            angles[name] = round(calculate_angle(
                _point(la, aspect), _point(lb, aspect), _point(lc, aspect)
            ), 2)
    return angles


def extract_visibility(landmarks):
    if not landmarks or len(landmarks) < 33:
        return {}
    visibility = {}
    for name, (a_i, b_i, c_i) in JOINT_ANGLES.items():
        vals = [
            getattr(landmarks[a_i], 'visibility', 1.0) or 0.0,
            getattr(landmarks[b_i], 'visibility', 1.0) or 0.0,
            getattr(landmarks[c_i], 'visibility', 1.0) or 0.0,
        ]
        visibility[name] = float(min(vals))
    return visibility


def _body_scale(landmarks, aspect=1.0):
    l_sh, r_sh = landmarks[LM.LEFT_SHOULDER], landmarks[LM.RIGHT_SHOULDER]
    l_hip, r_hip = landmarks[LM.LEFT_HIP], landmarks[LM.RIGHT_HIP]
    lhx, lhy = l_hip.x * aspect, l_hip.y
    rhx, rhy = r_hip.x * aspect, r_hip.y
    lsx, lsy = l_sh.x * aspect, l_sh.y
    rsx, rsy = r_sh.x * aspect, r_sh.y
    cx = (lhx + rhx) * 0.5
    cy = (lhy + rhy) * 0.5
    scale = max(float(np.hypot(lsx - rsx, lsy - rsy)), 1e-3)
    return cx, cy, scale


def extract_pose_vector(landmarks, frame_shape=None):
    """8 eklem merkezinin govde-normalize vektoru."""
    if not landmarks or len(landmarks) < 33:
        return []
    aspect = _frame_aspect(frame_shape)
    cx, cy, scale = _body_scale(landmarks, aspect)
    vec = []
    for _, (_, b_i, _) in JOINT_ANGLES.items():
        lm = landmarks[b_i]
        vis = float(getattr(lm, 'visibility', 1.0) or 1.0)
        if vis > 0.35:
            vec.extend([
                round(((lm.x * aspect) - cx) / scale, 4),
                round((lm.y - cy) / scale, 4),
            ])
        else:
            vec.extend([0.0, 0.0])
    return vec


def compare_poses(live_angles, ref_angles, live_vec, ref_vec):
    """
  0-1 arasi benzerlik.
  Ortalama + minimum eklem skoru + vektor kosinusu birlestirilir.
    """
    common = [j for j in JOINT_ANGLES if j in live_angles and j in ref_angles]
    if len(common) < MIN_JOINTS:
        return {'score': 0.0, 'mean': 0.0, 'min': 0.0, 'worst_joint': None, 'worst_diff': 0.0}

    scores = []
    worst_joint, worst_diff = None, 0.0
    for joint in common:
        diff = abs(float(live_angles[joint]) - float(ref_angles[joint]))
        if diff >= ANGLE_FAIL:
            s = 0.0
        elif diff <= ANGLE_OK:
            s = 1.0
        elif diff <= ANGLE_WARN:
            s = 1.0 - (diff - ANGLE_OK) / (ANGLE_WARN - ANGLE_OK) * 0.35
        else:
            s = 0.65 - (diff - ANGLE_WARN) / (ANGLE_FAIL - ANGLE_WARN) * 0.65
        scores.append(max(0.0, s))
        if diff > worst_diff:
            worst_diff = diff
            worst_joint = joint

    mean_s = float(np.mean(scores))
    min_s = float(min(scores))
    vec_s = 0.0
    if live_vec and ref_vec and len(live_vec) == len(ref_vec):
        a = np.array(live_vec, dtype=np.float32)
        b = np.array(ref_vec, dtype=np.float32)
        na, nb = np.linalg.norm(a), np.linalg.norm(b)
        if na > 1e-6 and nb > 1e-6:
            vec_s = float(np.clip(np.dot(a, b) / (na * nb), 0.0, 1.0))

    combined = (mean_s * 0.45) + (min_s * 0.40) + (vec_s * 0.15)
    return {
        'score': round(float(np.clip(combined, 0.0, 1.0)), 4),
        'mean': round(mean_s, 4),
        'min': round(min_s, 4),
        'worst_joint': worst_joint,
        'worst_diff': round(worst_diff, 1),
    }


def build_feedback(live_angles, ref_angles, match):
    feedback, joint_status = [], {}
    for joint in JOINT_ANGLES:
        if joint not in live_angles or joint not in ref_angles:
            continue
        diff = abs(live_angles[joint] - ref_angles[joint])
        if diff >= ANGLE_FAIL:
            status = 'error'
            feedback.append(
                f"{JOINT_NAMES_TR[joint]}: {diff:.0f} derece sapma"
            )
        elif diff >= ANGLE_WARN:
            status = 'warning'
            feedback.append(
                f"{JOINT_NAMES_TR[joint]}: doktor gibi yap ({diff:.0f} derece)"
            )
        else:
            status = 'ok'
        joint_status[joint] = status
    if match['score'] < LIVE_MATCH_MIN and not feedback:
        feedback.append('Hareketi doktor videosu ile ayni yapin')
    return feedback, joint_status


class PoseEngine:
    """Canli pose analizi. Tekrar sayimi RepCounter ile yapilir."""

    _reference_cache = {}

    def __init__(self):
        self._landmarker = None
        self._last_landmarks = None
        self._video_ts_ms = 0
        self._smooth_alpha = 0.62
        self._no_detection_streak = 0
        self._max_hold_frames = 5

        self.reference_sequence = []
        self.reference_profile = {}
        self.rep_counter = RepCounter()

        self.rep_count = 0
        self.total_attempts = 0
        self.correct_reps = 0
        self.frame_count = 0
        self.skip_frames = 1

        self._display_ema = 0.0
        self.joint_error_counts = {j: 0 for j in JOINT_ANGLES}
        self.error_history = deque(maxlen=100)
        self.current_feedback = []
        self.live_pipeline_steps = []

        self.exercise_mode = 'reference'
        self._replay_time = None
        self._replay_dt = 0.0
        self._init_landmarker()

    # ─── Kurulum ─────────────────────────────────────────────────────────────

    def _init_landmarker(self):
        if not _ensure_model():
            return
        try:
            opts = PoseLandmarkerOpts(
                base_options=BaseOptions(model_asset_path=MODEL_PATH),
                running_mode=RunningMode.VIDEO,
                num_poses=1,
                min_pose_detection_confidence=0.5,
                min_pose_presence_confidence=0.5,
                min_tracking_confidence=0.45,
            )
            self._landmarker = PoseLandmarker.create_from_options(opts)
            print('[PoseEngine] v2 hazir.')
        except Exception as exc:
            print(f'[PoseEngine] Baslatilamadi: {exc}')

    def set_exercise_mode(self, mode='reference'):
        self.exercise_mode = mode or 'reference'

    def has_reference(self):
        return self.rep_counter.configured and len(self.reference_sequence) >= 8

    def clear_reference(self):
        self.reference_sequence = []
        self.reference_profile = {}
        self.rep_counter = RepCounter()
        self.rep_count = 0
        self.correct_reps = 0
        self.total_attempts = 0

    @classmethod
    def get_cached_reference(cls, exercise_id):
        if exercise_id is None:
            return None
        return cls._reference_cache.get(int(exercise_id))

    @classmethod
    def cache_reference(cls, exercise_id, payload):
        if exercise_id is None or not payload:
            return
        cls._reference_cache[int(exercise_id)] = payload

    def reference_frame_count(self):
        return len(self.reference_sequence)

    # ─── Referans yukleme ────────────────────────────────────────────────────

    def load_reference_from_json(self, data):
        try:
            if isinstance(data, str):
                data = json.loads(data)
            if isinstance(data, dict):
                self.reference_sequence = data.get('frames', [])
                self.reference_profile = data.get('profile', {})
                profiles = data.get('rep_profile') or []
                stable = data.get('stable_profile') or []
            else:
                self.reference_sequence = data or []
                self.reference_profile = {}
                profiles = []
                stable = []
            if not self.reference_profile:
                self.reference_profile = self._build_profile(self.reference_sequence)
            if not profiles:
                profiles = self.reference_profile.get('rep_profile') or []
                stable = self.reference_profile.get('stable_profile') or stable
            if not profiles:
                profiles, stable = build_joint_model(
                    self._tracks_from_sequence(self.reference_sequence),
                    len(self.reference_sequence),
                )
            self.rep_counter.configure(profiles, stable)
            self.rep_count = 0
            self.correct_reps = 0
            self.total_attempts = 0
            return self.has_reference()
        except Exception:
            return False

    def extract_reference_from_video(self, video_path, callback_progress=None):
        if not self._landmarker:
            return {'frames': [], 'profile': {}}
        self._last_landmarks = None
        cap = cv2.VideoCapture(video_path)
        try:
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        except Exception:
            pass
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1
        sequence, frame_idx = [], 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            frame = preprocess_frame(frame)
            lms = self._detect_landmarks(frame)
            if lms:
                angles = extract_angles(lms, frame.shape)
                if len(angles) >= MIN_JOINTS:
                    sequence.append({
                        'frame': frame_idx,
                        'angles': angles,
                        'pose_vector': extract_pose_vector(lms, frame.shape),
                    })
            if callback_progress:
                try:
                    callback_progress(frame_idx / total, frame_idx, total)
                except TypeError:
                    callback_progress(frame_idx / total)
            frame_idx += 1
        cap.release()
        self._last_landmarks = None
        profiles, stable = build_joint_model(self._tracks_from_sequence(sequence), len(sequence))
        self.reference_sequence = self._annotate_progress(sequence, profiles)
        self.reference_profile = self._build_profile(self.reference_sequence)
        self.reference_profile['rep_profile'] = profiles
        self.reference_profile['stable_profile'] = stable
        self.rep_counter.configure(profiles, stable)
        return {
            'frames': self.reference_sequence,
            'profile': self.reference_profile,
            'rep_profile': profiles,
            'stable_profile': stable,
        }

    def _build_profile(self, sequence):
        if not sequence:
            return {}
        tracks = {j: [] for j in JOINT_ANGLES}
        for item in sequence:
            for j, a in item.get('angles', {}).items():
                tracks.setdefault(j, []).append(float(a))
        ranges = {
            j: float(np.percentile(v, 90) - np.percentile(v, 10))
            for j, v in tracks.items() if len(v) >= 4
        }
        if not ranges:
            return {}
        rep_joint = max(ranges, key=ranges.get)
        vals = tracks[rep_joint]
        return {
            'rep_joint': rep_joint,
            'joint_ranges': {k: round(v, 2) for k, v in ranges.items()},
            'length': len(sequence),
            'rep_profile': build_joint_model(tracks, len(sequence))[0],
            'stable_profile': build_joint_model(tracks, len(sequence))[1],
        }

    @staticmethod
    def _tracks_from_sequence(sequence):
        tracks = {name: [] for name in JOINT_ANGLES}
        for item in sequence or []:
            for name, angle in item.get('angles', {}).items():
                tracks.setdefault(name, []).append(float(angle))
        return tracks

    @staticmethod
    def _annotate_progress(sequence, profiles):
        if not profiles:
            return sequence
        counter = RepCounter()
        counter.configure(profiles)
        for item in sequence:
            progress, _missing = counter.progress_of(item.get('angles', {}))
            item['progress'] = 0.0 if progress is None else round(float(progress), 4)
        return sequence

    def _frame_time(self):
        if self._replay_time is None:
            return time.monotonic()
        now = self._replay_time
        self._replay_time += self._replay_dt
        return now

    def _quality_against_reference(self, angles, pose_vec, progress):
        if not self.reference_sequence:
            return 0.0, [], {}
        best = min(
            self.reference_sequence,
            key=lambda item: abs(float(item.get('progress', 0.0)) - float(progress or 0.0)),
        )
        ref_angles = best.get('angles', {})
        match = compare_poses(angles, ref_angles, pose_vec, best.get('pose_vector', []))
        feedback, joint_status = build_feedback(angles, ref_angles, match)
        for joint, status in joint_status.items():
            if status == 'error':
                self.joint_error_counts[joint] += 1
        return match['score'], feedback, joint_status

    # ─── Canli isleme ────────────────────────────────────────────────────────

    def process_frame(self, frame_bgr):
        self.frame_count += 1
        annotated = frame_bgr.copy()
        self.live_pipeline_steps = ['Kamera karesi alindi']

        if self.frame_count % self.skip_frames != 0:
            return annotated, self._display_ema, self.current_feedback, self.rep_count, {}

        landmarks = self._detect_landmarks(frame_bgr)
        if landmarks is None:
            self._no_detection_streak += 1
            if self._last_landmarks is not None and self._no_detection_streak <= self._max_hold_frames:
                landmarks = self._last_landmarks
            else:
                self._display_ema *= 0.80
                self.current_feedback = ['Lutfen kameranin karsisinda durun']
                self.live_pipeline_steps.append('Pose bulunamadi')
                return annotated, self._display_ema, self.current_feedback, self.rep_count, {}
        else:
            self._no_detection_streak = 0

        self._last_landmarks = landmarks
        shape = frame_bgr.shape
        current_angles = extract_angles(landmarks, shape)
        current_vec = extract_pose_vector(landmarks, shape)
        visibility = extract_visibility(landmarks)
        self.live_pipeline_steps.append(f'{len(current_angles)} eklem acisi hesaplandi')

        progress_now, _missing = self.rep_counter.progress_of(current_angles)
        similarity, feedback, joint_status = 0.0, [], {}
        if self.reference_sequence and current_angles:
            similarity, feedback, joint_status = self._quality_against_reference(
                current_angles, current_vec, progress_now or 0.0
            )
            self.live_pipeline_steps.append('Kalite referans ile olculdu')
        elif not self.rep_counter.configured:
            feedback = ['Referans bekleniyor — doktor videosu gerekli']

        decision = self.rep_counter.update(
            current_angles,
            now=self._frame_time(),
            quality=similarity,
            visibility=visibility,
        )
        self.rep_count = self.rep_counter.count
        self.correct_reps = self.rep_count
        self.total_attempts = self.rep_counter.attempts + self.rep_count
        for hint in decision.get('hints') or []:
            if hint not in feedback:
                feedback.insert(0, hint)
        if decision.get('counted'):
            self.error_history.append({
                'rep': self.rep_count,
                'correct': True,
                'quality': decision.get('quality', 0.0),
                'errors': [],
            })
            feedback.insert(0, f'Dogru tekrar! +1  (toplam {self.rep_count})')
        elif decision.get('reason') == 'form':
            self.error_history.append({
                'rep': self.total_attempts,
                'correct': False,
                'quality': decision.get('quality', 0.0),
                'reason': 'form',
                'joint': decision.get('joint'),
                'errors': list(feedback),
            })
            if DEBUG_REP:
                self.live_pipeline_steps.append(
                    f"Tekrar +1 progress={decision.get('progress')} peak={decision.get('peak')}"
                )

        display = self._smooth_display(similarity)
        self.live_pipeline_steps.append(f'Benzerlik: %{int(round(display * 100))}')
        self.current_feedback = feedback
        self._draw_skeleton(annotated, landmarks, joint_status, shape[:2])
        return annotated, display, feedback, self.rep_count, joint_status

    def _smooth_display(self, raw):
        if raw <= 0.0:
            self._display_ema *= 0.82
            return self._display_ema
        self._display_ema = (DISPLAY_SMOOTH * raw) + ((1.0 - DISPLAY_SMOOTH) * self._display_ema)
        return float(np.clip(self._display_ema, 0.0, 1.0))

    # ─── MediaPipe ───────────────────────────────────────────────────────────

    def _detect_landmarks(self, frame_bgr):
        if not self._landmarker:
            return None
        try:
            rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            mp_image = MPImage(image_format=MPImageFormat.SRGB, data=rgb)
            self._video_ts_ms += 33
            result = self._landmarker.detect_for_video(mp_image, self._video_ts_ms)
            if result.pose_landmarks:
                return self._smooth_landmarks(result.pose_landmarks[0])
        except Exception as exc:
            print(f'[PoseEngine] Tespit hatasi: {exc}')
        return None

    def _smooth_landmarks(self, landmarks):
        if self._last_landmarks is None:
            return landmarks
        out = []
        for cur, prev in zip(landmarks, self._last_landmarks):
            out.append(SimpleNamespace(
                x=self._smooth_alpha * cur.x + (1 - self._smooth_alpha) * prev.x,
                y=self._smooth_alpha * cur.y + (1 - self._smooth_alpha) * prev.y,
                z=self._smooth_alpha * getattr(cur, 'z', 0) + (1 - self._smooth_alpha) * getattr(prev, 'z', 0),
                visibility=self._smooth_alpha * getattr(cur, 'visibility', 1) + (1 - self._smooth_alpha) * getattr(prev, 'visibility', 1),
            ))
        return out

    def _draw_skeleton(self, frame, landmarks, joint_status, shape):
        h, w = shape
        pts = {i: (int(lm.x * w), int(lm.y * h)) for i, lm in enumerate(landmarks)}
        for i, j in POSE_CONNECTIONS:
            if i in pts and j in pts:
                cv2.line(frame, pts[i], pts[j], COLOR_BONE, 2, cv2.LINE_AA)
        for joint, (_, b_i, _) in JOINT_ANGLES.items():
            if b_i not in pts:
                continue
            status = joint_status.get(joint, 'ok')
            color = {'ok': COLOR_OK, 'warning': COLOR_WARN, 'error': COLOR_ERROR}.get(status, COLOR_OK)
            radius = {'ok': 5, 'warning': 7, 'error': 9}.get(status, 5)
            cv2.circle(frame, pts[b_i], radius, color, -1, cv2.LINE_AA)

    # ─── Oturum ──────────────────────────────────────────────────────────────

    def get_session_summary(self):
        counted = self.rep_counter.count
        accuracy = self.rep_counter.mean_quality() * 100.0
        top_errors = sorted(self.joint_error_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        return {
            'total_reps': counted,
            'correct_reps': counted,
            'accuracy_score': round(accuracy, 1),
            'joint_errors': {JOINT_NAMES_TR.get(k, k): v for k, v in top_errors if v > 0},
            'rep_history': list(self.error_history),
        }

    def get_live_pipeline_steps(self):
        return list(self.live_pipeline_steps)

    def reset_session(self):
        profiles = self.rep_counter.export_profiles()
        stable = self.rep_counter.export_stable()
        self.rep_counter.configure(profiles, stable)
        self.rep_count = 0
        self.total_attempts = 0
        self.correct_reps = 0
        self.frame_count = 0
        self._display_ema = 0.0
        self._no_detection_streak = 0
        self._last_landmarks = None
        self._recreate_landmarker()
        self.current_feedback = []
        self.live_pipeline_steps = []
        self.error_history.clear()
        self.joint_error_counts = {j: 0 for j in JOINT_ANGLES}

    def _recreate_landmarker(self):
        """VIDEO modu zaman damgasini geri saramaz; yeni oturumda dedektor yenilenir."""
        self.release()
        self._video_ts_ms = 0
        self._init_landmarker()

    def release(self):
        if self._landmarker:
            self._landmarker.close()
            self._landmarker = None
