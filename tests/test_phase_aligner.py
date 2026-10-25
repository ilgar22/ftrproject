"""Sentetik aci serileriyle faz hizalayici testleri (cv2/mediapipe gerekmez)."""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

from services.phase_aligner import OnlineAligner, build_template, segment_reps

FPS = 30.0


def squat_frames(reps, rep_sec, knee_depth=90.0, noise=2.0, hip_bias=0.0, seed=0, rest_sec=0.5,
                 with_points=True, hand_offset=(0.0, 0.0, 0.0)):
    """Comelme: diz 175 -> depth -> 175, kalca 170 -> 110 -> 170, omuz sabit ~20.
    Uc noktalar: eller yanlarda asagida, ayaklar omuz genisliginde sabit (govde birimi)."""
    rng = np.random.default_rng(seed)
    frames = []
    idx = 0

    def push(k, h, s=0.0):
        nonlocal idx
        item = {'frame': idx, 'angles': {
            'sol_diz': k + rng.normal(0, noise), 'sag_diz': k + rng.normal(0, noise),
            'sol_kalca': h + hip_bias + rng.normal(0, noise), 'sag_kalca': h + hip_bias + rng.normal(0, noise),
            'sol_omuz': 20 + rng.normal(0, noise), 'sag_omuz': 20 + rng.normal(0, noise),
            'sol_dirsek': 170 + rng.normal(0, noise), 'sag_dirsek': 170 + rng.normal(0, noise),
        }}
        if with_points:
            pn = 0.02
            ox, oy, oz = hand_offset
            item['points'] = {
                'sol_el_x': -0.45 + ox + rng.normal(0, pn), 'sol_el_y': 0.55 + 0.1 * s + oy + rng.normal(0, pn), 'sol_el_z': 0.05 + oz + rng.normal(0, pn),
                'sag_el_x': 0.45 + rng.normal(0, pn), 'sag_el_y': 0.55 + 0.1 * s + rng.normal(0, pn), 'sag_el_z': 0.05 + rng.normal(0, pn),
                'sol_ayak_x': -0.35 + rng.normal(0, pn), 'sol_ayak_y': 2.0 - 0.6 * s + rng.normal(0, pn), 'sol_ayak_z': 0.0 + rng.normal(0, pn),
                'sag_ayak_x': 0.35 + rng.normal(0, pn), 'sag_ayak_y': 2.0 - 0.6 * s + rng.normal(0, pn), 'sag_ayak_z': 0.0 + rng.normal(0, pn),
            }
        frames.append(item)
        idx += 1

    for _ in range(int(rest_sec * FPS)):
        push(175.0, 170.0, 0.0)
    for r in range(reps):
        depth = knee_depth if not isinstance(knee_depth, list) else knee_depth[r]
        n = int(rep_sec * FPS)
        for t in range(n):
            s = 0.5 - 0.5 * math.cos(2 * math.pi * t / n)   # 0 -> 1 -> 0
            push(175.0 - (175.0 - depth) * s, 170.0 - 60.0 * s, s)
        for _ in range(int(rest_sec * FPS)):
            push(175.0, 170.0, 0.0)
    return frames


def run(aligner, frames):
    t = 0.0
    counted, reasons = 0, []
    for f in frames:
        d = aligner.step({**f['angles'], **f.get('points', {})}, now=t)
        t += 1.0 / FPS
        if d['counted']:
            counted += 1
        elif d['reason'] in ('form', 'amplitude', 'too_long'):
            reasons.append(d['reason'])
    return counted, reasons


def test_template_segments_reference_reps():
    ref = squat_frames(reps=4, rep_sec=2.0)
    tpl = build_template(ref)
    assert tpl is not None
    assert tpl['rep_count'] == 4, tpl['rep_count']
    assert 'sol_diz' in tpl['lead_joints'] or 'sag_diz' in tpl['lead_joints']
    assert tpl['peak_phase'] > tpl['phases'] * 0.3
    print('OK  sablon: 4 tekrar bolutlendi, tepe faz =', tpl['peak_phase'])


def test_counts_same_tempo():
    tpl = build_template(squat_frames(reps=4, rep_sec=2.0))
    counted, reasons = run(OnlineAligner(tpl), squat_frames(reps=5, rep_sec=2.0, seed=7))
    assert counted == 5, (counted, reasons)
    print('OK  ayni tempo: 5/5 sayildi')


