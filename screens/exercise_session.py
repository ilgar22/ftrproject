"""
Egzersiz Seansı Ekranı - Kamera + MediaPipe Gerçek Zamanlı Analiz
En kritik ekran: pose estimation ve karşılaştırma burada çalışır
"""

import cv2
import numpy as np
import threading
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
        self._build()
    
    # ─── YÜKLEME ─────────────────────────────────────────────────────────────
    def load_exercise(self, exercise_data):
        """Egzersiz verisini yükle ve ekranı hazırla"""
        self.exercise = exercise_data
        self.target_reps = exercise_data.get('daily_reps', 10)
        self.pose_engine.reset_session()
        
        # Ekran başlığını güncelle
        self.title_label.text = exercise_data.get('name', 'Egzersiz')
        self.target_label.text = f'Hedef: {self.target_reps} tekrar'
        self.rep_label.text = '0'
        self.status_label.text = 'Hazır'
        
        # Referans pose verilerini API'den çek
        ex_id = exercise_data.get('id')
        if ex_id:
            api.get_exercise_pose_data(ex_id, self._on_pose_data_loaded)
    
    def _on_pose_data_loaded(self, success, data):
        def update(dt):
            if success and data:
                self.pose_engine.load_reference_from_json(data)
                self.status_label.text = 'Referans yüklendi ✓'
                self.status_label.color = c('success')
            else:
                self.status_label.text = '⚠ Demo modu (referans yok)'
                self.status_label.color = c('warning')
        Clock.schedule_once(update, 0)
    
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
            allow_stretch=True,
            keep_ratio=True,
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
            text='▶  Başlat',
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
        self.start_btn.text = '⏸  Duraklat'
        self.finish_btn.opacity = 1.0
        self.finish_btn.disabled = False
        self.status_label.text = 'Egzersiz yapılıyor...'
        self.status_label.color = c('success')
        
        # Kamerayı başlat
        self._open_camera()
        
        # Clock ile frame güncelleme
        self._clock_event = Clock.schedule_interval(self._update_frame, 1/25)
    
    def _pause_session(self):
        self.is_running = False
        self.start_btn.text = '▶  Devam'
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
        if self.camera is None:
            self.camera = cv2.VideoCapture(0)
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    def _close_camera(self):
        if self.camera:
            self.camera.release()
            self.camera = None
    
    def _update_frame(self, dt):
        if not self.is_running or self.camera is None:
            return
        
        ret, frame = self.camera.read()
        if not ret:
            return
        
        # Aynalama (selfie view)
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
            self.status_label.text = f'🎉 {self.target_reps} tekrar tamamlandı!'
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
