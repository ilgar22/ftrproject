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
from types import SimpleNamespace
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
ANGLE_SOFT_TOLERANCE = 12.0
ANGLE_HARD_TOLERANCE = 60.0
TRAJECTORY_POINTS = {
    'sol_bilek': LM.LEFT_WRIST,
    'sag_bilek': LM.RIGHT_WRIST,
    'sol_dirsek': LM.LEFT_ELBOW,
    'sag_dirsek': LM.RIGHT_ELBOW,
}

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

    # Aci benzerligini "yaklasik dogruluk" mantigiyla hesapla:
    # kucuk farklari tolere et, buyuk farklarda puani hizla dusur.
    scores = []
    for j in common:
        diff = abs(float(angles_a[j]) - float(angles_b[j]))
        if diff <= ANGLE_SOFT_TOLERANCE:
            s = 1.0
        elif diff >= ANGLE_HARD_TOLERANCE:
            s = 0.0
        else:
            span = ANGLE_HARD_TOLERANCE - ANGLE_SOFT_TOLERANCE
            s = 1.0 - ((diff - ANGLE_SOFT_TOLERANCE) / span)
        scores.append(float(np.clip(s, 0.0, 1.0)))
    return round(float(np.mean(scores)), 4)


def extract_trajectory(pose_landmarks):
    """Govde merkezine ve omuz genisligine gore normalize edilmis noktalar."""
    if not pose_landmarks or len(pose_landmarks) < 33:
        return {}

    l_sh = pose_landmarks[LM.LEFT_SHOULDER]
    r_sh = pose_landmarks[LM.RIGHT_SHOULDER]
    l_hip = pose_landmarks[LM.LEFT_HIP]
    r_hip = pose_landmarks[LM.RIGHT_HIP]
    center_x = (l_hip.x + r_hip.x) * 0.5
    center_y = (l_hip.y + r_hip.y) * 0.5
    shoulder_dist = np.hypot(l_sh.x - r_sh.x, l_sh.y - r_sh.y)
    scale = max(float(shoulder_dist), 1e-3)

    traj = {}
    for name, idx in TRAJECTORY_POINTS.items():
        lm = pose_landmarks[idx]
        vis = getattr(lm, 'visibility', 1.0) or 1.0
        if vis > 0.4:
            traj[name] = [
                round((lm.x - center_x) / scale, 4),
                round((lm.y - center_y) / scale, 4),
            ]
    return traj


def trajectory_similarity(traj_a, traj_b):
    common = set(traj_a.keys()) & set(traj_b.keys())
    if not common:
        return 0.0

    dists = []
    for key in common:
        pa = np.array(traj_a[key], dtype=np.float32)
        pb = np.array(traj_b[key], dtype=np.float32)
        dists.append(float(np.linalg.norm(pa - pb)))

    # 0'a yakin mesafe => 1'e yakin benzerlik
    mean_dist = float(np.mean(dists))
    return float(np.clip(np.exp(-1.8 * mean_dist), 0.0, 1.0))


def extract_landmarks33(pose_landmarks):
    """33 landmarkin tamamini govde merkezine gore normalize et."""
    if not pose_landmarks or len(pose_landmarks) < 33:
        return []

    l_sh = pose_landmarks[LM.LEFT_SHOULDER]
    r_sh = pose_landmarks[LM.RIGHT_SHOULDER]
    l_hip = pose_landmarks[LM.LEFT_HIP]
    r_hip = pose_landmarks[LM.RIGHT_HIP]
    center_x = (l_hip.x + r_hip.x) * 0.5
    center_y = (l_hip.y + r_hip.y) * 0.5
    center_z = (getattr(l_hip, 'z', 0.0) + getattr(r_hip, 'z', 0.0)) * 0.5
    shoulder_dist = np.hypot(l_sh.x - r_sh.x, l_sh.y - r_sh.y)
    scale = max(float(shoulder_dist), 1e-3)

    out = []
    for lm in pose_landmarks[:33]:
        vis = float(getattr(lm, 'visibility', 1.0) or 1.0)
        out.append([
            round((lm.x - center_x) / scale, 4),
            round((lm.y - center_y) / scale, 4),
            round((getattr(lm, 'z', 0.0) - center_z) / scale, 4),
            round(vis, 4),
        ])
    return out


