"""
Pose Engine - MediaPipe Pose Estimation ve Karşılaştırma Motoru
MediaPipe Tasks API v0.10+ uyumlu (PoseLandmarker)
"""

import mediapipe as mp
import numpy as np
import cv2
import json
import urllib.request
import os
from collections import deque


# ─── MediaPipe Tasks API ─────────────────────────────────────────────────────
PoseLandmarker     = mp.tasks.vision.PoseLandmarker
PoseLandmarkerOpts = mp.tasks.vision.PoseLandmarkerOptions
RunningMode        = mp.tasks.vision.RunningMode
BaseOptions        = mp.tasks.BaseOptions
MPImage            = mp.Image
MPImageFormat      = mp.ImageFormat

MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          'pose_landmarker.task')
MODEL_URL  = ("https://storage.googleapis.com/mediapipe-models/"
              "pose_landmarker/pose_landmarker_lite/float16/latest/"
              "pose_landmarker_lite.task")


def _ensure_model():
    if not os.path.exists(MODEL_PATH):
        print("[PoseEngine] Model indiriliyor...")
        try:
            urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
            print("[PoseEngine] Model indirildi.")
            return True
        except Exception as e:
            print(f"[PoseEngine] Model indirilemedi: {e}")
            return False
    return True


# ─── LANDMARK INDEXLERİ ──────────────────────────────────────────────────────
class LM:
    NOSE           = 0
    LEFT_SHOULDER  = 11
    RIGHT_SHOULDER = 12
    LEFT_ELBOW     = 13
    RIGHT_ELBOW    = 14
    LEFT_WRIST     = 15
    RIGHT_WRIST    = 16
    LEFT_HIP       = 23
    RIGHT_HIP      = 24
    LEFT_KNEE      = 25
    RIGHT_KNEE     = 26
    LEFT_ANKLE     = 27
    RIGHT_ANKLE    = 28


JOINT_ANGLES = {
    'sol_dirsek': (LM.LEFT_SHOULDER,  LM.LEFT_ELBOW,    LM.LEFT_WRIST),
    'sag_dirsek': (LM.RIGHT_SHOULDER, LM.RIGHT_ELBOW,   LM.RIGHT_WRIST),
    'sol_omuz':   (LM.LEFT_ELBOW,     LM.LEFT_SHOULDER, LM.LEFT_HIP),
    'sag_omuz':   (LM.RIGHT_ELBOW,    LM.RIGHT_SHOULDER,LM.RIGHT_HIP),
    'sol_kalca':  (LM.LEFT_SHOULDER,  LM.LEFT_HIP,      LM.LEFT_KNEE),
    'sag_kalca':  (LM.RIGHT_SHOULDER, LM.RIGHT_HIP,     LM.RIGHT_KNEE),
    'sol_diz':    (LM.LEFT_HIP,       LM.LEFT_KNEE,     LM.LEFT_ANKLE),
    'sag_diz':    (LM.RIGHT_HIP,      LM.RIGHT_KNEE,    LM.RIGHT_ANKLE),
}

JOINT_NAMES_TR = {
    'sol_dirsek': 'Sol Dirsek', 'sag_dirsek': 'Sag Dirsek',
    'sol_omuz':   'Sol Omuz',   'sag_omuz':   'Sag Omuz',
    'sol_kalca':  'Sol Kalca',  'sag_kalca':  'Sag Kalca',
    'sol_diz':    'Sol Diz',    'sag_diz':    'Sag Diz',
}

COLOR_OK    = (100, 255, 0)
COLOR_WARN  = (0,   200, 255)
COLOR_ERROR = (0,   60,  255)
COLOR_BONE  = (160, 160, 160)
THRESHOLD_WARN  = 20
THRESHOLD_ERROR = 35

POSE_CONNECTIONS = [
    (11,12),(11,13),(13,15),(12,14),(14,16),
    (11,23),(12,24),(23,24),
    (23,25),(25,27),(24,26),(26,28),
    (27,29),(28,30),(27,31),(28,32),
]


def calculate_angle(a, b, c):
    a, b, c = np.array(a), np.array(b), np.array(c)
    ba, bc = a - b, c - b
    cos_a = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-8)
    return float(np.degrees(np.arccos(np.clip(cos_a, -1.0, 1.0))))


