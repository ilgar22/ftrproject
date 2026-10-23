"""Exercise templates: ownership, shared video, thumbnail, daily_reps."""

import os
import tempfile
import unittest

import cv2
import numpy as np

from services import database as db
from services.exercise_library import ApiError
from services import exercise_library as library


def _clip(path):
    writer = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*'MJPG'), 10, (32, 32))
    if not writer.isOpened():
        raise RuntimeError('video writer failed')
    for index in range(10):
        frame = np.full((32, 32, 3), (0, 40 + index, 80), dtype=np.uint8)
        writer.write(frame)
    writer.release()


class ExerciseTemplateTests(unittest.TestCase):
    def setUp(self):
        self._orig = (db._DB_PATH, db._DIR, db._CACHE)
        self.tmp = tempfile.TemporaryDirectory()
        db.configure_storage(os.path.join(self.tmp.name, 'physio.db'))
        self.doctor = {'id': 7, 'role': 'doctor', 'name': 'Dr'}
        self.other = {'id': 8, 'role': 'doctor', 'name': 'Other'}
        self.patient_user = {'id': 3, 'role': 'patient', 'name': 'Hasta'}
        self.video = os.path.join(self.tmp.name, 'ref.avi')
        _clip(self.video)

    def tearDown(self):
        db._DB_PATH, db._DIR, db._CACHE = self._orig
        self.tmp.cleanup()

    def _upload(self, user, name, patient_id=4, reps=12, exercise_id=1000):
        return library.register_upload(
            user,
            name,
            self.video,
            {'frames': [{'frame': 0}], 'profile': {}},
            assigned_patient_id=patient_id,
            assigned_patient_name='Hasta',
            daily_reps=reps,
            exercise_id=exercise_id,
        )

    def test_upload_creates_template_thumbnail_and_shared_assign(self):
        before = db.count_media()
        template, exercise, _pose = self._upload(self.doctor, 'Omuz', reps=12, exercise_id=1000)
        self.assertEqual(db.count_media(), before + 1)
        self.assertEqual(template['doctor_id'], 7)
        self.assertEqual(template['name'], 'Omuz')
        self.assertTrue(template['video_url'].startswith('media://'))
        self.assertTrue(os.path.exists(template['thumbnail_url']))
        with open(template['thumbnail_url'], 'rb') as handle:
            self.assertEqual(handle.read(2), b'\xff\xd8')
        self.assertGreaterEqual(template['duration_seconds'], 1)
        self.assertEqual(exercise['video_url'], template['video_url'])
        self.assertEqual(exercise['daily_reps'], 12)
        self.assertEqual(exercise['video_path'], template['video_path'])

        again, _pose = library.assign_template(
            self.doctor, template['id'], 5, 8, patient_name='Ikinci', exercise_id=1001
        )
        self.assertEqual(db.count_media(), before + 1)
        self.assertEqual(again['video_url'], template['video_url'])
        self.assertEqual(again['video_media_id'], exercise['video_media_id'])
        self.assertEqual(db.media_blob_size(exercise['video_media_id']), db.media_blob_size(again['video_media_id']))

        listed = library.patient_exercises(5)
        match = next(item for item in listed if item['id'] == 1001)
        self.assertEqual(match['daily_reps'], 8)

        library.delete_template(self.doctor, template['id'])
        self.assertIsNone(db.get_template(template['id']))
        exported = db.export_media(exercise['video_media_id'])
        self.assertIsNotNone(exported)
        self.assertTrue(os.path.exists(exported[0]))
        self.assertGreater(os.path.getsize(exported[0]), 0)
        still = next(item for item in library.patient_exercises(4) if item['id'] == 1000)
        self.assertEqual(still['daily_reps'], 12)
        self.assertEqual(still['video_url'], template['video_url'])

    def test_owner_only_and_name_rules(self):
        first, _ex, _pose = self._upload(self.doctor, 'Bir', exercise_id=1100)
        second, _ex, _pose = self._upload(self.doctor, 'Iki', exercise_id=1101)
        listed = library.list_templates(self.doctor)
        self.assertEqual([item['id'] for item in listed], [second['id'], first['id']])
        self.assertEqual(library.list_templates(self.other), [])

        with self.assertRaises(ApiError) as other:
            library.update_template(self.other, first['id'], 'Hack')
        self.assertEqual(other.exception.status_code, 403)
        with self.assertRaises(ApiError) as missing:
            library.delete_template(self.doctor, 99999)
        self.assertEqual(missing.exception.status_code, 404)
        with self.assertRaises(ApiError) as patient:
            library.list_templates(self.patient_user)
        self.assertEqual(patient.exception.status_code, 403)
        with self.assertRaises(ApiError) as anon:
            library.list_templates(None)
        self.assertEqual(anon.exception.status_code, 401)

        for bad in ('', '   ', 'x' * 61, None):
            with self.assertRaises(ApiError) as err:
                library.update_template(self.doctor, first['id'], bad)
            self.assertEqual(err.exception.status_code, 422)

        renamed = library.update_template(self.doctor, first['id'], '  ' + ('n' * 60) + '  ')
        self.assertEqual(renamed['name'], 'n' * 60)
        self.assertGreater(renamed['updated_at'], first['updated_at'])
        self.assertEqual(renamed['created_at'], first['created_at'])

        with self.assertRaises(ApiError) as reps:
            library.assign_template(self.doctor, second['id'], 4, 0, exercise_id=1102)
        self.assertEqual(reps.exception.status_code, 422)


if __name__ == '__main__':
    unittest.main()
