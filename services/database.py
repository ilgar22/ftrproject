"""SQLite storage for exercises, pose JSON, and uploaded videos."""

import json
import os
import sqlite3
import threading
from datetime import datetime

_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
_DB_PATH = os.path.join(_DIR, 'physio.db')
_CACHE = os.path.join(_DIR, 'cache')
_lock = threading.Lock()


def configure_storage(db_path):
    """Point storage at another SQLite file. Used by tests."""
    global _DB_PATH, _DIR, _CACHE
    _DB_PATH = os.path.abspath(db_path)
    _DIR = os.path.dirname(_DB_PATH)
    _CACHE = os.path.join(_DIR, 'cache')


def _connect():
    os.makedirs(_DIR, exist_ok=True)
    conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')
    return conn


def init_db():
    with _lock:
        conn = _connect()
        conn.executescript(
            '''
            CREATE TABLE IF NOT EXISTS meta (
                key TEXT PRIMARY KEY,
                value TEXT
            );
            CREATE TABLE IF NOT EXISTS exercises (
                id INTEGER PRIMARY KEY,
                payload TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS pose_data (
                exercise_id INTEGER PRIMARY KEY,
                payload TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS videos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                exercise_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                filename TEXT,
                data BLOB NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_videos_ex_role
                ON videos(exercise_id, role, id);
            CREATE TABLE IF NOT EXISTS media (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT,
                data BLOB NOT NULL,
                thumbnail BLOB,
                duration_seconds INTEGER,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS exercise_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doctor_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                video_url TEXT,
                thumbnail_url TEXT,
                duration_seconds INTEGER,
                media_id INTEGER,
                pose_json TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_templates_doctor
                ON exercise_templates(doctor_id, created_at DESC, id DESC);
            CREATE TABLE IF NOT EXISTS library (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                video_path TEXT,
                thumbnail_path TEXT,
                duration REAL,
                created_at TEXT
            );
            '''
        )
        _migrate_legacy_library(conn)
        conn.commit()
        conn.close()


def _get_meta(conn, key, default):
    row = conn.execute('SELECT value FROM meta WHERE key = ?', (key,)).fetchone()
    return int(row['value']) if row else default


def load_state():
    init_db()
    with _lock:
        conn = _connect()
        exercises = []
        for row in conn.execute('SELECT payload FROM exercises ORDER BY id DESC'):
            exercises.append(json.loads(row['payload']))
        pose = {}
        for row in conn.execute('SELECT exercise_id, payload FROM pose_data'):
            pose[int(row['exercise_id'])] = json.loads(row['payload'])
        next_id = _get_meta(conn, 'next_exercise_id', 1000)
        paths = {}
        recordings = {}
        for ex in exercises:
            ex_id = int(ex['id'])
            doctor = _export_latest(conn, ex_id, 'doctor')
            media_id = ex.get('video_media_id')
            if media_id and not doctor:
                exported = _export_media(conn, int(media_id))
                doctor = exported[0] if exported else None
            patient = _export_latest(conn, ex_id, 'patient')
            if doctor:
                paths[ex_id] = doctor
            if patient:
                recordings[ex_id] = patient
                ex['patient_recording_path'] = patient
                if ex.get('last_result'):
                    ex['last_result']['patient_recording_path'] = patient
        conn.close()
        return {
            'exercises': exercises,
            'pose_data': pose,
            'video_paths': paths,
            'session_recordings': recordings,
            'next_exercise_id': next_id,
        }


def save_exercise(exercise, pose_payload=None):
    init_db()
    with _lock:
        conn = _connect()
        conn.execute(
            'INSERT OR REPLACE INTO exercises (id, payload) VALUES (?, ?)',
            (int(exercise['id']), json.dumps(exercise, ensure_ascii=False)),
        )
        if pose_payload is not None:
            conn.execute(
                'INSERT OR REPLACE INTO pose_data (exercise_id, payload) VALUES (?, ?)',
                (int(exercise['id']), json.dumps(pose_payload, ensure_ascii=False)),
            )
        conn.execute(
            'INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)',
            ('next_exercise_id', str(int(exercise['id']) + 1)),
        )
        conn.commit()
        conn.close()


def save_exercises(exercises, next_id):
    init_db()
    with _lock:
        conn = _connect()
        for exercise in exercises:
            conn.execute(
                'INSERT OR REPLACE INTO exercises (id, payload) VALUES (?, ?)',
                (int(exercise['id']), json.dumps(exercise, ensure_ascii=False)),
            )
        conn.execute(
            'INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)',
            ('next_exercise_id', str(int(next_id))),
        )
        conn.commit()
        conn.close()


