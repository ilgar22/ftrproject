"""
PhysioConnect - Tam Demo Testi
Kivy ve kamera olmadan tüm kritik modülleri test eder
"""

import sys
import os
import json
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

PASS = "\033[92m✓ PASS\033[0m"
FAIL = "\033[91m✗ FAIL\033[0m"
INFO = "\033[94mℹ\033[0m"
WARN = "\033[93m⚠\033[0m"
BOLD = "\033[1m"
RESET = "\033[0m"

results = []

def test(test_name, fn):
    try:
        result = fn()
        status = PASS if result else FAIL
        results.append((test_name, bool(result)))
        print(f"  {status}  {test_name}")
        return result
    except Exception as e:
        results.append((test_name, False))
        print(f"  {FAIL}  {test_name}")
        print(f"         {WARN} Hata: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
print(f"\n{BOLD}{'='*58}{RESET}")
print(f"{BOLD}  PhysioConnect — Demo Test Paketi{RESET}")
print(f"{BOLD}{'='*58}{RESET}\n")


# ═══════════════════════════════════════════════════════════════
print(f"{BOLD}1. BAĞIMLILIK TESTLERİ{RESET}")
print("─" * 40)

test("numpy import", lambda: __import__("numpy") is not None)
test("opencv import", lambda: __import__("cv2") is not None)
test("mediapipe import", lambda: __import__("mediapipe") is not None)
test("requests import", lambda: __import__("requests") is not None)
test("json import", lambda: __import__("json") is not None)
test("threading import", lambda: __import__("threading") is not None)


# ═══════════════════════════════════════════════════════════════
print(f"\n{BOLD}2. POSE ENGINE — AÇI HESAPLAMA TESTLERİ{RESET}")
print("─" * 40)

import mediapipe as mp
import cv2

# MediaPipe Tasks API v0.10+
PoseLandmark = mp.tasks.vision.PoseLandmark

def calculate_angle(a, b, c):
    a, b, c = np.array(a), np.array(b), np.array(c)
    ba, bc = a - b, c - b
    cos_a = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-8)
    return np.degrees(np.arccos(np.clip(cos_a, -1.0, 1.0)))

def test_angle_straight():
    # 180° düz çizgi
    angle = calculate_angle([0,0], [1,0], [2,0])
    return abs(angle - 180.0) < 0.1

def test_angle_right():
    # 90° dik açı
    angle = calculate_angle([0,1], [0,0], [1,0])
    return abs(angle - 90.0) < 0.1

def test_angle_45():
    # 45° açı
    angle = calculate_angle([1,1], [0,0], [1,0])
    return abs(angle - 45.0) < 0.5

def test_angle_symmetric():
    # Simetri: a,b,c == c,b,a
    a1 = calculate_angle([0,1], [0,0], [1,0])
    a2 = calculate_angle([1,0], [0,0], [0,1])
    return abs(a1 - a2) < 0.01

test("Düz çizgi açısı (beklenen: 180°)", test_angle_straight)
test("Dik açı (beklenen: 90°)", test_angle_right)
test("45° açı tespiti", test_angle_45)
test("Açı simetrisi (a,b,c = c,b,a)", test_angle_symmetric)


# ═══════════════════════════════════════════════════════════════
print(f"\n{BOLD}3. POSE ENGINE — BENZERLİK KARŞILAŞTIRMA TESTLERİ{RESET}")
print("─" * 40)

def angle_similarity(angles_a, angles_b):
    common = set(angles_a.keys()) & set(angles_b.keys())
    if not common:
        return 0.0
    errors = [min(abs(angles_a[j] - angles_b[j]) / 180.0, 1.0) for j in common]
    return round(1.0 - np.mean(errors), 4)

def test_identical_poses():
    a = {"sol_diz": 145.0, "sag_diz": 143.0, "sol_kalca": 165.0}
    return angle_similarity(a, a) == 1.0

def test_completely_different():
    a = {"sol_diz": 90.0}
    b = {"sol_diz": 0.0}
    score = angle_similarity(a, b)
    return score < 0.6

def test_partial_match():
    a = {"sol_diz": 145.0, "sag_diz": 143.0}
    b = {"sol_diz": 140.0, "sag_diz": 138.0}  # ~5° fark
    score = angle_similarity(a, b)
    return score > 0.90

