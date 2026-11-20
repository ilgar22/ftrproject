"""
Pose Engine v3 — MediaPipe (agir model, 3B dunya koordinatlari) + cevrimici faz hizalama.

Mimari:
  1. MediaPipe Pose Landmarker (heavy): 33 nokta; acilar 3B dunya koordinatlarindan
     (metre, kalca merkezli) hesaplanir -> kamera acisina daha az bagimli.
  2. Referans videodan tekrar bolutleme ve faz sablonu (phase_aligner.build_template):
     faz basina eklem ortalamasi + referans degiskenliginden ogrenilen tolerans.
  3. Canli akis sablona cevrimici dongusel hizalama ile eslenir (OnlineAligner):
     tempo farki, tekrar siniri ve kalite ayni hizalama yolundan turer.
  4. Eklem durumu z-skorundan; ekran API'si onceki surumle ayni.
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

from services.phase_aligner import (
    ENDPOINT_NAMES_TR, JOINT_NAMES_TR, JOINTS, OnlineAligner, build_template,
    frames_to_matrix, joint_roles, progress_signal,
)

# ─── MediaPipe Tasks API ─────────────────────────────────────────────────────
PoseLandmarker = mp.tasks.vision.PoseLandmarker
PoseLandmarkerOpts = mp.tasks.vision.PoseLandmarkerOptions
RunningMode = mp.tasks.vision.RunningMode
BaseOptions = mp.tasks.BaseOptions
MPImage = mp.Image
MPImageFormat = mp.ImageFormat

# Model surumu: heavy (varsayilan) | full | lite  — POSE_MODEL_VARIANT ile degistirilebilir
MODEL_VARIANT = os.getenv('POSE_MODEL_VARIANT', 'heavy').strip().lower()
if MODEL_VARIANT not in ('heavy', 'full', 'lite'):
    MODEL_VARIANT = 'heavy'
_SERVICES_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(_SERVICES_DIR, f'pose_landmarker_{MODEL_VARIANT}.task')
MODEL_URL = (
    'https://storage.googleapis.com/mediapipe-models/'
    f'pose_landmarker/pose_landmarker_{MODEL_VARIANT}/float16/latest/'
    f'pose_landmarker_{MODEL_VARIANT}.task'
)
DEBUG_REP = os.getenv('DEBUG_REP', '0').strip().lower() in ('1', 'true', 'yes')


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

POSE_CONNECTIONS = [
    (11, 12), (11, 13), (13, 15), (12, 14), (14, 16),
    (11, 23), (12, 24), (23, 24),
    (23, 25), (25, 27), (24, 26), (26, 28),
]

COLOR_OK = (80, 220, 80)
COLOR_WARN = (0, 200, 255)
COLOR_ERROR = (0, 60, 255)
COLOR_BONE = (160, 160, 160)

MIN_JOINTS = 4
MIN_VISIBILITY = 0.35
DISPLAY_SMOOTH = 0.50
LIVE_MATCH_MIN = 0.55


def _ensure_model():
    if os.path.exists(MODEL_PATH):
        return True
    print(f'[PoseEngine] {MODEL_VARIANT} modeli indiriliyor...')
    try:
        urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
        return True
    except Exception as exc:
        print(f'[PoseEngine] Model indirilemedi: {exc}')
        return False


def calculate_angle(a, b, c):
    a, b, c = np.asarray(a, dtype=np.float64), np.asarray(b, dtype=np.float64), np.asarray(c, dtype=np.float64)
    ba, bc = a - b, c - b
    cos_a = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-8)
    return float(np.degrees(np.arccos(np.clip(cos_a, -1.0, 1.0))))


def preprocess_frame(frame_bgr):
    """Hasta kamerasi ile ayni donusum — referans video ve yardimci onizleme icin."""
    frame = cv2.rotate(frame_bgr, cv2.ROTATE_90_CLOCKWISE)
    return cv2.flip(frame, 1)


def _vis(lm):
    v = getattr(lm, 'visibility', None)
    return 1.0 if v is None else float(v)


def extract_angles(world_landmarks, image_landmarks=None, min_visibility=MIN_VISIBILITY):
    """3B dunya koordinatlarindan eklem acilari. Gorunurluk goruntu noktalarindan alinir."""
    if not world_landmarks or len(world_landmarks) < 33:
        return {}
    vis_src = image_landmarks if image_landmarks and len(image_landmarks) >= 33 else world_landmarks
    angles = {}
    for name, (a_i, b_i, c_i) in JOINT_ANGLES.items():
        if min(_vis(vis_src[a_i]), _vis(vis_src[b_i]), _vis(vis_src[c_i])) <= min_visibility:
            continue
        la, lb, lc = world_landmarks[a_i], world_landmarks[b_i], world_landmarks[c_i]
        angles[name] = round(calculate_angle(
            (la.x, la.y, la.z), (lb.x, lb.y, lb.z), (lc.x, lc.y, lc.z)
        ), 2)
    return angles


def extract_visibility(landmarks):
    if not landmarks or len(landmarks) < 33:
        return {}
    return {
        name: float(min(_vis(landmarks[a]), _vis(landmarks[b]), _vis(landmarks[c])))
        for name, (a, b, c) in JOINT_ANGLES.items()
    }


ENDPOINT_LANDMARKS = {
    'sol_el': LM.LEFT_WRIST, 'sag_el': LM.RIGHT_WRIST,
    'sol_ayak': LM.LEFT_ANKLE, 'sag_ayak': LM.RIGHT_ANKLE,
}


def extract_points(world_landmarks, image_landmarks=None, min_visibility=MIN_VISIBILITY):
    """El ve ayak bilegi konumlari: kalca merkezli, govde boyuna normalize 3B koordinatlar."""
    if not world_landmarks or len(world_landmarks) < 33:
        return {}
    vis_src = image_landmarks if image_landmarks and len(image_landmarks) >= 33 else world_landmarks
    l_hip, r_hip = world_landmarks[LM.LEFT_HIP], world_landmarks[LM.RIGHT_HIP]
    l_sh, r_sh = world_landmarks[LM.LEFT_SHOULDER], world_landmarks[LM.RIGHT_SHOULDER]
    hip = np.array([(l_hip.x + r_hip.x) * 0.5, (l_hip.y + r_hip.y) * 0.5, (l_hip.z + r_hip.z) * 0.5])
    sh = np.array([(l_sh.x + r_sh.x) * 0.5, (l_sh.y + r_sh.y) * 0.5, (l_sh.z + r_sh.z) * 0.5])
    scale = max(float(np.linalg.norm(sh - hip)), 1e-3)
    points = {}
    for name, idx in ENDPOINT_LANDMARKS.items():
        if _vis(vis_src[idx]) <= min_visibility:
            continue
        lm = world_landmarks[idx]
        rel = (np.array([lm.x, lm.y, lm.z]) - hip) / scale
        points[f'{name}_x'] = round(float(rel[0]), 4)
        points[f'{name}_y'] = round(float(rel[1]), 4)
        points[f'{name}_z'] = round(float(rel[2]), 4)
    return points


class PoseEngine:
    """Canli pose analizi. Tekrar sayimi ve kalite OnlineAligner ile yapilir."""

    _reference_cache = {}

    def __init__(self):
        self._landmarker = None
        self._last_landmarks = None
        self._last_world = None
        self._video_ts_ms = 0
        self._smooth_alpha = 0.62
        self._no_detection_streak = 0
        self._max_hold_frames = 5

        self.reference_sequence = []
        self.reference_profile = {}
        self.template = None
        self.aligner = OnlineAligner()

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
        self.current_phase = 0.0

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
            print(f'[PoseEngine] v3 hazir ({MODEL_VARIANT}).')
        except Exception as exc:
            print(f'[PoseEngine] Baslatilamadi: {exc}')

    def set_exercise_mode(self, mode='reference'):
        self.exercise_mode = mode or 'reference'

    def has_reference(self):
        return self.aligner.configured and len(self.reference_sequence) >= 8

    def clear_reference(self):
        self.reference_sequence = []
        self.reference_profile = {}
        self.template = None
        self.aligner = OnlineAligner()
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
                frames = data.get('frames', []) or []
                template = data.get('template')
                profile = data.get('profile', {}) or {}
            else:
                frames, template, profile = (data or []), None, {}
            if not template:
                # eski format: yalnizca kareler -> sablonu burada kur
                template = build_template(frames)
            if not template:
                return False
            self.reference_sequence = frames
            self.template = template
            self.reference_profile = profile or self._build_profile(frames, template)
            self.aligner = OnlineAligner(template)
            self.rep_count = 0
            self.correct_reps = 0
            self.total_attempts = 0
            return self.has_reference()
        except Exception as exc:
            print(f'[PoseEngine] Referans yuklenemedi: {exc}')
            return False

    def extract_reference_from_video(self, video_path, callback_progress=None):
        if not self._landmarker:
            return {'frames': [], 'profile': {}, 'template': None}
        self._last_landmarks = None
        self._last_world = None
        cap = cv2.VideoCapture(video_path)
        try:
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        except Exception:
            pass
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1
        fps = float(cap.get(cv2.CAP_PROP_FPS) or 30.0)
        sequence, frame_idx = [], 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            frame = preprocess_frame(frame)
            lms, world = self._detect_landmarks(frame)
            if lms and world:
                angles = extract_angles(world, lms)
                if len(angles) >= MIN_JOINTS:
                    sequence.append({
                        'frame': frame_idx,
                        'angles': angles,
                        'points': extract_points(world, lms),
                    })
            if callback_progress:
                try:
                    callback_progress(frame_idx / total, frame_idx, total)
                except TypeError:
                    callback_progress(frame_idx / total)
            frame_idx += 1
        cap.release()
        self._last_landmarks = None
        self._last_world = None

        template = build_template(sequence)
        self.reference_sequence = self._annotate_progress(sequence)
        self.template = template
        self.reference_profile = self._build_profile(self.reference_sequence, template)
        self.reference_profile['fps'] = fps
        self.aligner = OnlineAligner(template) if template else OnlineAligner()
        return {
            'frames': self.reference_sequence,
            'profile': self.reference_profile,
            'template': template,
            'rep_profile': (template or {}).get('rep_profile', []),
            'stable_profile': (template or {}).get('stable_profile', []),
        }

    @staticmethod
    def _build_profile(sequence, template):
        if not sequence:
            return {}
        mat = frames_to_matrix(sequence)
        leads, stable = joint_roles(mat)
        ranges = {}
        for j, name in enumerate(JOINTS):
            col = mat[:, j]
            col = col[~np.isnan(col)]
            if col.size >= 4:
                ranges[name] = round(float(np.percentile(col, 90) - np.percentile(col, 10)), 2)
        return {
            'rep_joint': leads[0]['name'] if leads else None,
            'joint_ranges': ranges,
            'length': len(sequence),
            'reference_reps': (template or {}).get('rep_count', 0),
            'rep_profile': leads,
            'stable_profile': stable,
        }

    @staticmethod
    def _annotate_progress(sequence):
        if not sequence:
            return sequence
        mat = frames_to_matrix(sequence)
        leads, _ = joint_roles(mat)
        prog = progress_signal(mat, leads)
        for item, p in zip(sequence, prog):
            item['progress'] = round(float(p), 4)
        return sequence

    def _frame_time(self):
        if self._replay_time is None:
            return time.monotonic()
        now = self._replay_time
        self._replay_time += self._replay_dt
        return now

    # ─── Canli isleme ────────────────────────────────────────────────────────

    def process_frame(self, frame_bgr):
        self.frame_count += 1
        annotated = frame_bgr.copy()
        self.live_pipeline_steps = ['Kamera karesi alindi']

        if self.frame_count % self.skip_frames != 0:
            return annotated, self._display_ema, self.current_feedback, self.rep_count, {}

        landmarks, world = self._detect_landmarks(frame_bgr)
        if landmarks is None:
            self._no_detection_streak += 1
            if self._last_landmarks is not None and self._no_detection_streak <= self._max_hold_frames:
                landmarks, world = self._last_landmarks, self._last_world
            else:
                self._display_ema *= 0.80
                self.current_feedback = ['Lutfen kameranin karsisinda durun']
                self.live_pipeline_steps.append('Pose bulunamadi')
                return annotated, self._display_ema, self.current_feedback, self.rep_count, {}
        else:
            self._no_detection_streak = 0

        self._last_landmarks, self._last_world = landmarks, world
        shape = frame_bgr.shape
        current_angles = extract_angles(world, landmarks)
        current_points = extract_points(world, landmarks)
        self.live_pipeline_steps.append(
            f'{len(current_angles)} eklem acisi + {len(current_points) // 3} uc nokta (3B) hesaplandi'
        )

        feedback, joint_status, similarity = [], {}, 0.0
        if self.aligner.configured and current_angles:
            features = dict(current_angles)
            features.update(current_points)
            decision = self.aligner.step(features, now=self._frame_time())
            self.current_phase = decision['phase']
            similarity = decision['quality']
            joint_status, feedback = self.aligner.joint_status(decision.get('z'))
            for joint, status in joint_status.items():
                if status == 'error':
                    self.joint_error_counts[joint] = self.joint_error_counts.get(joint, 0) + 1
            self.live_pipeline_steps.append(
                f'Faz %{int(self.current_phase * 100)} — hizalama kalitesi %{int(similarity * 100)}'
            )
            self.rep_count = self.aligner.count
            self.correct_reps = self.rep_count
            self.total_attempts = self.aligner.attempts + self.rep_count

            if decision.get('counted'):
                self.error_history.append({
                    'rep': self.rep_count, 'correct': True,
                    'quality': decision.get('cycle_quality', 0.0), 'errors': [],
                })
                feedback.insert(0, f'Dogru tekrar! +1  (toplam {self.rep_count})')
            elif decision.get('reason') in ('form', 'amplitude', 'too_long'):
                reason = decision['reason']
                self.error_history.append({
                    'rep': self.total_attempts, 'correct': False,
                    'quality': decision.get('cycle_quality', 0.0),
                    'reason': reason, 'joint': decision.get('joint'), 'errors': list(feedback),
                })
                msg = {
                    'amplitude': 'Tekrar sayilmadi: hareket tam acilmadi',
                    'form': 'Tekrar sayilmadi: hareket referansa uymadi',
                    'too_long': 'Tekrar sayilmadi: cok yavas',
                }[reason]
                feedback.insert(0, msg)
            elif decision.get('reason') == 'visibility':
                feedback.insert(0, 'Eklemler gorunmuyor, kameraya tam donun')
            elif similarity < LIVE_MATCH_MIN and not feedback:
                feedback.append('Hareketi doktor videosu ile ayni yapin')
            if DEBUG_REP and (decision.get('counted') or decision.get('reason')):
                print(f"[REP] {decision}")
        elif not self.aligner.configured:
            feedback = ['Referans bekleniyor — doktor videosu gerekli']

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
        """(goruntu noktalari, dunya noktalari) veya (None, None)."""
        if not self._landmarker:
            return None, None
        try:
            rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            mp_image = MPImage(image_format=MPImageFormat.SRGB, data=rgb)
            self._video_ts_ms += 33
            result = self._landmarker.detect_for_video(mp_image, self._video_ts_ms)
            if result.pose_landmarks:
                img = self._smooth(result.pose_landmarks[0], self._last_landmarks)
                world_raw = result.pose_world_landmarks[0] if result.pose_world_landmarks else None
                world = self._smooth(world_raw, self._last_world) if world_raw else None
                return img, world
        except Exception as exc:
            print(f'[PoseEngine] Tespit hatasi: {exc}')
        return None, None

    def _smooth(self, landmarks, prev):
        if prev is None or len(prev) != len(landmarks):
            return list(landmarks)
        a = self._smooth_alpha
        out = []
        for cur, old in zip(landmarks, prev):
            out.append(SimpleNamespace(
                x=a * cur.x + (1 - a) * old.x,
                y=a * cur.y + (1 - a) * old.y,
                z=a * getattr(cur, 'z', 0.0) + (1 - a) * getattr(old, 'z', 0.0),
                visibility=a * _vis(cur) + (1 - a) * _vis(old),
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
        for ep, idx in ENDPOINT_LANDMARKS.items():
            if idx not in pts or ep not in joint_status:
                continue
            status = joint_status[ep]
            color = {'ok': COLOR_OK, 'warning': COLOR_WARN, 'error': COLOR_ERROR}.get(status, COLOR_OK)
            radius = {'ok': 5, 'warning': 7, 'error': 9}.get(status, 5)
            cv2.circle(frame, pts[idx], radius, color, -1, cv2.LINE_AA)

    # ─── Oturum ──────────────────────────────────────────────────────────────

    def get_session_summary(self):
        counted = self.aligner.count
        accuracy = self.aligner.mean_quality() * 100.0
        top_errors = sorted(self.joint_error_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        names = dict(JOINT_NAMES_TR)
        names.update(ENDPOINT_NAMES_TR)
        return {
            'total_reps': counted,
            'correct_reps': counted,
            'failed_attempts': self.aligner.attempts,
            'accuracy_score': round(accuracy, 1),
            'joint_errors': {names.get(k, k): v for k, v in top_errors if v > 0},
            'rep_history': list(self.error_history),
        }

    def get_live_pipeline_steps(self):
        return list(self.live_pipeline_steps)

    def reset_session(self):
        if self.template:
            self.aligner = OnlineAligner(self.template)
        self.rep_count = 0
        self.total_attempts = 0
        self.correct_reps = 0
        self.frame_count = 0
        self.current_phase = 0.0
        self._display_ema = 0.0
        self._no_detection_streak = 0
        self._last_landmarks = None
        self._last_world = None
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
