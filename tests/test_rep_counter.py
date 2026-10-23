"""Sentetik aci sinyalleriyle RepCounter testleri."""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.rep_counter import RepCounter, build_profiles


def _signal(n_reps, period=2.0, fps=30.0, amplitude=1.0, start=160.0, peak=40.0):
    samples = []
    dt = 1.0 / fps
    total = n_reps * period
    t = 0.0
    while t < total - 1e-9:
        phase = (t % period) / period
        progress = math.sin(math.pi * phase) * amplitude
        angle = start + (peak - start) * progress
        samples.append((t, angle))
        t += dt
    return samples


def _profiles_from_full(n_reps=4, period=2.0):
    track = [angle for _t, angle in _signal(n_reps, period=period, amplitude=1.0)]
    return build_profiles({'sol_dirsek': track})


def _feed(counter, samples, drop_every=0):
    for index, (t, angle) in enumerate(samples):
        if drop_every and index % drop_every == 0:
            continue
        counter.update({'sol_dirsek': angle}, now=t, quality=1.0, visibility={'sol_dirsek': 1.0})
    return counter.count


class RepCounterTests(unittest.TestCase):
    def test_n_reps(self):
        profiles = _profiles_from_full(4)
        self.assertTrue(profiles)
        counter = RepCounter()
        counter.configure(profiles)
        self.assertEqual(_feed(counter, _signal(4)), 4)

    def test_tempo_invariant(self):
        profiles = _profiles_from_full(3, period=2.0)
        for speed in (0.6, 1.5):
            counter = RepCounter()
            counter.configure(profiles)
            samples = _signal(3, period=2.0 / speed)
            self.assertEqual(_feed(counter, samples), 3, msg=f'speed={speed}')

    def test_dropped_frames(self):
        profiles = _profiles_from_full(4)
        counter = RepCounter()
        counter.configure(profiles)
        self.assertEqual(_feed(counter, _signal(4), drop_every=5), 4)

    def test_standing_still(self):
        profiles = _profiles_from_full(2)
        counter = RepCounter()
        counter.configure(profiles)
        start = profiles[0]['start']
        samples = [(t / 10.0, start) for t in range(300)]
        self.assertEqual(_feed(counter, samples), 0)

    def test_half_amplitude_is_not_counted(self):
        profiles = _profiles_from_full(3)
        counter = RepCounter()
        counter.configure(profiles)
        self.assertEqual(_feed(counter, _signal(3, amplitude=0.50)), 0)

    def test_seventy_five_percent_counts(self):
        profiles = _profiles_from_full(3)
        counter = RepCounter()
        counter.configure(profiles)
        self.assertEqual(_feed(counter, _signal(3, amplitude=0.75)), 3)

    def test_two_reps_without_pause(self):
        profiles = _profiles_from_full(2, period=2.0)
        counter = RepCounter()
        counter.configure(profiles)
        self.assertEqual(_feed(counter, _signal(2, period=2.0)), 2)


def _arm_samples(n_reps, elbow_for_rep=None, period=2.0):
    from services.rep_counter import build_joint_model
    shoulders = _signal(n_reps, period=period, start=30.0, peak=120.0)
    samples = []
    for t, shoulder in shoulders:
        rep_index = int(t // period)
        elbow = 90.0
        if elbow_for_rep:
            elbow = elbow_for_rep(rep_index, t, period)
        samples.append((t, {'sol_omuz': shoulder, 'sol_dirsek': elbow}))
    return samples


def _arm_counter(samples):
    from services.rep_counter import build_joint_model
    tracks = {'sol_omuz': [], 'sol_dirsek': []}
    for _t, angles in samples:
        tracks['sol_omuz'].append(angles['sol_omuz'])
        tracks['sol_dirsek'].append(90.0)
    leads, stable = build_joint_model(tracks, len(samples))
    counter = RepCounter()
    counter.configure(leads, stable)
    return counter


class FormCheckTests(unittest.TestCase):
    def test_stable_elbow_counts(self):
        samples = _arm_samples(4, lambda *_a: 90.0)
        counter = _arm_counter(samples)
        self.assertEqual(_feed_angles(counter, samples), 4)
        self.assertEqual(counter.attempts, 0)

    def test_straight_elbow_is_form_failure(self):
        samples = _arm_samples(4, lambda *_a: 170.0)
        counter = _arm_counter(samples)
        self.assertEqual(_feed_angles(counter, samples), 0)
        self.assertEqual(counter.attempts, 4)

    def test_elbow_noise_within_tolerance(self):
        def elbow(rep_index, t, period):
            return 90.0 + (10.0 if int(t * 10) % 2 == 0 else -10.0)
        samples = _arm_samples(3, elbow)
        counter = _arm_counter(samples)
        self.assertEqual(_feed_angles(counter, samples), 3)

    def test_one_bad_rep_of_ten(self):
        def elbow(rep_index, _t, _period):
            return 170.0 if rep_index == 4 else 90.0
        samples = _arm_samples(10, elbow)
        counter = _arm_counter(samples)
        self.assertEqual(_feed_angles(counter, samples), 9)
        self.assertEqual(counter.attempts, 1)


def _feed_angles(counter, samples):
    for t, angles in samples:
        visibility = {name: 1.0 for name in angles}
        counter.update(angles, now=t, quality=1.0, visibility=visibility)
    return counter.count


class ReferenceVideoIntegrationTests(unittest.TestCase):
    def test_doctor_video_rep_count_matches_reference(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        candidates = []
        for folder in (
            os.path.join(root, 'data', 'cache'),
            os.path.join(root, 'data', 'videos'),
        ):
            if not os.path.isdir(folder):
                continue
            for name in os.listdir(folder):
                if name.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
                    candidates.append(os.path.join(folder, name))
        if not candidates:
            self.skipTest('Doktor videosu yok')

        from services.pose_engine import PoseEngine, preprocess_frame
        import cv2

        video_path = candidates[0]
        engine = PoseEngine()
        try:
            reference = engine.extract_reference_from_video(video_path)
            profiles = reference.get('rep_profile') or []
            self.assertTrue(profiles)
            self.assertGreater(len(reference.get('frames', [])), 8)

            cap = cv2.VideoCapture(video_path)
            fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
            if fps <= 1:
                fps = 30.0
            cap.release()

            expected = RepCounter()
            expected.configure(profiles)
            for item in reference.get('frames', []):
                frame_index = int(item.get('frame', 0))
                angles = item.get('angles', {})
                visibility = {name: 1.0 for name in angles}
                expected.update(angles, now=frame_index / fps, quality=1.0, visibility=visibility)

            engine.rep_counter.reset()
            engine.rep_count = 0
            engine._replay_time = 0.0
            engine._replay_dt = 1.0 / fps
            engine._last_landmarks = None
            engine._recreate_landmarker()
            cap = cv2.VideoCapture(video_path)
            while cap.isOpened():
                ok, frame = cap.read()
                if not ok:
                    break
                engine.process_frame(preprocess_frame(frame))
            cap.release()
            self.assertEqual(engine.rep_count, expected.count)
        finally:
            engine.release()


if __name__ == '__main__':
    unittest.main()