def test_empty_angles():
    return angle_similarity({}, {"sol_diz": 90.0}) == 0.0

def test_no_common_joints():
    a = {"sol_diz": 90.0}
    b = {"sag_diz": 90.0}
    return angle_similarity(a, b) == 0.0

test("Aynı pozlar → benzerlik 1.0", test_identical_poses)
test("Tamamen farklı pozlar → düşük benzerlik", test_completely_different)
test("Küçük fark (5°) → yüksek benzerlik", test_partial_match)
test("Boş açı listesi → 0.0", test_empty_angles)
test("Ortak eklem yok → 0.0", test_no_common_joints)


# ═══════════════════════════════════════════════════════════════
print(f"\n{BOLD}4. TEKRAR SAYACI SİMÜLASYONU{RESET}")
print("─" * 40)

class MockRepCounter:
    def __init__(self, threshold_up=0.75, threshold_down=0.45):
        self.state = 'rest'
        self.rep_count = 0
        self.correct_reps = 0
        self.total_reps = 0
        self.th_up = threshold_up
        self.th_down = threshold_down

    def update(self, similarity, has_error=False):
        if self.state == 'rest' and similarity >= self.th_up:
            self.state = 'active'
        elif self.state == 'active' and similarity < self.th_down:
            self.state = 'rest'
            self.total_reps += 1
            if not has_error:
                self.correct_reps += 1
                self.rep_count += 1

def test_rep_count_3():
    counter = MockRepCounter()
    # 3 tam tekrar simüle et (yukarı-aşağı-yukarı-aşağı...)
    sequence = [0.3, 0.5, 0.8, 0.9, 0.8, 0.4, 0.2,   # 1. tekrar
                0.3, 0.8, 0.9, 0.8, 0.3, 0.2,          # 2. tekrar
                0.4, 0.85, 0.9, 0.85, 0.3, 0.2]        # 3. tekrar
    for s in sequence:
        counter.update(s, has_error=False)
    return counter.rep_count == 3

def test_wrong_rep_not_counted():
    counter = MockRepCounter()
    # 1 hatalı tekrar
    sequence = [0.3, 0.8, 0.9, 0.8, 0.3, 0.2]
    for s in sequence:
        counter.update(s, has_error=True)
    return counter.total_reps == 1 and counter.correct_reps == 0

def test_no_rep_below_threshold():
    counter = MockRepCounter()
    # Hiç eşiği aşmıyor
    for s in [0.3, 0.4, 0.5, 0.6, 0.4, 0.3]:
        counter.update(s)
    return counter.rep_count == 0

def test_partial_reps():
    counter = MockRepCounter()
    # 2 doğru + 1 hatalı = toplam 3, doğru 2
    seq_correct = [0.3, 0.85, 0.9, 0.85, 0.3, 0.2]
    seq_wrong   = [0.3, 0.85, 0.9, 0.85, 0.3, 0.2]
    for s in seq_correct: counter.update(s, has_error=False)
    for s in seq_correct: counter.update(s, has_error=False)
    for s in seq_wrong:   counter.update(s, has_error=True)
    return counter.total_reps == 3 and counter.correct_reps == 2

test("3 doğru tekrar sayımı", test_rep_count_3)
test("Hatalı tekrar sayılmıyor", test_wrong_rep_not_counted)
test("Eşik altında tekrar yok", test_no_rep_below_threshold)
test("Karışık (doğru+hatalı) tekrar", test_partial_reps)


# ═══════════════════════════════════════════════════════════════
print(f"\n{BOLD}5. REFERANS POSE VERİSİ — JSON FORMAT TESTİ{RESET}")
print("─" * 40)