def extract_angles(pose_landmarks):
    if not pose_landmarks or len(pose_landmarks) < 33:
        return {}
    angles = {}
    for joint_name, (a_idx, b_idx, c_idx) in JOINT_ANGLES.items():
        lm_a = pose_landmarks[a_idx]
        lm_b = pose_landmarks[b_idx]
        lm_c = pose_landmarks[c_idx]
        vis_a = getattr(lm_a, 'visibility', 1.0) or 1.0
        vis_b = getattr(lm_b, 'visibility', 1.0) or 1.0
        vis_c = getattr(lm_c, 'visibility', 1.0) or 1.0
        if vis_a > 0.4 and vis_b > 0.4 and vis_c > 0.4:
            angles[joint_name] = round(calculate_angle(
                [lm_a.x, lm_a.y], [lm_b.x, lm_b.y], [lm_c.x, lm_c.y]
            ), 2)
    return angles


def angle_similarity(angles_a, angles_b):
    common = set(angles_a.keys()) & set(angles_b.keys())
    if not common:
        return 0.0
    errors = [min(abs(angles_a[j] - angles_b[j]) / 180.0, 1.0) for j in common]
    return round(1.0 - float(np.mean(errors)), 4)


class PoseEngine:

    def __init__(self):
        self._landmarker     = None
        self._last_landmarks = None
        self.frame_count     = 0
        self.skip_frames     = 2
        self.reference_sequence  = []
        self.ref_index           = 0
        self.rep_count           = 0
        self.total_reps          = 0
        self.correct_reps        = 0
        self.rep_state           = 'rest'
        self.rep_threshold_up    = 0.75
        self.rep_threshold_down  = 0.45
        self.current_feedback    = []
        self.error_history       = deque(maxlen=100)
        self.joint_error_counts  = {j: 0 for j in JOINT_ANGLES}
        self._init_landmarker()

    def _init_landmarker(self):
        if not _ensure_model():
            return
        try:
            opts = PoseLandmarkerOpts(
                base_options=BaseOptions(model_asset_path=MODEL_PATH),
                running_mode=RunningMode.IMAGE,
                num_poses=1,
                min_pose_detection_confidence=0.55,
                min_pose_presence_confidence=0.55,
                min_tracking_confidence=0.5,
            )
            self._landmarker = PoseLandmarker.create_from_options(opts)
            print("[PoseEngine] Hazir.")
        except Exception as e:
            print(f"[PoseEngine] Baslatilamadi: {e}")

    def load_reference_from_json(self, pose_json_data):
        try:
            if isinstance(pose_json_data, str):
                pose_json_data = json.loads(pose_json_data)
            self.reference_sequence = pose_json_data
            self.ref_index = 0
            return True
        except Exception:
            return False

    def extract_reference_from_video(self, video_path, callback_progress=None):
        if not self._landmarker:
            return []
        cap = cv2.VideoCapture(video_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        sequence = []
        frame_idx = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            if frame_idx % 3 == 0:
                lms = self._detect_landmarks(frame)
                if lms:
                    angles = extract_angles(lms)
                    if angles:
                        sequence.append({'frame': frame_idx, 'angles': angles})
                if callback_progress and total_frames > 0:
                    callback_progress(frame_idx / total_frames)
            frame_idx += 1
        cap.release()
        self.reference_sequence = sequence
        return sequence

    def _detect_landmarks(self, frame_bgr):
        if not self._landmarker:
            return None
        try:
            rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            mp_image = MPImage(image_format=MPImageFormat.SRGB, data=rgb)
            result = self._landmarker.detect(mp_image)
            if result.pose_landmarks and len(result.pose_landmarks) > 0:
                return result.pose_landmarks[0]
        except Exception as e:
            print(f"[PoseEngine] Tespit hatasi: {e}")
        return None

    def process_frame(self, frame_bgr):
        self.frame_count += 1
        annotated = frame_bgr.copy()

        if self.frame_count % self.skip_frames != 0:
            return annotated, 0.0, self.current_feedback, self.rep_count, {}

        landmarks = self._detect_landmarks(frame_bgr)
        if landmarks is None:
            self.current_feedback = ["Lutfen kameranin karsisinda durun"]
            return annotated, 0.0, self.current_feedback, self.rep_count, {}

        self._last_landmarks = landmarks
        current_angles = extract_angles(landmarks)
        similarity, feedback, joint_status = 0.0, [], {}

        if self.reference_sequence and current_angles:
            similarity, feedback, joint_status = self._compare_with_reference(current_angles)
            self._update_rep_counter(similarity, feedback)

        self._draw_skeleton(annotated, landmarks, joint_status, frame_bgr.shape[:2])
        self.current_feedback = feedback
        return annotated, similarity, feedback, self.rep_count, joint_status

    def _compare_with_reference(self, current_angles):
        best_score, best_ref = 0.0, {}
        start = max(0, self.ref_index - 10)
        end   = min(len(self.reference_sequence), self.ref_index + 15)

        for i in range(start, end):
            ref   = self.reference_sequence[i].get('angles', {})
            score = angle_similarity(current_angles, ref)
            if score > best_score:
                best_score = score
                best_ref   = ref
                self.ref_index = i

        feedback, joint_status = [], {}
        for joint_name, cur_angle in current_angles.items():
            if joint_name not in best_ref:
                continue
            diff = abs(cur_angle - best_ref[joint_name])
            if diff >= THRESHOLD_ERROR:
                status = 'error'
                self.joint_error_counts[joint_name] += 1
                feedback.append(f"{JOINT_NAMES_TR.get(joint_name, joint_name)}: {diff:.0f}° hata")
            elif diff >= THRESHOLD_WARN:
                status = 'warning'
                feedback.append(f"{JOINT_NAMES_TR.get(joint_name, joint_name)}: duzelt ({diff:.0f}°)")
            else:
                status = 'ok'
            joint_status[joint_name] = status

        return best_score, feedback, joint_status

    def _update_rep_counter(self, similarity, feedback):
        has_error = any('hata' in f for f in feedback)
        if self.rep_state == 'rest' and similarity >= self.rep_threshold_up:
            self.rep_state = 'active'
        elif self.rep_state == 'active' and similarity < self.rep_threshold_down:
            self.rep_state = 'rest'
            self.total_reps += 1
            self.ref_index = 0
            if not has_error:
                self.correct_reps += 1
                self.rep_count += 1
            self.error_history.append({
                'rep': self.total_reps, 'correct': not has_error, 'errors': feedback.copy()
            })

    def _draw_skeleton(self, frame, landmarks, joint_status, shape):
        h, w = shape
        pts = {i: (int(lm.x * w), int(lm.y * h)) for i, lm in enumerate(landmarks)}
        for (i, j) in POSE_CONNECTIONS:
            if i in pts and j in pts:
                cv2.line(frame, pts[i], pts[j], COLOR_BONE, 2, cv2.LINE_AA)
        for joint_name, (a_idx, b_idx, c_idx) in JOINT_ANGLES.items():
            status = joint_status.get(joint_name, 'ok')
            color  = {'ok': COLOR_OK, 'warning': COLOR_WARN, 'error': COLOR_ERROR}.get(status, COLOR_OK)
            radius = {'ok': 5, 'warning': 7, 'error': 9}.get(status, 5)
            if b_idx in pts:
                cv2.circle(frame, pts[b_idx], radius, color, -1, cv2.LINE_AA)
                cv2.circle(frame, pts[b_idx], radius+2, (255,255,255), 1, cv2.LINE_AA)

    def get_session_summary(self):
        accuracy = (self.correct_reps / self.total_reps * 100 if self.total_reps > 0 else 0.0)
        top_errors = sorted(self.joint_error_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        return {
            'total_reps':     self.total_reps,
            'correct_reps':   self.correct_reps,
            'accuracy_score': round(accuracy, 1),
            'joint_errors':   {JOINT_NAMES_TR.get(k, k): v for k, v in top_errors if v > 0},
            'rep_history':    list(self.error_history),
        }

    def reset_session(self):
        self.rep_count = self.total_reps = self.correct_reps = self.frame_count = 0
        self.rep_state = 'rest'
        self.ref_index = 0
        self.current_feedback = []
        self.error_history.clear()
        self.joint_error_counts  = {j: 0 for j in JOINT_ANGLES}
        self._last_landmarks = None

    def release(self):
        if self._landmarker:
            self._landmarker.close()
            self._landmarker = None
