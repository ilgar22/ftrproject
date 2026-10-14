"""
Yerel veri kaliciligi — doktor atamalari, pose verisi ve kayit yollari.
Uygulama yeniden baslatildiginda veriler korunur.
"""

import json
import os
import threading

_STORE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
_STORE_PATH = os.path.join(_STORE_DIR, 'physio_store.json')
_lock = threading.Lock()


def _default_store():
    return {
        'version': 1,
        'next_exercise_id': 1000,
        'exercises': [],
        'pose_data': {},
        'video_paths': {},
        'session_recordings': {},
    }


def load():
    with _lock:
        if not os.path.exists(_STORE_PATH):
            return _default_store()
        try:
            with open(_STORE_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
            base = _default_store()
            base.update({k: data.get(k, base[k]) for k in base})
            base['pose_data'] = {int(k): v for k, v in (data.get('pose_data') or {}).items()}
            base['video_paths'] = {int(k): v for k, v in (data.get('video_paths') or {}).items()}
            base['session_recordings'] = {
                int(k): v for k, v in (data.get('session_recordings') or {}).items()
            }
            return base
        except (json.JSONDecodeError, OSError, ValueError):
            return _default_store()


def save(store):
    with _lock:
        os.makedirs(_STORE_DIR, exist_ok=True)
        payload = {
            'version': store.get('version', 1),
            'next_exercise_id': store.get('next_exercise_id', 1000),
            'exercises': store.get('exercises', []),
            'pose_data': {str(k): v for k, v in (store.get('pose_data') or {}).items()},
            'video_paths': {str(k): v for k, v in (store.get('video_paths') or {}).items()},
            'session_recordings': {
                str(k): v for k, v in (store.get('session_recordings') or {}).items()
            },
        }
        tmp = _STORE_PATH + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        os.replace(tmp, _STORE_PATH)
