"""
Hasta Paneli - Egzersiz listesi ve ilerleme istatistikleri
"""

from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.graphics import Color, Rectangle
from kivy.utils import get_color_from_hex
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.app import App

from widgets.components import (
    Card, ExerciseCard, StatCard, TopBar, GlowButton, c, COLORS
)
from services.api_service import api


# Demo verisi (API bağlantısı yokken kullan)
DEMO_EXERCISES = [
    {
        'id': 1,
        'name': 'Diz Bükme Egzersizi',
        'daily_reps': 15,
        'schedule': 'Sabah & Akşam',
        'status': 'pending',
        'description': 'Bacak kaslarını güçlendirmek için',
    },
    {
        'id': 2,
        'name': 'Omuz Rotasyonu',
        'daily_reps': 10,
        'schedule': 'Sabah',
        'status': 'completed',
        'description': 'Omuz mobilizasyonu için',
    },
    {
        'id': 3,
        'name': 'Kalça Fleksiyonu',
        'daily_reps': 12,
        'schedule': 'Akşam',
        'status': 'pending',
        'description': 'Kalça eklem hareketliliği için',
    },
    {
        'id': 4,
        'name': 'Biceps Curl Test',
        'daily_reps': 12,
        'schedule': 'Test Seansi',
        'status': 'pending',
        'description': 'Dirsek acisina gore tekrar sayimi',
        'mode': 'biceps',
        'side': 'auto',
    },
]

DEMO_STATS = {
    'total_sessions': 24,
    'weekly_streak': 5,
    'avg_accuracy': 78,
    'completed_today': 1,
}


class PatientDashboard(Screen):
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.exercises = []
        self._build()
    
    def on_enter(self):
        self._load_data()
    
    def _build(self):
        self.root_layout = BoxLayout(orientation='vertical')
        
        with self.root_layout.canvas.before:
            Color(*get_color_from_hex(COLORS['bg_dark']))
            self._bg = Rectangle(pos=self.root_layout.pos,
                                  size=self.root_layout.size)
        self.root_layout.bind(
            pos=lambda *a: setattr(self._bg, 'pos', self.root_layout.pos),
            size=lambda *a: setattr(self._bg, 'size', self.root_layout.size),
        )
        
        # ── Üst bar ──────────────────────────────────────────
        self.top_bar = TopBar(title='PhysioConnect')
        
        # Çıkış butonu ekle
        logout_btn = Button(
            text='Çıkış',
            font_size=dp(12),
            color=c('button_text'),
            background_color=(0, 0, 0, 0),
            size_hint_x=None,
            width=dp(60),
        )
        logout_btn.bind(on_press=self._logout)
        self.top_bar.add_widget(logout_btn)
        
        self.root_layout.add_widget(self.top_bar)
        
        # ── Scroll alanı ─────────────────────────────────────
        scroll = ScrollView()
        content = BoxLayout(
            orientation='vertical',
            padding=dp(16),
            spacing=dp(14),
            size_hint_y=None,
        )
        content.bind(minimum_height=content.setter('height'))
        
        # Karşılama
        self.welcome_label = Label(
            text='Merhaba! 👋',
            font_size=dp(20),
            bold=True,
            color=c('text_main'),
            halign='left',
            size_hint_y=None,
            height=dp(34),
        )
        self.welcome_label.bind(
            size=lambda w, s: setattr(w, 'text_size', (s[0], None))
        )
        content.add_widget(self.welcome_label)
        
        # İstatistik kartları
        stats_row = BoxLayout(
            spacing=dp(10),
            size_hint_y=None,
            height=dp(100),
        )
        
        self.stat_sessions = StatCard('📅', '0', 'Toplam Seans')
        self.stat_streak   = StatCard('🔥', '0', 'Günlük Seri',
                                       accent=c('warning'))
        self.stat_accuracy = StatCard('🎯', '0%', 'Doğruluk',
                                       accent=c('success'))
        
        stats_row.add_widget(self.stat_sessions)
        stats_row.add_widget(self.stat_streak)
        stats_row.add_widget(self.stat_accuracy)
        content.add_widget(stats_row)
        
        # Egzersizler başlık
        ex_title = Label(
            text='Bugünkü Egzersizlerim',
            font_size=dp(16),
            bold=True,
            color=c('text_main'),
            halign='left',
            size_hint_y=None,
            height=dp(28),
        )
        ex_title.bind(size=lambda w, s: setattr(w, 'text_size', (s[0], None)))
        content.add_widget(ex_title)
        
        # Egzersiz listesi konteyneri
        self.exercise_container = BoxLayout(
            orientation='vertical',
            spacing=dp(8),
            size_hint_y=None,
        )
        self.exercise_container.bind(
            minimum_height=self.exercise_container.setter('height')
        )
        content.add_widget(self.exercise_container)
        
        # Yükleniyor label
        self.loading_label = Label(
            text='Egzersizler yükleniyor...',
            font_size=dp(14),
            color=c('text_sub'),
            size_hint_y=None,
            height=dp(60),
        )
        self.exercise_container.add_widget(self.loading_label)
        
        content.add_widget(BoxLayout(size_hint_y=None, height=dp(30)))
        
        scroll.add_widget(content)
        self.root_layout.add_widget(scroll)
        self.add_widget(self.root_layout)
    
    def _load_data(self):
        # API'den veri çek
        api.get_exercises(self._on_exercises_loaded)
        api.get_progress(self._on_progress_loaded)
        
        # Karşılama metnini güncelle
        name = api.user.get('name', 'Hasta') if api.user else 'Hasta'
        self.welcome_label.text = f'Merhaba, {name}! 👋'
    
    def _on_exercises_loaded(self, success, data):
        def update(dt):
            self.exercise_container.clear_widgets()
            exercises = data if success else DEMO_EXERCISES
            
            if not exercises:
                self.exercise_container.add_widget(Label(
                    text='Henüz egzersiz atanmamış',
                    color=c('text_sub'),
                    size_hint_y=None,
                    height=dp(60),
                ))
                return
            
            for ex in exercises:
                card = ExerciseCard(
                    exercise_data=ex,
                    on_press_cb=self._open_exercise,
                )
                self.exercise_container.add_widget(card)
        
        Clock.schedule_once(update, 0)
    
    def _on_progress_loaded(self, success, data):
        def update(dt):
            stats = data if success and data else DEMO_STATS
            self.stat_sessions.children[1].text = str(
                stats.get('total_sessions', 0))
            self.stat_streak.children[1].text = str(
                stats.get('weekly_streak', 0))
            self.stat_accuracy.children[1].text = str(
                stats.get('avg_accuracy', 0)) + '%'
        
        Clock.schedule_once(update, 0)
    
    def _open_exercise(self, exercise_data):
        app = App.get_running_app()
        # Egzersiz verisini session ekranına aktar
        session_screen = app.sm.get_screen('exercise_session')
        session_screen.load_exercise(exercise_data)
        app.switch_screen('exercise_session')
    
    def _logout(self, *a):
        api.logout()
        App.get_running_app().switch_screen('login', direction='right')