def save_video_file(exercise_id, role, file_path):
    """Store an uploaded doctor or patient video as a BLOB."""
    if not file_path or not os.path.exists(file_path):
        return None
    with open(file_path, 'rb') as handle:
        blob = handle.read()
    if not blob:
        return None
    init_db()
    created = datetime.now().isoformat()
    filename = os.path.basename(file_path)
    with _lock:
        conn = _connect()
        conn.execute(
            '''
            INSERT INTO videos (exercise_id, role, filename, data, created_at)
            VALUES (?, ?, ?, ?, ?)
            ''',
            (int(exercise_id), role, filename, blob, created),
        )
        conn.commit()
        path = _export_latest(conn, int(exercise_id), role)
        conn.close()
    return path


def export_video(exercise_id, role):
    init_db()
    with _lock:
        conn = _connect()
        path = _export_latest(conn, int(exercise_id), role)
        if path is None and role == 'doctor':
            row = conn.execute(
                'SELECT payload FROM exercises WHERE id = ?',
                (int(exercise_id),),
            ).fetchone()
            if row:
                payload = json.loads(row['payload'])
                media_id = payload.get('video_media_id')
                if media_id:
                    exported = _export_media(conn, int(media_id))
                    path = exported[0] if exported else None
        conn.close()
    return path


def _export_latest(conn, exercise_id, role):
    row = conn.execute(
        '''
        SELECT filename, data FROM videos
        WHERE exercise_id = ? AND role = ?
        ORDER BY id DESC LIMIT 1
        ''',
        (int(exercise_id), role),
    ).fetchone()
    if not row:
        return None
    os.makedirs(_CACHE, exist_ok=True)
    ext = os.path.splitext(row['filename'] or '')[1] or '.mp4'
    path = os.path.join(_CACHE, f'{role}_{int(exercise_id)}{ext}')
    with open(path, 'wb') as handle:
        handle.write(row['data'])
    return path