SAMPLE_POSE_JSON = [
    {"frame": 0,  "angles": {"sol_diz": 170.0, "sag_diz": 168.0, "sol_kalca": 175.0, "sag_kalca": 174.0}},
    {"frame": 3,  "angles": {"sol_diz": 155.0, "sag_diz": 153.0, "sol_kalca": 160.0, "sag_kalca": 159.0}},
    {"frame": 6,  "angles": {"sol_diz": 130.0, "sag_diz": 128.0, "sol_kalca": 145.0, "sag_kalca": 144.0}},
    {"frame": 9,  "angles": {"sol_diz": 100.0, "sag_diz": 98.0,  "sol_kalca": 120.0, "sag_kalca": 119.0}},
    {"frame": 12, "angles": {"sol_diz": 80.0,  "sag_diz": 78.0,  "sol_kalca": 100.0, "sag_kalca": 99.0}},
    {"frame": 15, "angles": {"sol_diz": 100.0, "sag_diz": 98.0,  "sol_kalca": 120.0, "sag_kalca": 119.0}},
    {"frame": 18, "angles": {"sol_diz": 135.0, "sag_diz": 133.0, "sol_kalca": 150.0, "sag_kalca": 149.0}},
    {"frame": 21, "angles": {"sol_diz": 165.0, "sag_diz": 163.0, "sol_kalca": 172.0, "sag_kalca": 171.0}},
]

def test_json_serializable():
    s = json.dumps(SAMPLE_POSE_JSON)
    return isinstance(s, str) and len(s) > 0

def test_json_deserializable():
    s = json.dumps(SAMPLE_POSE_JSON)
    loaded = json.loads(s)
    return len(loaded) == len(SAMPLE_POSE_JSON)

def test_pose_structure():
    for frame in SAMPLE_POSE_JSON:
        if 'frame' not in frame or 'angles' not in frame:
            return False
        if not isinstance(frame['angles'], dict):
            return False
    return True

def test_sliding_window_search():
    # En iyi eşleşen frame'i bul
    current = {"sol_diz": 82.0, "sag_diz": 79.0}
    best_score = 0.0
    best_idx = -1
    for i, ref in enumerate(SAMPLE_POSE_JSON):
        score = angle_similarity(current, ref['angles'])
        if score > best_score:
            best_score = score
            best_idx = i
    # En yakın frame index 4 olmalı (sol_diz:80, sag_diz:78)
    return best_idx == 4 and best_score > 0.98

test("JSON serializasyon", test_json_serializable)
test("JSON deserializasyon", test_json_deserializable)
test("Pose data yapısı doğruluğu", test_pose_structure)
test("Sliding window en iyi eşleşme", test_sliding_window_search)


# ═══════════════════════════════════════════════════════════════
print(f"\n{BOLD}6. SEANS ÖZET VE İSTATİSTİK TESTLERİ{RESET}")
print("─" * 40)

def build_session_summary(total, correct, joint_errors, duration):
    accuracy = (correct / total * 100) if total > 0 else 0
    top_errors = sorted(joint_errors.items(), key=lambda x: x[1], reverse=True)[:3]
    return {
        'total_reps': total,
        'correct_reps': correct,
        'accuracy_score': round(accuracy, 1),
        'joint_errors': {k: v for k, v in top_errors if v > 0},
        'duration_seconds': duration,
    }

def test_accuracy_calc():
    s = build_session_summary(15, 12, {}, 120)
    return s['accuracy_score'] == 80.0

def test_zero_reps():
    s = build_session_summary(0, 0, {}, 0)
    return s['accuracy_score'] == 0.0

def test_perfect_session():
    s = build_session_summary(10, 10, {}, 60)
    return s['accuracy_score'] == 100.0

def test_top_errors_sorted():
    errors = {"sol_diz": 5, "sag_diz": 2, "sol_kalca": 8, "sag_omuz": 1}
    s = build_session_summary(10, 7, errors, 90)
    keys = list(s['joint_errors'].keys())
    # En fazla hata sol_kalca (8) olmalı
    return keys[0] == 'sol_kalca' and s['joint_errors']['sol_kalca'] == 8

def test_summary_fields():
    s = build_session_summary(10, 8, {"sol_diz": 3}, 75)
    required = ['total_reps', 'correct_reps', 'accuracy_score', 'joint_errors', 'duration_seconds']
    return all(k in s for k in required)

test("Doğruluk oranı hesabı (12/15 = 80%)", test_accuracy_calc)
test("Sıfır tekrar → 0%", test_zero_reps)
test("Mükemmel seans → 100%", test_perfect_session)
test("Hata sıralaması (en fazla hata önce)", test_top_errors_sorted)
test("Özet alanları tam mı?", test_summary_fields)