def test_counts_faster_and_slower_tempo():
    tpl = build_template(squat_frames(reps=4, rep_sec=2.0))
    c_fast, r_fast = run(OnlineAligner(tpl), squat_frames(reps=5, rep_sec=1.1, seed=3))
    c_slow, r_slow = run(OnlineAligner(tpl), squat_frames(reps=5, rep_sec=3.6, seed=4))
    assert c_fast == 5, (c_fast, r_fast)
    assert c_slow == 5, (c_slow, r_slow)
    print('OK  tempo farki: hizli 5/5, yavas 5/5')


def test_shallow_rep_not_counted():
    tpl = build_template(squat_frames(reps=4, rep_sec=2.0))
    # 3. tekrar yarim (diz sadece 150'ye iniyor)
    pat = squat_frames(reps=5, rep_sec=2.0, knee_depth=[90, 90, 150, 90, 90], seed=5)
    counted, reasons = run(OnlineAligner(tpl), pat)
    assert counted == 4, (counted, reasons)
    assert 'amplitude' in reasons or 'form' in reasons, reasons
    print('OK  yarim tekrar sayilmadi: 4/5, red nedeni =', reasons)


def test_wrong_form_flagged():
    tpl = build_template(squat_frames(reps=4, rep_sec=2.0))
    pat = squat_frames(reps=3, rep_sec=2.0, hip_bias=45.0, seed=6)  # kalca surekli 45 derece sapik
    al = OnlineAligner(tpl)
    errors = 0
    t = 0.0
    for f in pat:
        d = al.step({**f['angles'], **f.get('points', {})}, now=t)
        t += 1.0 / FPS
        st, _ = al.joint_status(d.get('z'))
        if st.get('sol_kalca') == 'error':
            errors += 1
    assert errors > len(pat) * 0.5, errors
    print(f'OK  hatali kalca {errors}/{len(pat)} karede "error" olarak isaretlendi; sayilan={al.count}, deneme={al.attempts}')


def test_standing_still_counts_nothing():
    tpl = build_template(squat_frames(reps=4, rep_sec=2.0))
    counted, _ = run(OnlineAligner(tpl), squat_frames(reps=0, rep_sec=2.0, rest_sec=20.0))
    assert counted == 0
    print('OK  hareketsiz: 0 sayim')


def test_wrong_hand_position_flagged():
    tpl = build_template(squat_frames(reps=4, rep_sec=2.0))
    # sol el yanlis konumda (one/yukari uzatilmis), eklem acilari dogru
    pat = squat_frames(reps=3, rep_sec=2.0, seed=11, hand_offset=(0.9, -0.8, 0.0))
    al = OnlineAligner(tpl)
    errors = 0
    t = 0.0
    for f in pat:
        d = al.step({**f['angles'], **f['points']}, now=t)
        t += 1.0 / FPS
        st, _ = al.joint_status(d.get('z'))
        if st.get('sol_el') == 'error':
            errors += 1
    assert errors > len(pat) * 0.5, errors
    print(f'OK  yanlis el konumu {errors}/{len(pat)} karede "error"; sayilan={al.count}, deneme={al.attempts}')


def test_frames_without_points_still_work():
    tpl = build_template(squat_frames(reps=4, rep_sec=2.0, with_points=False))
    counted, reasons = run(OnlineAligner(tpl), squat_frames(reps=5, rep_sec=2.0, seed=12, with_points=False))
    assert counted == 5, (counted, reasons)
    print('OK  konum verisi olmadan (eski bicim): 5/5')


def test_single_rep_reference():
    tpl = build_template(squat_frames(reps=1, rep_sec=2.0))
    assert tpl['rep_count'] == 1
    counted, reasons = run(OnlineAligner(tpl), squat_frames(reps=3, rep_sec=2.0, seed=9))
    assert counted == 3, (counted, reasons)
    print('OK  tek tekrarli referans: 3/3')


if __name__ == '__main__':
    for name, fn in list(globals().items()):
        if name.startswith('test_'):
            fn()
    print('TUM TESTLER GECTI')