def _migrate_legacy_library(conn):
    """Copy the old library table into exercise templates once."""
    done = conn.execute(
        "SELECT value FROM meta WHERE key = 'library_migrated'"
    ).fetchone()
    if done:
        return
    rows = conn.execute('SELECT * FROM library').fetchall()
    for row in rows:
        existing = conn.execute(
            'SELECT id FROM exercise_templates WHERE id = ?', (int(row['id']),)
        ).fetchone()
        if existing:
            continue
        media_id = None
        video_url = None
        thumbnail_url = None
        duration = int(round(float(row['duration'] or 0)))
        video_path = row['video_path']
        if video_path and os.path.exists(video_path):
            with open(video_path, 'rb') as handle:
                blob = handle.read()
            if blob:
                created = row['created_at'] or datetime.now().isoformat(timespec='microseconds')
                cur = conn.execute(
                    '''
                    INSERT INTO media (filename, data, thumbnail, duration_seconds, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    ''',
                    (os.path.basename(video_path), blob, None, duration, created),
                )
                media_id = int(cur.lastrowid)
                video_url = f'media://{media_id}'
                thumb_file = row['thumbnail_path']
                thumb_blob = None
                if thumb_file and os.path.exists(thumb_file):
                    with open(thumb_file, 'rb') as handle:
                        thumb_blob = handle.read() or None
                if thumb_blob:
                    conn.execute(
                        'UPDATE media SET thumbnail = ? WHERE id = ?',
                        (thumb_blob, media_id),
                    )
                    thumbnail_url = f'thumb://{media_id}'
        created_at = row['created_at'] or datetime.now().isoformat(timespec='microseconds')
        conn.execute(
            '''
            INSERT INTO exercise_templates (
                id, doctor_id, name, video_url, thumbnail_url, duration_seconds,
                media_id, pose_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                int(row['id']),
                1,
                row['name'] or 'Egzersiz',
                video_url,
                thumbnail_url,
                duration,
                media_id,
                None,
                created_at,
                created_at,
            ),
        )
    conn.execute(
        "INSERT OR REPLACE INTO meta (key, value) VALUES ('library_migrated', '1')"
    )


def _write_media_files(media_id, filename, blob, thumbnail):
    os.makedirs(_CACHE, exist_ok=True)
    ext = os.path.splitext(filename or '')[1] or '.mp4'
    video_path = os.path.join(_CACHE, f'media_{int(media_id)}{ext}')
    with open(video_path, 'wb') as handle:
        handle.write(blob)
    thumb_path = None
    if thumbnail:
        thumb_path = os.path.join(_CACHE, f'thumb_{int(media_id)}.jpg')
        with open(thumb_path, 'wb') as handle:
            handle.write(thumbnail)
    return video_path, thumb_path


def _export_media(conn, media_id):
    row = conn.execute(
        'SELECT filename, data, thumbnail FROM media WHERE id = ?',
        (int(media_id),),
    ).fetchone()
    if not row:
        return None
    return _write_media_files(media_id, row['filename'], row['data'], row['thumbnail'])


def export_media(media_id):
    init_db()
    with _lock:
        conn = _connect()
        exported = _export_media(conn, int(media_id))
        conn.close()
    return exported


def count_media():
    init_db()
    with _lock:
        conn = _connect()
        row = conn.execute('SELECT COUNT(*) AS n FROM media').fetchone()
        conn.close()
    return int(row['n'])


def media_blob_size(media_id):
    init_db()
    with _lock:
        conn = _connect()
        row = conn.execute(
            'SELECT LENGTH(data) AS n FROM media WHERE id = ?',
            (int(media_id),),
        ).fetchone()
        conn.close()
    return int(row['n']) if row and row['n'] is not None else 0


def insert_media(blob, filename, thumbnail, duration_seconds):
    init_db()
    created = datetime.now().isoformat(timespec='microseconds')
    with _lock:
        conn = _connect()
        cur = conn.execute(
            '''
            INSERT INTO media (filename, data, thumbnail, duration_seconds, created_at)
            VALUES (?, ?, ?, ?, ?)
            ''',
            (filename, blob, thumbnail, duration_seconds, created),
        )
        media_id = int(cur.lastrowid)
        video_path, thumb_path = _write_media_files(media_id, filename, blob, thumbnail)
        conn.commit()
        conn.close()
    return {
        'id': media_id,
        'video_url': f'media://{media_id}',
        'thumbnail_url': f'thumb://{media_id}',
        'video_path': video_path,
        'thumbnail_path': thumb_path,
        'duration_seconds': duration_seconds,
    }


def insert_template(doctor_id, name, media, pose_payload, created_at, updated_at):
    init_db()
    pose_json = json.dumps(pose_payload, ensure_ascii=False) if pose_payload is not None else None
    with _lock:
        conn = _connect()
        cur = conn.execute(
            '''
            INSERT INTO exercise_templates (
                doctor_id, name, video_url, thumbnail_url, duration_seconds,
                media_id, pose_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                int(doctor_id),
                name,
                media.get('video_url'),
                media.get('thumbnail_url'),
                media.get('duration_seconds'),
                media.get('id'),
                pose_json,
                created_at,
                updated_at,
            ),
        )
        template_id = int(cur.lastrowid)
        conn.commit()
        conn.close()
    return template_id


def get_template(template_id):
    init_db()
    with _lock:
        conn = _connect()
        row = conn.execute(
            'SELECT * FROM exercise_templates WHERE id = ?',
            (int(template_id),),
        ).fetchone()
        conn.close()
    return dict(row) if row else None


def list_templates(doctor_id):
    init_db()
    with _lock:
        conn = _connect()
        rows = conn.execute(
            '''
            SELECT * FROM exercise_templates
            WHERE doctor_id = ?
            ORDER BY created_at DESC, id DESC
            ''',
            (int(doctor_id),),
        ).fetchall()
        conn.close()
    return [dict(row) for row in rows]


def update_template_name(template_id, name, updated_at):
    init_db()
    with _lock:
        conn = _connect()
        cur = conn.execute(
            '''
            UPDATE exercise_templates
            SET name = ?, updated_at = ?
            WHERE id = ?
            ''',
            (name, updated_at, int(template_id)),
        )
        conn.commit()
        changed = cur.rowcount
        conn.close()
    return changed > 0


def delete_template(template_id):
    """Remove the template row. Shared media and assigned exercises stay."""
    init_db()
    with _lock:
        conn = _connect()
        conn.execute(
            'DELETE FROM exercise_templates WHERE id = ?',
            (int(template_id),),
        )
        conn.commit()
        conn.close()


def template_pose(template_id):
    row = get_template(template_id)
    if not row or not row.get('pose_json'):
        return None
    return json.loads(row['pose_json'])


def list_exercises():
    init_db()
    with _lock:
        conn = _connect()
        rows = conn.execute('SELECT payload FROM exercises ORDER BY id DESC').fetchall()
        conn.close()
    return [json.loads(row['payload']) for row in rows]