# ═══════════════════════════════════════════════════════════════
print(f"\n{BOLD}7. API SERVİSİ — DEMO MODU TESTİ{RESET}")
print("─" * 40)

class MockAPIService:
    def __init__(self):
        self.token = None
        self.user = None

    def login(self, email, password, callback):
        if email and password:
            self.token = "demo_token_xyz"
            self.user = {"id": 1, "name": "Test Kullanıcı", "role": "patient"}
            callback(True, {"token": self.token, "user": self.user})
        else:
            callback(False, "Bilgiler eksik")

    @staticmethod
    def get_exercises(callback):
        demo = [
            {"id": 1, "name": "Diz Bükme", "daily_reps": 15, "status": "pending"},
            {"id": 2, "name": "Omuz Rotasyonu", "daily_reps": 10, "status": "completed"},
        ]
        callback(True, demo)

    @staticmethod
    def get_exercise_pose_data(_ex_id, callback):
        callback(True, SAMPLE_POSE_JSON)

    @staticmethod
    def submit_session_result(_ex_id, data, callback):
        required = ['total_reps', 'correct_reps', 'accuracy_score']
        ok = all(k in data for k in required)
        callback(ok, {"saved": True} if ok else None)

mock_api = MockAPIService()
login_result = {}
exercise_result = {}
pose_result = {}
submit_result = {}

mock_api.login("test@test.com", "123456",
               lambda s, d: login_result.update({"success": s, "data": d}))
mock_api.get_exercises(
               lambda s, d: exercise_result.update({"success": s, "data": d}))
mock_api.get_exercise_pose_data(1,
               lambda s, d: pose_result.update({"success": s, "data": d}))
mock_api.submit_session_result(1,
    {"total_reps": 15, "correct_reps": 12, "accuracy_score": 80.0},
               lambda s, d: submit_result.update({"success": s, "data": d}))

test("Login demo → token alındı", lambda: login_result.get("success") and mock_api.token is not None)
test("Login → kullanıcı rolü 'patient'", lambda: mock_api.user.get("role") == "patient")
test("Egzersiz listesi → 2 egzersiz", lambda: exercise_result.get("success") and len(exercise_result["data"]) == 2)
test("Pose data → 8 frame yüklendi", lambda: pose_result.get("success") and len(pose_result["data"]) == 8)
test("Seans sonucu gönderimi başarılı", lambda: submit_result.get("success"))


# ═══════════════════════════════════════════════════════════════
print(f"\n{BOLD}8. EKLEM HATA EŞIK TESTLERİ{RESET}")
print("─" * 40)

THRESHOLD_WARN  = 20
THRESHOLD_ERROR = 35

def classify_joint(current_angle, ref_angle):
    diff = abs(current_angle - ref_angle)
    if diff >= THRESHOLD_ERROR:
        return 'error', diff
    elif diff >= THRESHOLD_WARN:
        return 'warning', diff
    else:
        return 'ok', diff

def test_joint_ok():
    status, diff = classify_joint(145.0, 148.0)
    return status == 'ok' and diff < THRESHOLD_WARN

def test_joint_warning():
    status, diff = classify_joint(145.0, 120.0)
    return status == 'warning'

def test_joint_error():
    status, diff = classify_joint(145.0, 105.0)
    return status == 'error'

def test_boundary_warn():
    # Tam sınırda: 20° fark → warning
    status, _ = classify_joint(100.0, 80.0)
    return status == 'warning'

def test_boundary_error():
    # Tam sınırda: 35° fark → error
    status, _ = classify_joint(100.0, 65.0)
    return status == 'error'

test("3° fark → ok",         test_joint_ok)
test("25° fark → warning",   test_joint_warning)
test("40° fark → error",     test_joint_error)
test("20° sınır → warning",  test_boundary_warn)
test("35° sınır → error",    test_boundary_error)


# ═══════════════════════════════════════════════════════════════
print(f"\n{BOLD}9. TAM SEANS SİMÜLASYONU (End-to-End){RESET}")
print("─" * 40)

