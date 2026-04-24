"""
API Service - Replit backend ile iletişim modülü
Tüm HTTP isteklerini yönetir
"""

import requests
import json
import threading
from kivy.app import App


# =============================================
# BURAYA KENDİ REPLİT URL'İNİ YAZ
BASE_URL = "https://your-replit-app.replit.app/api"
# =============================================


class APIService:
    """Singleton API servisi"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.token = None
            cls._instance.user = None
        return cls._instance
    
    def _get_headers(self):
        headers = {'Content-Type': 'application/json'}
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'
        return headers
    
    # ─── AUTH ────────────────────────────────────────────────
    def login(self, email, password, callback):
        """Giriş yap - callback(success, data)"""
        def _run():
            try:
                r = requests.post(
                    f"{BASE_URL}/auth/login",
                    json={"email": email, "password": password},
                    headers=self._get_headers(),
                    timeout=10
                )
                data = r.json()
                if r.status_code == 200:
                    self.token = data.get('token') or data.get('access_token')
                    self.user = data.get('user')
                    callback(True, data)
                else:
                    callback(False, data.get('message', 'Giriş başarısız'))
            except Exception as e:
                callback(False, f"Bağlantı hatası: {str(e)}")
        
        threading.Thread(target=_run, daemon=True).start()
    
    def logout(self):
        self.token = None
        self.user = None
    
    # ─── EGZERSİZLER ─────────────────────────────────────────
    def get_exercises(self, callback):
        """Hastanın egzersiz listesini getir"""
        def _run():
            try:
                r = requests.get(
                    f"{BASE_URL}/exercises",
                    headers=self._get_headers(),
                    timeout=10
                )
                if r.status_code == 200:
                    callback(True, r.json())
                else:
                    callback(False, [])
            except Exception as e:
                callback(False, [])
        
        threading.Thread(target=_run, daemon=True).start()
    
    def get_exercise_detail(self, exercise_id, callback):
        """Egzersiz detayını ve referans pose verilerini getir"""
        def _run():
            try:
                r = requests.get(
                    f"{BASE_URL}/exercises/{exercise_id}",
                    headers=self._get_headers(),
                    timeout=10
                )
                if r.status_code == 200:
                    callback(True, r.json())
                else:
                    callback(False, None)
            except Exception as e:
                callback(False, None)
        
        threading.Thread(target=_run, daemon=True).start()
    
    def get_exercise_video_url(self, exercise_id):
        """Egzersiz video URL'ini döndür"""
        return f"{BASE_URL}/exercises/{exercise_id}/video"
    
    def get_exercise_pose_data(self, exercise_id, callback):
        """Doktorun kaydeddiği referans pose verilerini getir (JSON)"""
        def _run():
            try:
                r = requests.get(
                    f"{BASE_URL}/exercises/{exercise_id}/pose-data",
                    headers=self._get_headers(),
                    timeout=15
                )
                if r.status_code == 200:
                    callback(True, r.json())
                else:
                    callback(False, None)
            except Exception as e:
                callback(False, None)
        
        threading.Thread(target=_run, daemon=True).start()
    
    # ─── SONUÇLAR ────────────────────────────────────────────
    def submit_session_result(self, exercise_id, result_data, callback):
        """
        Egzersiz seansı sonucunu gönder
        result_data = {
            'total_reps': int,
            'correct_reps': int,
            'accuracy_score': float,
            'duration_seconds': int,
            'joint_errors': dict,
            'completed_at': str (ISO datetime)
        }
        """
        def _run():
            try:
                r = requests.post(
                    f"{BASE_URL}/exercises/{exercise_id}/results",
                    json=result_data,
                    headers=self._get_headers(),
                    timeout=15
                )
                if r.status_code in (200, 201):
                    callback(True, r.json())
                else:
                    callback(False, None)
            except Exception as e:
                callback(False, None)
        
        threading.Thread(target=_run, daemon=True).start()
    
    def get_progress(self, callback):
        """Hastanın ilerleme istatistiklerini getir"""
        def _run():
            try:
                r = requests.get(
                    f"{BASE_URL}/patient/progress",
                    headers=self._get_headers(),
                    timeout=10
                )
                if r.status_code == 200:
                    callback(True, r.json())
                else:
                    callback(False, {})
            except Exception as e:
                callback(False, {})
        
        threading.Thread(target=_run, daemon=True).start()
    
    # ─── DOKTOR PANELİ ───────────────────────────────────────
    def get_patients(self, callback):
        """Doktorun hasta listesini getir"""
        def _run():
            try:
                r = requests.get(
                    f"{BASE_URL}/doctor/patients",
                    headers=self._get_headers(),
                    timeout=10
                )
                if r.status_code == 200:
                    callback(True, r.json())
                else:
                    callback(False, [])
            except Exception as e:
                callback(False, [])
        
        threading.Thread(target=_run, daemon=True).start()
    
    def get_patient_results(self, patient_id, callback):
        """Belirli hastanın egzersiz sonuçlarını getir"""
        def _run():
            try:
                r = requests.get(
                    f"{BASE_URL}/doctor/patients/{patient_id}/results",
                    headers=self._get_headers(),
                    timeout=10
                )
                if r.status_code == 200:
                    callback(True, r.json())
                else:
                    callback(False, [])
            except Exception as e:
                callback(False, [])
        
        threading.Thread(target=_run, daemon=True).start()


# Global singleton instance
api = APIService()