def landmarks33_similarity(lms_a, lms_b):
    if not lms_a or not lms_b:
        return 0.0
    n = min(len(lms_a), len(lms_b), 33)
    if n == 0:
        return 0.0

    dists = []
    for i in range(n):
        xa, ya, za, va = lms_a[i]
        xb, yb, zb, vb = lms_b[i]
        vis = min(float(va), float(vb))
        if vis < 0.35:
            continue
        d = np.linalg.norm(np.array([xa - xb, ya - yb, za - zb], dtype=np.float32))
        dists.append(float(d))

    if not dists:
        return 0.0
    mean_dist = float(np.mean(dists))
    return float(np.clip(np.exp(-1.4 * mean_dist), 0.0, 1.0))


class PoseEngine:

    def __init__(self):
        self._landmarker     = None
        self._last_landmarks = None
        self.frame_count     = 0
        self.skip_frames     = 1
        self.reference_sequence  = []
        self.reference_profile   = {}
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
        self.exercise_mode       = 'reference'
        self.biceps_side         = 'auto'
        self.biceps_up_angle     = 65
        self.biceps_down_angle   = 145
        self._biceps_state       = 'down'
        self._video_ts_ms        = 0
        self._smooth_alpha       = 0.65
        self._no_detection_streak = 0
        self._max_hold_frames     = 6
        self.rep_angle_joint      = None
        self.rep_up_angle         = 70.0
        self.rep_down_angle       = 140.0
        self._rep_quality_window  = []
        self.live_pipeline_steps  = []
        self._init_landmarker()

    def set_exercise_mode(self, mode='reference', side='auto'):
        self.exercise_mode = mode or 'reference'
        self.biceps_side = side or 'auto'
        self._biceps_state = 'down'

    def _init_landmarker(self):
        if not _ensure_model():
            return
        try:
            opts = PoseLandmarkerOpts(
                base_options=BaseOptions(model_asset_path=MODEL_PATH),
                running_mode=RunningMode.VIDEO,
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
            if isinstance(pose_json_data, dict):
                self.reference_sequence = pose_json_data.get('frames', [])
                self.reference_profile = pose_json_data.get('profile', {})
            else:
                self.reference_sequence = pose_json_data
                self.reference_profile = self._build_reference_profile(self.reference_sequence)
            self._apply_profile_to_rep_counter()
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
                    trajectory = extract_trajectory(lms)
                    lms33 = extract_landmarks33(lms)
                    if angles:
                        sequence.append({
                            'frame': frame_idx,
                            'angles': angles,
                            'trajectory': trajectory,
                            'landmarks33': lms33,
                        })
                if callback_progress and total_frames > 0:
                    progress = frame_idx / total_frames
                    try:
                        callback_progress(progress, frame_idx, total_frames)
                    except TypeError:
                        callback_progress(progress)
            frame_idx += 1
        cap.release()
        self.reference_sequence = sequence
        self.reference_profile = self._build_reference_profile(sequence)
        self._apply_profile_to_rep_counter()
        return {
            'frames': sequence,
            'profile': self.reference_profile,
        }

    def _detect_landmarks(self, frame_bgr):
        if not self._landmarker:
            return None
        try:
            rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            mp_image = MPImage(image_format=MPImageFormat.SRGB, data=rgb)
            self._video_ts_ms += 33
            result = self._landmarker.detect_for_video(mp_image, self._video_ts_ms)
            if result.pose_landmarks and len(result.pose_landmarks) > 0:
                return self._smooth_landmarks(result.pose_landmarks[0])
        except Exception as e:
            print(f"[PoseEngine] Tespit hatasi: {e}")
        return None

    def _smooth_landmarks(self, landmarks):
        if self._last_landmarks is None:
            return landmarks

        smoothed = []
        for cur, prev in zip(landmarks, self._last_landmarks):
            smoothed.append(SimpleNamespace(
                x=(self._smooth_alpha * cur.x) + ((1.0 - self._smooth_alpha) * prev.x),
                y=(self._smooth_alpha * cur.y) + ((1.0 - self._smooth_alpha) * prev.y),
                z=(self._smooth_alpha * getattr(cur, 'z', 0.0)) + ((1.0 - self._smooth_alpha) * getattr(prev, 'z', 0.0)),
                visibility=(self._smooth_alpha * getattr(cur, 'visibility', 1.0)) + ((1.0 - self._smooth_alpha) * getattr(prev, 'visibility', 1.0)),
            ))
        return smoothed

    def process_frame(self, frame_bgr):
        self.frame_count += 1
        annotated = frame_bgr.copy()
        self.live_pipeline_steps = [
            '1) Kamera karesi alindi',
            '2) Pose landmark tespiti basladi',
        ]

        if self.frame_count % self.skip_frames != 0:
            return annotated, 0.0, self.current_feedback, self.rep_count, {}

        landmarks = self._detect_landmarks(frame_bgr)
        if landmarks is None:
            self._no_detection_streak += 1
            if self._last_landmarks is not None and self._no_detection_streak <= self._max_hold_frames:
                landmarks = self._last_landmarks
                self.live_pipeline_steps.append('3) Landmark gecici olarak onceki kareden tutuldu')
            else:
                self.current_feedback = ["Lutfen kameranin karsisinda durun"]
                self.live_pipeline_steps.append('3) Pose bulunamadi')
                return annotated, 0.0, self.current_feedback, self.rep_count, {}
        else:
            self._no_detection_streak = 0
            self.live_pipeline_steps.append('3) Landmarklar basariyla bulundu')

        self._last_landmarks = landmarks
        current_angles = extract_angles(landmarks)
        current_traj = extract_trajectory(landmarks)
        current_lms33 = extract_landmarks33(landmarks)
        self.live_pipeline_steps.append('4) Eklem acilari hesaplandi')
        self.live_pipeline_steps.append('5) Normalize trajektori cikarildi')
        self.live_pipeline_steps.append('6) 33 landmark normalize edildi')
        similarity, feedback, joint_status = 0.0, [], {}

        if self.exercise_mode == 'biceps' and current_angles:
            similarity, feedback, joint_status = self._process_biceps(current_angles)
            self.live_pipeline_steps.append('7) Biceps kural seti ile analiz edildi')
        elif self.reference_sequence and current_angles:
            similarity, feedback, joint_status = self._compare_with_reference(current_angles, current_traj, current_lms33)
            self._update_rep_counter(similarity, feedback, current_angles)
            self.live_pipeline_steps.append('7) Referans model ile canli hareket karsilastirildi')
            self.live_pipeline_steps.append('8) Tekrar sayaci durum makinesi guncellendi')
        else:
            self.live_pipeline_steps.append('7) Referans bekleniyor')

        self.live_pipeline_steps.append(f'9) Benzerlik skoru: %{int(similarity * 100)}')

        self._draw_skeleton(annotated, landmarks, joint_status, frame_bgr.shape[:2])
        self.current_feedback = feedback
        return annotated, similarity, feedback, self.rep_count, joint_status

    def get_live_pipeline_steps(self):
        return list(self.live_pipeline_steps)

    def _process_biceps(self, current_angles):
        left = current_angles.get('sol_dirsek')
        right = current_angles.get('sag_dirsek')

        if left is None and right is None:
            return 0.0, ['Dirsek gorunmuyor, kameraya yaklasin'], {}

        if self.biceps_side == 'left':
            active = left
            side_key = 'sol_dirsek'
        elif self.biceps_side == 'right':
            active = right
            side_key = 'sag_dirsek'
        else:
            if left is not None and right is not None:
                active = min(left, right)
                side_key = 'sol_dirsek' if left <= right else 'sag_dirsek'
            elif left is not None:
                active, side_key = left, 'sol_dirsek'
            else:
                active, side_key = right, 'sag_dirsek'

        similarity = float(np.clip((180.0 - active) / 120.0, 0.0, 1.0))
        feedback = []
        joint_status = {side_key: 'ok'}

        if self._biceps_state == 'down' and active <= self.biceps_up_angle:
            self._biceps_state = 'up'
            feedback.append('Yukari pozisyon algilandi')
        elif self._biceps_state == 'up' and active >= self.biceps_down_angle:
            self._biceps_state = 'down'
            self.total_reps += 1
            self.correct_reps += 1
            self.rep_count += 1
            self.error_history.append({
                'rep': self.total_reps, 'correct': True, 'errors': []
            })
            feedback.append(f'Tekrar sayildi: {self.rep_count}')
        else:
            if active > self.biceps_up_angle and self._biceps_state == 'down':
                feedback.append('Dirsegi daha fazla bukun')
            elif active < self.biceps_down_angle and self._biceps_state == 'up':
                feedback.append('Kolu kontrollu sekilde asagi indirin')

        return similarity, feedback, joint_status

    def _compare_with_reference(self, current_angles, current_traj, current_lms33):
        best_score, best_ref = 0.0, {}
        start = max(0, self.ref_index - 10)
        end   = min(len(self.reference_sequence), self.ref_index + 15)

        for i in range(start, end):
            ref   = self.reference_sequence[i].get('angles', {})
            ref_traj = self.reference_sequence[i].get('trajectory', {})
            ref_lms33 = self.reference_sequence[i].get('landmarks33', [])
            score_angle = angle_similarity(current_angles, ref)
            score_traj = trajectory_similarity(current_traj, ref_traj)
            score_lm = landmarks33_similarity(current_lms33, ref_lms33)
            # Birincil metrik acilar: hareketi yaklasik aci benzerligine gore degerlendir.
            score = (0.85 * score_angle) + (0.10 * score_traj) + (0.05 * score_lm)
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

    def _update_rep_counter(self, similarity, feedback, current_angles):
        self._rep_quality_window.append(similarity)
        if len(self._rep_quality_window) > 90:
            self._rep_quality_window = self._rep_quality_window[-90:]

        joint_name = self.rep_angle_joint
        current_joint_angle = current_angles.get(joint_name) if joint_name else None
        if current_joint_angle is None:
            self._update_rep_counter_fallback(similarity, feedback)
            return

        has_error = any('hata' in f for f in feedback)
        if self.rep_state == 'rest' and current_joint_angle <= self.rep_up_angle:
            self.rep_state = 'active'
        elif self.rep_state == 'active' and current_joint_angle >= self.rep_down_angle:
            self.rep_state = 'rest'
            self.total_reps += 1
            self.ref_index = 0
            rep_quality = float(np.mean(self._rep_quality_window[-20:])) if self._rep_quality_window else similarity
            rep_is_correct = (not has_error) and (rep_quality >= 0.60)
            if rep_is_correct:
                self.correct_reps += 1
                self.rep_count += 1
            self.error_history.append({
                'rep': self.total_reps,
                'correct': rep_is_correct,
                'quality': round(rep_quality, 3),
                'errors': feedback.copy()
            })

    def _update_rep_counter_fallback(self, similarity, feedback):
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

    def _build_reference_profile(self, sequence):
        if not sequence:
            return {}

        angle_tracks = {}
        for item in sequence:
            for j, a in item.get('angles', {}).items():
                angle_tracks.setdefault(j, []).append(float(a))

        ranges = {}
        for j, vals in angle_tracks.items():
            if len(vals) >= 6:
                ranges[j] = float(np.percentile(vals, 90) - np.percentile(vals, 10))

        if not ranges:
            return {}

        # En fazla degisim gosteren eklem tekrar sayiminda ana sinyal olur.
        rep_joint = max(ranges, key=ranges.get)
        vals = angle_tracks.get(rep_joint, [])
        low = float(np.percentile(vals, 15))
        high = float(np.percentile(vals, 85))

        up = low + 0.20 * (high - low)
        down = high - 0.20 * (high - low)
        if down - up < 8.0:
            up = low + 2.0
            down = high - 2.0

        return {
            'rep_joint': rep_joint,
            'rep_up_angle': round(float(up), 2),
            'rep_down_angle': round(float(down), 2),
            'joint_ranges': {k: round(v, 2) for k, v in ranges.items()},
        }

    def _apply_profile_to_rep_counter(self):
        profile = self.reference_profile or {}
        self.rep_angle_joint = profile.get('rep_joint')
        if profile.get('rep_up_angle') is not None:
            self.rep_up_angle = float(profile.get('rep_up_angle'))
        if profile.get('rep_down_angle') is not None:
            self.rep_down_angle = float(profile.get('rep_down_angle'))

    def _draw_skeleton(self, frame, landmarks, joint_status, shape):
        h, w = shape
        pts = {i: (int(lm.x * w), int(lm.y * h)) for i, lm in enumerate(landmarks)}
        for (i, j) in POSE_CONNECTIONS:
            if i in pts and j in pts:
                cv2.line(frame, pts[i], pts[j], COLOR_BONE, 2, cv2.LINE_AA)

        # Tum 33 landmarki gostermek icin kucuk noktalar ciz.
        for idx, p in pts.items():
            vis = float(getattr(landmarks[idx], 'visibility', 1.0) or 1.0)
            if vis > 0.35:
                cv2.circle(frame, p, 2, (220, 220, 220), -1, cv2.LINE_AA)

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
        self._biceps_state = 'down'
        self._video_ts_ms = 0
        self._no_detection_streak = 0
        self.ref_index = 0
        self.current_feedback = []
        self.live_pipeline_steps = []
        self._rep_quality_window = []
        self.error_history.clear()
        self.joint_error_counts  = {j: 0 for j in JOINT_ANGLES}
        self._last_landmarks = None

    def release(self):
        if self._landmarker:
            self._landmarker.close()
            self._landmarker = None