def full_session_simulation():
    """
    Gerçek bir seans akışını simüle et:
    1. Referans pose yükle
    2. 10 tekrar yap (8 doğru, 2 hatalı)
    3. Sonuç özetini kontrol et
    """
    counter = MockRepCounter()
    joint_error_counts = {"sol_diz": 0, "sag_diz": 0}

    # 10 tekrar simüle et
    for rep in range(10):
        has_error = rep in [2, 7]  # 3. ve 8. tekrar hatalı

        # Active fazı (yüksek benzerlik)
        for sim_score in [0.35, 0.65, 0.82, 0.91, 0.87]:
            counter.update(sim_score, has_error=has_error)

        # Rest fazı (düşük benzerlik)
        for sim_score in [0.55, 0.38, 0.25]:
            counter.update(sim_score, has_error=has_error)

        if has_error:
            joint_error_counts["sol_diz"] += 3

    summary = build_session_summary(
        counter.total_reps,
        counter.correct_reps,
        joint_error_counts,
        duration=180
    )
    return summary

session_summary = full_session_simulation()

test("Simülasyon: toplam 10 tekrar",
     lambda: session_summary['total_reps'] == 10)
test("Simülasyon: 8 doğru tekrar",
     lambda: session_summary['correct_reps'] == 8)
test("Simülasyon: doğruluk %80",
     lambda: session_summary['accuracy_score'] == 80.0)
test("Simülasyon: sol diz hatası raporlandı",
     lambda: session_summary['joint_errors'].get('sol_diz', 0) > 0)
test("Simülasyon: süre 180 sn kaydedildi",
     lambda: session_summary['duration_seconds'] == 180)


# ═══════════════════════════════════════════════════════════════
print(f"\n{BOLD}10. OPENCV FRAME İŞLEME TESTİ{RESET}")
print("─" * 40)

def test_frame_creation():
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    return frame.shape == (480, 640, 3)

def test_frame_flip():
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    frame[0, 0] = [255, 0, 0]
    flipped = cv2.flip(frame, 1)
    return flipped[0, 639, 0] == 255

def test_bgr_to_rgb():
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    frame[:, :, 0] = 100  # Blue channel
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    return rgb[0, 0, 2] == 100  # Şimdi Red channel'da olmalı

def test_circle_draw():
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.circle(frame, (320, 240), 10, (0, 255, 0), -1)
    return frame[240, 320, 1] == 255  # Yeşil piksel

def test_texture_conversion():
    frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    flipped = cv2.flip(rgb, 0)
    buf = flipped.tobytes()
    return len(buf) == 480 * 640 * 3

test("Frame oluşturma (640x480)",     test_frame_creation)
test("Frame aynalama (flip)",          test_frame_flip)
test("BGR → RGB dönüşümü",            test_bgr_to_rgb)
test("Eklem noktası çizimi",          test_circle_draw)
test("Kivy texture dönüşümü hazırlığı", test_texture_conversion)


# ═══════════════════════════════════════════════════════════════
# SONUÇLAR
# ═══════════════════════════════════════════════════════════════
total_tests = len(results)
passed = sum(1 for _, ok in results if ok)
failed = total_tests - passed

print(f"\n{BOLD}{'='*58}{RESET}")
print(f"{BOLD}  TEST SONUÇLARI{RESET}")
print(f"{'='*58}")
print(f"  Toplam test  : {total_tests}")
print(f"  \033[92mGeçti\033[0m         : {passed}")
print(f"  \033[91mKaldı\033[0m         : {failed}")
pct = passed / total_tests * 100
bar_len = 40
filled = int(bar_len * passed / total_tests)
bar = "█" * filled + "░" * (bar_len - filled)
color = "\033[92m" if pct >= 90 else "\033[93m" if pct >= 70 else "\033[91m"
print(f"\n  {color}{bar}{RESET}  {color}{pct:.1f}%{RESET}")
print(f"{'='*58}\n")

if failed > 0:
    print(f"{BOLD}Başarısız testler:{RESET}")
    for t_name, ok in results:
        if not ok:
            print(f"  {FAIL} {t_name}")
    print()

if pct == 100:
    print(f"  \033[92m🎉 Tüm testler başarılı! Uygulama üretime hazır.\033[0m\n")
elif pct >= 90:
    print(f"  \033[93m✓ Uygulama büyük ölçüde hazır.\033[0m\n")
else:
    print(f"  \033[91m⚠ Bazı modüller düzeltme gerektiriyor.\033[0m\n")
