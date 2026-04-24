"""
Doktor Paneli - Hasta listesi ve egzersiz takibi
"""

from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.graphics import Color, Rectangle, RoundedRectangle, Line
from kivy.utils import get_color_from_hex
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.app import App

from widgets.components import Card, TopBar, SolidButton, GlowButton, c, COLORS
from services.api_service import api


DEMO_PATIENTS = [
    {'id': 1, 'name': 'Ali Yılmaz', 'age': 45,
     'exercises_today': 2, 'compliance': 85, 'last_active': 'Bugün'},
    {'id': 2, 'name': 'Fatma Demir', 'age': 38,
     'exercises_today': 1, 'compliance': 72, 'last_active': 'Dün'},
    {'id': 3, 'name': 'Mehmet Kaya', 'age': 60,
     'exercises_today': 0, 'compliance': 45, 'last_active': '3 gün önce'},
]


class PatientCard(Card):
    def __init__(self, patient, on_view_cb=None, **kwargs):
        super().__init__(orientation='horizontal', spacing=dp(10),
                         size_hint_y=None, height=dp(80), **kwargs)
        
        info = BoxLayout(orientation='vertical', spacing=dp(2))
        
        name_lbl = Label(
            text=patient['name'],
            font_size=dp(15),
            bold=True,
            color=c('text_main'),
            halign='left',
            size_hint_y=None,
            height=dp(22),
        )
        name_lbl.bind(size=lambda w, s: setattr(w, 'text_size', (s[0], None)))
        
        comp = patient['compliance']
        comp_color = (
            COLORS['success'] if comp >= 70 else
            COLORS['warning'] if comp >= 45 else
            COLORS['error']
        )
        
        detail_lbl = Label(
            text=f"Uyum: {comp}%  ·  Son aktif: {patient['last_active']}",
            font_size=dp(12),
            color=get_color_from_hex(comp_color),
            halign='left',
            size_hint_y=None,
            height=dp(18),
        )
        detail_lbl.bind(size=lambda w, s: setattr(w, 'text_size', (s[0], None)))
        
        ex_lbl = Label(
            text=f"Bugün {patient['exercises_today']} egzersiz",
            font_size=dp(11),
            color=c('text_sub'),
            halign='left',
            size_hint_y=None,
            height=dp(16),
        )
        ex_lbl.bind(size=lambda w, s: setattr(w, 'text_size', (s[0], None)))
        
        info.add_widget(name_lbl)
        info.add_widget(detail_lbl)
        info.add_widget(ex_lbl)
        
        view_btn = Button(
            text='Detay ›',
            font_size=dp(13),
            color=c('primary'),
            background_color=(0, 0, 0, 0),
            size_hint_x=None,
            width=dp(70),
        )
        if on_view_cb:
            view_btn.bind(on_press=lambda x: on_view_cb(patient))
        
        self.add_widget(info)
        self.add_widget(view_btn)


class DoctorDashboard(Screen):
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._build()
    
    def on_enter(self):
        api.get_patients(self._on_patients_loaded)
        name = api.user.get('name', 'Doktor') if api.user else 'Doktor'
        self.welcome_lbl.text = f'Dr. {name}'
    
    def _build(self):
        root = BoxLayout(orientation='vertical')
        
        with root.canvas.before:
            Color(*get_color_from_hex(COLORS['bg_dark']))
            bg = Rectangle(pos=root.pos, size=root.size)
        root.bind(
            pos=lambda *a: setattr(bg, 'pos', root.pos),
            size=lambda *a: setattr(bg, 'size', root.size),
        )
        
        # Üst bar
        bar = TopBar(title='Doktor Paneli')
        logout_btn = Button(
            text='Çıkış',
            font_size=dp(12),
            color=c('text_sub'),
            background_color=(0, 0, 0, 0),
            size_hint_x=None,
            width=dp(60),
        )
        logout_btn.bind(on_press=lambda x: (
            api.logout(),
            App.get_running_app().switch_screen('login', direction='right')
        ))
        bar.add_widget(logout_btn)
        root.add_widget(bar)
        
        scroll = ScrollView()
        content = BoxLayout(
            orientation='vertical',
            padding=dp(16),
            spacing=dp(14),
            size_hint_y=None,
        )
        content.bind(minimum_height=content.setter('height'))
        
        # Karşılama
        self.welcome_lbl = Label(
            text='Dr. ...',
            font_size=dp(20),
            bold=True,
            color=c('text_main'),
            halign='left',
            size_hint_y=None,
            height=dp(34),
        )
        self.welcome_lbl.bind(
            size=lambda w, s: setattr(w, 'text_size', (s[0], None))
        )
        content.add_widget(self.welcome_lbl)
        
        # Özet istatistikler
        stats = BoxLayout(spacing=dp(10), size_hint_y=None, height=dp(80))
        
        for icon, val, label, accent in [
            ('👥', '3', 'Toplam Hasta', c('primary')),
            ('✓', '2', 'Aktif Bugün',  c('success')),
            ('⚠', '1', 'Düşük Uyum',  c('warning')),
        ]:
            card = Card(orientation='vertical', spacing=dp(2))
            card.add_widget(Label(text=icon, font_size=dp(20),
                                   size_hint_y=None, height=dp(26)))
            card.add_widget(Label(text=val, font_size=dp(18), bold=True,
                                   color=accent, size_hint_y=None, height=dp(22)))
            card.add_widget(Label(text=label, font_size=dp(11), color=c('text_sub'),
                                   size_hint_y=None, height=dp(16)))
            stats.add_widget(card)
        
        content.add_widget(stats)
        
        # Hasta listesi başlık
        pt_title = Label(
            text='Hastalarım',
            font_size=dp(16),
            bold=True,
            color=c('text_main'),
            halign='left',
            size_hint_y=None,
            height=dp(28),
        )
        pt_title.bind(size=lambda w, s: setattr(w, 'text_size', (s[0], None)))
        content.add_widget(pt_title)
        
        # Hasta listesi
        self.patients_box = BoxLayout(
            orientation='vertical',
            spacing=dp(8),
            size_hint_y=None,
        )
        self.patients_box.bind(minimum_height=self.patients_box.setter('height'))
        content.add_widget(self.patients_box)
        
        content.add_widget(BoxLayout(size_hint_y=None, height=dp(30)))
        
        scroll.add_widget(content)
        root.add_widget(scroll)
        self.add_widget(root)
    
    def _on_patients_loaded(self, success, data):
        def update(dt):
            self.patients_box.clear_widgets()
            patients = data if success and data else DEMO_PATIENTS
            for pt in patients:
                card = PatientCard(pt, on_view_cb=self._view_patient)
                self.patients_box.add_widget(card)
        Clock.schedule_once(update, 0)
    
    def _view_patient(self, patient):
        # İleride hasta detay ekranı açılabilir
        print(f"Hasta görüntülendi: {patient['name']}")
