"""
Egzersiz Seansı Ekranı - Kamera + MediaPipe Gerçek Zamanlı Analiz
En kritik ekran: pose estimation ve karşılaştırma burada çalışır
"""

import cv2
import numpy as np
import threading
import os
from datetime import datetime

from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.graphics.texture import Texture
from kivy.graphics import Color, RoundedRectangle, Rectangle
from kivy.utils import get_color_from_hex
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.app import App

from widgets.components import (
    Card, SolidButton, GlowButton, TopBar,
    SimilarityMeter, FeedbackPanel, c, COLORS
)
from services.pose_engine import PoseEngine
from services.api_service import api

DROIDCAM_IP = "192.168.50.139:4747"
DROIDCAM_URL = f"http://{DROIDCAM_IP}"
DROIDCAM_ALT_URL = f"http://{DROIDCAM_IP}/mjpegfeed"


class ExerciseSessionScreen(Screen):
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.exercise = None
        self.camera = None
        self.pose_engine = PoseEngine()
        self.is_running = False
        self.session_start_time = None
        self.target_reps = 10
        self._clock_event = None
        self._green_frame_count = 0
        self._using_droidcam = False
        self._build()
    
    # ─── YÜKLEME ─────────────────────────────────────────────────────────────
    def load_exercise(self, exercise_data):
        """Egzersiz verisini yükle ve ekranı hazırla"""
        self.exercise = exercise_data
        self.target_reps = exercise_data.get('daily_reps', 10)
        self.pose_engine.reset_session()
        self._configure_exercise_mode(exercise_data)
        
        # Ekran başlığını güncelle
        self.title_label.text = exercise_data.get('name', 'Egzersiz')
        self.target_label.text = f'Hedef: {self.target_reps} tekrar'
        self.rep_label.text = '0'
        self.status_label.text = 'Hazır'
        
        # Referans pose verilerini API'den çek
        ex_id = exercise_data.get('id')
        if self.pose_engine.exercise_mode == 'reference' and ex_id:
            api.get_exercise_pose_data(ex_id, self._on_pose_data_loaded)
        elif self.pose_engine.exercise_mode == 'biceps':
            self.status_label.text = 'Biceps sayaci hazir'
            self.status_label.color = c('success')

    def _configure_exercise_mode(self, exercise_data):
        name = (exercise_data.get('name') or '').lower()
        mode = (exercise_data.get('mode') or '').lower()
        if 'biceps' in name or mode == 'biceps':
            side = exercise_data.get('side', 'auto')
            self.pose_engine.set_exercise_mode('biceps', side=side)
        else:
            self.pose_engine.set_exercise_mode('reference')
    
    def _on_pose_data_loaded(self, success, data):
        def update(dt):
            if success and data:
                self.pose_engine.load_reference_from_json(data)
                self.status_label.text = 'Referans yuklendi'
                self.status_label.color = c('success')
            else:
                self.status_label.text = 'Referans video indiriliyor...'
                self.status_label.color = c('warning')
                self._load_reference_from_video()
        Clock.schedule_once(update, 0)

    def _load_reference_from_video(self):
        ex_id = self.exercise.get('id') if self.exercise else None
        if not ex_id:
            self.status_label.text = 'Demo modu (egzersiz kimligi yok)'
            self.status_label.color = c('warning')
            return

        def on_video_downloaded(success, local_path):
            if not success or not local_path:
                Clock.schedule_once(
                    lambda dt: self._set_status('Demo modu (referans bulunamadi)', 'warning'),
                    0
                )
                return

            thread = threading.Thread(
                target=self._extract_reference_worker,
                args=(local_path,),
                daemon=True
            )
            thread.start()

        api.download_exercise_video(ex_id, on_video_downloaded)

    def _extract_reference_worker(self, local_video_path):
        Clock.schedule_once(
            lambda dt: self._set_status('Referans video analiz ediliyor...', 'warning'),
            0
        )
        try:
            sequence = self.pose_engine.extract_reference_from_video(local_video_path)
            if sequence:
                Clock.schedule_once(
                    lambda dt: self._set_status(f'Referans hazir ({len(sequence)} frame)', 'success'),
                    0
                )
            else:
                Clock.schedule_once(
                    lambda dt: self._set_status('Referans cikarilamadi, demo modu', 'warning'),
                    0
                )
        except Exception:
            Clock.schedule_once(
                lambda dt: self._set_status('Referans analiz hatasi, demo modu', 'warning'),

                0
            )
        finally:
            try:
                if os.path.exists(local_video_path):
                    os.remove(local_video_path)
            except OSError:
                pass

    def _set_status(self, text, color_key='text_sub'):
        self.status_label.text = text
        self.status_label.color = c(color_key)
    
    # ─── EKRAN YAPISI ─────────────────────────────────────────────────────────
    def _build(self):
        root = BoxLayout(orientation='vertical')
        
        with root.canvas.before:
            Color(*get_color_from_hex(COLORS['bg_dark']))
            self._bg = Rectangle(pos=root.pos, size=root.size)
        root.bind(
            pos=lambda *a: setattr(self._bg, 'pos', root.pos),
            size=lambda *a: setattr(self._bg, 'size', root.size),
        )
        
        # ── Üst bar ──────────────────────────────────────────
        self.top_bar = TopBar(
            title='Egzersiz',
            back_cb=self._go_back
        )
        root.add_widget(self.top_bar)
        
        # ── Ana içerik ───────────────────────────────────────
        body = BoxLayout(orientation='vertical', padding=dp(12), spacing=dp(10))
        
        # Başlık ve durum
        header = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(8))
        
        title_box = BoxLayout(orientation='vertical')
        self.title_label = Label(
            text='Egzersiz',
            font_size=dp(17),
            bold=True,
            color=c('text_main'),
            halign='left',
            size_hint_y=None,
            height=dp(26),
        )
        self.title_label.bind(
            size=lambda w, s: setattr(w, 'text_size', (s[0], None))
        )
        
        self.status_label = Label(
            text='Hazır',
            font_size=dp(12),
            color=c('text_sub'),
            halign='left',
            size_hint_y=None,
            height=dp(20),
        )
        self.status_label.bind(
            size=lambda w, s: setattr(w, 'text_size', (s[0], None))
        )
        
        title_box.add_widget(self.title_label)
        title_box.add_widget(self.status_label)
        header.add_widget(title_box)
        body.add_widget(header)
        
        # ── Kamera görüntüsü ─────────────────────────────────
        cam_container = FloatLayout(size_hint_y=0.52)
        
        with cam_container.canvas.before:
            Color(*get_color_from_hex(COLORS['bg_surface']))
            self._cam_bg = RoundedRectangle(
                pos=cam_container.pos,
                size=cam_container.size,
                radius=[dp(14)]
            )
        cam_container.bind(
            pos=lambda *a: setattr(self._cam_bg, 'pos', cam_container.pos),
            size=lambda *a: setattr(self._cam_bg, 'size', cam_container.size),
        )
        
        # Kamera feed
        self.cam_image = Image(
            size_hint=(1, 1),
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
            fit_mode='contain',
        )
        cam_container.add_widget(self.cam_image)
        
        # Tekrar sayacı overlay
        rep_overlay = BoxLayout(
            size_hint=(None, None),
            size=(dp(90), dp(70)),
            pos_hint={'right': 0.98, 'top': 0.98},
            orientation='vertical',
        )
        with rep_overlay.canvas.before:
            Color(0, 0, 0, 0.65)
            self._rep_bg = RoundedRectangle(
                pos=rep_overlay.pos, size=rep_overlay.size, radius=[dp(10)]
            )
        rep_overlay.bind(
            pos=lambda *a: setattr(self._rep_bg, 'pos', rep_overlay.pos),
            size=lambda *a: setattr(self._rep_bg, 'size', rep_overlay.size),
        )
        
        self.rep_label = Label(
            text='0',
            font_size=dp(36),
            bold=True,
            color=c('primary'),
        )
        self.target_label = Label(
            text=f'Hedef: {self.target_reps}',
            font_size=dp(11),
            color=c('text_sub'),
        )
        rep_overlay.add_widget(self.rep_label)
        rep_overlay.add_widget(self.target_label)
        cam_container.add_widget(rep_overlay)
        
        body.add_widget(cam_container)
        
        # ── Benzerlik ve geri bildirim ───────────────────────
        metrics_row = BoxLayout(spacing=dp(10), size_hint_y=None, height=dp(75))
        
        # Benzerlik metre
        sim_card = Card(orientation='vertical', spacing=dp(4))
        sim_title = Label(
            text='Benzerlik',
            font_size=dp(11),
            color=c('text_sub'),
            size_hint_y=None,
            height=dp(16),
        )
        self.similarity_meter = SimilarityMeter()
        sim_card.add_widget(sim_title)
        sim_card.add_widget(self.similarity_meter)
        
        metrics_row.add_widget(sim_card)
        body.add_widget(metrics_row)
        
        # Geri bildirim paneli
        self.feedback_panel = FeedbackPanel()
        body.add_widget(self.feedback_panel)
        
        # ── Kontrol butonları ────────────────────────────────
        controls = BoxLayout(
            spacing=dp(10),
            size_hint_y=None,
            height=dp(54),
        )
        
        self.start_btn = SolidButton(
            text='Baslat',
            color_hex=COLORS['success'],
        )
        self.start_btn.bind(on_press=self._toggle_session)
        
        self.finish_btn = GlowButton(text='Bitir & Kaydet')
        self.finish_btn.bind(on_press=self._finish_session)
        self.finish_btn.opacity = 0.4
        self.finish_btn.disabled = True
        
        controls.add_widget(self.start_btn)
        controls.add_widget(self.finish_btn)
        body.add_widget(controls)
        
        root.add_widget(body)
        self.add_widget(root)
    
    # ─── SEANS KONTROLÜ ──────────────────────────────────────────────────────
    def _toggle_session(self, *a):
        if not self.is_running:
            self._start_session()
        else:
            self._pause_session()
    
    def _start_session(self):
        self.is_running = True
        self.session_start_time = datetime.now()
        self.start_btn.text = 'Duraklat'
        self.finish_btn.opacity = 1.0
        self.finish_btn.disabled = False
        self.status_label.text = 'Egzersiz yapılıyor...'
        self.status_label.color = c('success')
        
        # Kamerayı başlat
        self._open_camera()
        if self.camera is None:
            self.is_running = False
            self.start_btn.text = 'Baslat'
            self._set_status('Kamera baglantisi kurulamadi', 'error')
            return
        
        # Clock ile frame güncelleme
        self._clock_event = Clock.schedule_interval(self._update_frame, 1/25)
    
    def _pause_session(self):
        self.is_running = False
        self.start_btn.text = 'Devam'
        self.status_label.text = 'Duraklatıldı'
        self.status_label.color = c('warning')
        
        if self._clock_event:
            self._clock_event.cancel()
    
    def _finish_session(self, *a):
        self._pause_session()
        self._close_camera()
        
        # Sonuçları kaydet ve sonuç ekranına geç
        summary = self.pose_engine.get_session_summary()
        
        if self.session_start_time:
            duration = (datetime.now() - self.session_start_time).seconds
            summary['duration_seconds'] = duration
        
        summary['completed_at'] = datetime.now().isoformat()
        summary['exercise_name'] = self.exercise.get('name', '') if self.exercise else ''
        
        # API'ye gönder
        if self.exercise and api.token:
            api.submit_session_result(
                self.exercise.get('id'),
                summary,
                lambda s, d: None
            )
        
        # Sonuç ekranına geç
        app = App.get_running_app()
        results_screen = app.sm.get_screen('results')
        results_screen.show_results(summary)
        app.switch_screen('results')
    
    # ─── KAMERA & POSE ───────────────────────────────────────────────────────
    def _open_camera(self):
        if self.camera is not None:
            return

        candidates = [
            (DROIDCAM_URL, cv2.CAP_FFMPEG, True),
            (DROIDCAM_ALT_URL, cv2.CAP_FFMPEG, True),
            (f"http://{DROIDCAM_IP}/videofeed", cv2.CAP_FFMPEG, True),
            (DROIDCAM_URL, cv2.CAP_ANY, True),
            (DROIDCAM_ALT_URL, cv2.CAP_ANY, True),
            (0, cv2.CAP_DSHOW, False),
            (0, cv2.CAP_ANY, False),
        ]

        for source, backend, is_droidcam in candidates:
            cap = cv2.VideoCapture(source, backend)
            if not cap or not cap.isOpened():
                if cap:
                    cap.release()
                continue

            ok = False
            for _ in range(10):
                ret, frame = cap.read()
                if ret and frame is not None and frame.size > 0:
                    ok = True
                    break
            if not ok:
                cap.release()
                continue

            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.camera = cap
            self._using_droidcam = is_droidcam
            self._green_frame_count = 0
            return
    
    def _close_camera(self):
        if self.camera:
            self.camera.release()
            self.camera = None
        self._green_frame_count = 0
        self._using_droidcam = False
    
    def _update_frame(self, dt):
        if not self.is_running or self.camera is None:
            return
        
        ret, frame = self.camera.read()
        if not ret:
            self._set_status('Kare alinamadi, kamerayi kontrol edin', 'warning')
            return

        # Detect common DroidCam decode issue (solid green frames) and auto-fallback.
        if self._is_likely_green_frame(frame):
            self._green_frame_count += 1
            if self._green_frame_count > 12 and self._using_droidcam:
                self._set_status('DroidCam goruntu sorunu, yerel kameraya geciliyor', 'warning')
                self._close_camera()
                self.camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)
                self._using_droidcam = False
            return
        self._green_frame_count = 0
        
        # Portrait orientation: rotate frame by -90 degrees (clockwise).
        frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
        # Selfie mirror
        frame = cv2.flip(frame, 1)
        
        # Pose analizi
        annotated, similarity, feedback, rep_count, joint_status = \
            self.pose_engine.process_frame(frame)
        
        # Kamera görüntüsünü güncelle
        self._frame_to_texture(annotated)
        
        # UI güncelle
        self.similarity_meter.update(similarity)
        self.feedback_panel.update(feedback)
        self.rep_label.text = str(rep_count)
        
        # Hedef tamamlandı mı?
        if rep_count >= self.target_reps:
            self.status_label.text = f'{self.target_reps} tekrar tamamlandi'
            self.status_label.color = c('success')
    
    def _frame_to_texture(self, frame_bgr):
        """OpenCV frame'ini Kivy texture'a dönüştür"""
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        frame_flipped = cv2.flip(frame_rgb, 0)
        
        buf = frame_flipped.tobytes()
        texture = Texture.create(
            size=(frame_bgr.shape[1], frame_bgr.shape[0]),
            colorfmt='rgb'
        )
        texture.blit_buffer(buf, colorfmt='rgb', bufferfmt='ubyte')
        self.cam_image.texture = texture

    def _is_likely_green_frame(self, frame):
        if frame is None or len(frame.shape) != 3 or frame.shape[2] < 3:
            return False
        mean_bgr = frame.mean(axis=(0, 1))
        b, g, r = float(mean_bgr[0]), float(mean_bgr[1]), float(mean_bgr[2])
        return g > 90 and g > (r * 1.8) and g > (b * 1.8)
    
    # ─── NAVİGASYON ──────────────────────────────────────────────────────────
    def _go_back(self):
        if self.is_running:
            self._pause_session()
        self._close_camera()
        App.get_running_app().switch_screen('patient_dashboard', direction='right')
    
    def cleanup(self):
        self._close_camera()
        if self._clock_event:
            self._clock_event.cancel()
        self.pose_engine.release()
    
    def on_leave(self):
        self._close_camera()
        if self._clock_event:
            self._clock_event.cancel()
