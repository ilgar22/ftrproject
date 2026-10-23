"""Doctor exercise templates.

Templates keep one shared video. Assigning a template to a patient stores the
same video_url and does not copy the file. Deleting a template leaves assigned
exercises and that video in place.
"""

import os
from datetime import datetime, timedelta

from services import database as db


class ApiError(Exception):
    def __init__(self, status_code, detail):
        super().__init__(detail)
        self.status_code = int(status_code)
        self.detail = detail


def _now_stamp(not_before=None):
    stamp = datetime.now()
    if not_before:
        previous = datetime.fromisoformat(not_before)
        if stamp <= previous:
            stamp = previous + timedelta(microseconds=1)
    return stamp.isoformat(timespec='microseconds')


def _require_doctor(user):
    if not user or user.get('id') is None or not user.get('role'):
        raise ApiError(401, 'Giris gerekli')
    if user.get('role') not in ('doctor', 'physiotherapist'):
        raise ApiError(403, 'Sadece doktor erisebilir')
    return int(user['id'])


def validate_name(name):
    if not isinstance(name, str):
        raise ApiError(422, 'Ad 1-60 karakter olmali')
    clean = name.strip()
    if not clean or len(clean) > 60:
        raise ApiError(422, 'Ad 1-60 karakter olmali')
    return clean


def _require_daily_reps(value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ApiError(422, 'daily_reps pozitif tam sayi olmali')
    if value < 1:
        raise ApiError(422, 'daily_reps pozitif tam sayi olmali')
    return value


def _own_template(doctor_id, template_id):
    try:
        template_id = int(template_id)
    except (TypeError, ValueError):
        raise ApiError(404, 'Sablon bulunamadi')
    row = db.get_template(template_id)
    if not row:
        raise ApiError(404, 'Sablon bulunamadi')
    if int(row['doctor_id']) != int(doctor_id):
        raise ApiError(403, 'Bu kayit size ait degil')
    return row


def _public_template(row):
    media_id = row.get('media_id')
    video_path = None
    thumb_path = None
    if media_id:
        exported = db.export_media(int(media_id))
        if exported:
            video_path, thumb_path = exported
    duration = row.get('duration_seconds')
    if duration is None:
        duration = 0
    return {
        'id': int(row['id']),
        'doctor_id': int(row['doctor_id']),
        'name': row['name'],
        'video_url': row.get('video_url'),
        'thumbnail_url': thumb_path or row.get('thumbnail_url'),
        'duration_seconds': int(duration),
        'created_at': row['created_at'],
        'updated_at': row['updated_at'],
        'media_id': int(media_id) if media_id is not None else None,
        'video_path': video_path,
        'thumbnail_path': thumb_path,
        'duration': int(duration),
    }


def _probe_video(video_path):
    import cv2

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        cap.release()
        raise ApiError(422, 'Video acilamadi')
    fps = cap.get(cv2.CAP_PROP_FPS) or 0
    frames = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
    duration = int(round(frames / fps)) if fps else 0
    ok, frame = cap.read()
    cap.release()
    if not ok or frame is None:
        raise ApiError(422, 'Video onizlemesi olusturulamadi')
    encoded, buffer = cv2.imencode('.jpg', frame)
    if not encoded:
        raise ApiError(422, 'Video onizlemesi olusturulamadi')
    return buffer.tobytes(), duration


def list_templates(user):
    doctor_id = _require_doctor(user)
    return [_public_template(row) for row in db.list_templates(doctor_id)]


def update_template(user, template_id, name):
    doctor_id = _require_doctor(user)
    row = _own_template(doctor_id, template_id)
    clean = validate_name(name)
    updated_at = _now_stamp(row.get('updated_at'))
    db.update_template_name(row['id'], clean, updated_at)
    saved = db.get_template(row['id'])
    return _public_template(saved)


def delete_template(user, template_id):
    doctor_id = _require_doctor(user)
    row = _own_template(doctor_id, template_id)
    db.delete_template(row['id'])
    return {'deleted': int(row['id'])}


def _exercise_from_template(template, exercise_id, patient_id, patient_name, daily_reps, description):
    media_id = template.get('media_id')
    video_path = None
    thumb_path = None
    if media_id:
        exported = db.export_media(int(media_id))
        if exported:
            video_path, thumb_path = exported
    return {
        'id': int(exercise_id),
        'name': template['name'],
        'daily_reps': int(daily_reps),
        'schedule': 'Gunluk',
        'status': 'pending',
        'description': description,
        'assigned_by': 'doctor',
        'assigned_patient_id': patient_id,
        'assigned_patient_name': patient_name or '',
        'template_id': int(template['id']),
        'video_url': template.get('video_url'),
        'video_media_id': int(media_id) if media_id is not None else None,
        'thumbnail_url': thumb_path or template.get('thumbnail_url'),
        'video_path': video_path,
    }


def assign_template(user, template_id, patient_id, daily_reps, patient_name='', exercise_id=None):
    doctor_id = _require_doctor(user)
    row = _own_template(doctor_id, template_id)
    if patient_id is None:
        raise ApiError(422, 'patient_id gerekli')
    reps = _require_daily_reps(daily_reps)
    if not row.get('media_id') or not row.get('video_url'):
        raise ApiError(422, 'Sablon videosu yok')
    if exercise_id is None:
        raise ApiError(422, 'exercise id gerekli')
    pose = db.template_pose(row['id']) or {'frames': [], 'profile': {}}
    exercise = _exercise_from_template(
        row, exercise_id, patient_id, patient_name, reps, 'Kutuphaneden atandi'
    )
    db.save_exercise(exercise, pose)
    return exercise, pose


def register_upload(user, name, video_path, pose_payload, assigned_patient_id=None,
                    assigned_patient_name='', daily_reps=10, schedule='Gunluk',
                    description='Doktor tarafindan yuklendi', exercise_id=None):
    """Store one video, create a template, and optionally assign it."""
    doctor_id = _require_doctor(user)
    clean = validate_name(name if isinstance(name, str) else '')
    if not video_path or not os.path.exists(video_path):
        raise ApiError(422, 'Video bulunamadi')
    thumbnail, duration = _probe_video(video_path)
    with open(video_path, 'rb') as handle:
        blob = handle.read()
    if not blob:
        raise ApiError(422, 'Video bos')
    media = db.insert_media(
        blob,
        os.path.basename(video_path),
        thumbnail,
        duration,
    )
    created = _now_stamp()
    template_id = db.insert_template(
        doctor_id,
        clean,
        media,
        pose_payload,
        created,
        created,
    )
    template_row = db.get_template(template_id)
    public = _public_template(template_row)
    exercise = None
    pose = pose_payload or {'frames': [], 'profile': {}}
    if assigned_patient_id is not None:
        reps = _require_daily_reps(daily_reps if isinstance(daily_reps, int) else int(daily_reps))
        if exercise_id is None:
            raise ApiError(422, 'exercise id gerekli')
        exercise = _exercise_from_template(
            template_row,
            exercise_id,
            assigned_patient_id,
            assigned_patient_name,
            reps,
            description,
        )
        exercise['schedule'] = schedule or 'Gunluk'
        db.save_exercise(exercise, pose)
    return public, exercise, pose


def patient_exercises(patient_id):
    """Exercises visible to one patient, including the doctor's daily_reps."""
    items = []
    for exercise in db.list_exercises():
        assigned = exercise.get('assigned_patient_id')
        if assigned is not None and str(assigned) != str(patient_id):
            continue
        row = dict(exercise)
        row['daily_reps'] = int(row['daily_reps']) if row.get('daily_reps') is not None else 0
        items.append(row)
    return items
