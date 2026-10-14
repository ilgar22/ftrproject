"""
Giriş Ekranı - Hasta ve Doktor girişi
"""

from kivy.uix.widget import Widget
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.graphics import Color, RoundedRectangle, Rectangle
from kivy.utils import get_color_from_hex
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.app import App

from widgets.components import SolidButton, GlowButton, c, COLORS
from services.api_service import api


class LoginScreen(Screen):
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._build()
    
    def _build(self):
        root = BoxLayout(orientation='vertical', padding=dp(32), spacing=dp(20))
        
        with root.canvas.before:
            Color(*get_color_from_hex(COLORS['bg_dark']))
            self._bg = Rectangle(pos=root.pos, size=root.size)
        root.bind(
            pos=lambda *a: setattr(self._bg, 'pos', root.pos),
            size=lambda *a: setattr(self._bg, 'size', root.size),
        )
        
        # Logo
        logo_row = BoxLayout(size_hint_y=None, height=dp(72))
        logo_box = BoxLayout(size_hint_x=None, width=dp(72))
        with logo_box.canvas.before:
            Color(*get_color_from_hex(COLORS['primary']))
            self._logo_bg = RoundedRectangle(pos=logo_box.pos, size=logo_box.size, radius=[dp(18)])
        logo_box.bind(
            pos=lambda *a: setattr(self._logo_bg, 'pos', logo_box.pos),
            size=lambda *a: setattr(self._logo_bg, 'size', logo_box.size),
        )
        logo_label = Label(
            text='PC',
            font_size=dp(28),
            bold=True,
            color=get_color_from_hex(COLORS['button_text']),
        )
        logo_box.add_widget(logo_label)
        logo_row.add_widget(Widget(size_hint_x=1))
        logo_row.add_widget(logo_box)
        logo_row.add_widget(Widget(size_hint_x=1))
        root.add_widget(logo_row)
        
        title = Label(
            text='PhysioConnect',
            font_size=dp(28),
            bold=True,
            color=c('primary'),
            size_hint_y=None,
            height=dp(38),
        )
        root.add_widget(title)
        
        sub = Label(
            text='Fizyoterapi Takip Sistemi',
            font_size=dp(14),
            color=c('text_sub'),
            size_hint_y=None,
            height=dp(24),
        )
        root.add_widget(sub)
        
        root.add_widget(BoxLayout(size_hint_y=0.05))
        
        # E-posta
        email_lbl = Label(
            text='E-posta',
            font_size=dp(13),
            color=c('text_sub'),
            halign='left',
            size_hint_y=None,
            height=dp(22),
        )
        email_lbl.bind(size=lambda w, s: setattr(w, 'text_size', (s[0], None)))
        root.add_widget(email_lbl)
        
        self.email_input = self._make_input('ornek@email.com', False)
        root.add_widget(self.email_input)
        
        # Şifre
        pass_lbl = Label(
            text='Şifre',
            font_size=dp(13),
            color=c('text_sub'),
            halign='left',
            size_hint_y=None,
            height=dp(22),
        )
        pass_lbl.bind(size=lambda w, s: setattr(w, 'text_size', (s[0], None)))
        root.add_widget(pass_lbl)
        
        self.pass_input = self._make_input('••••••••', True)
        root.add_widget(self.pass_input)
        
        # Hata mesajı
        self.error_label = Label(
            text='',
            font_size=dp(12),
            color=c('error'),
            size_hint_y=None,
            height=dp(24),
        )
        root.add_widget(self.error_label)
        
        # Giriş butonu
        self.login_btn = SolidButton(
            text='Giriş Yap',
            color_hex=COLORS['primary'],
        )
        self.login_btn.bind(on_press=self._do_login)
        root.add_widget(self.login_btn)
        
        # Demo butonları
        demo_box = BoxLayout(spacing=dp(8), size_hint_y=None, height=dp(44))
        
        demo_patient = GlowButton(text='Demo Hasta')
        demo_patient.bind(on_press=lambda x: self._demo_login('patient'))
        
        demo_doctor = GlowButton(text='Demo Doktor')
        demo_doctor.bind(on_press=lambda x: self._demo_login('doctor'))
        
        demo_box.add_widget(demo_patient)
        demo_box.add_widget(demo_doctor)
        root.add_widget(demo_box)
        
        root.add_widget(BoxLayout(size_hint_y=0.1))
        
        self.add_widget(root)
    
    def _make_input(self, hint, password):
        inp = TextInput(
            hint_text=hint,
            password=password,
            multiline=False,
            size_hint_y=None,
            height=dp(50),
            background_normal='',
            background_active='',
            background_color=get_color_from_hex(COLORS['bg_input']),
            foreground_color=get_color_from_hex(COLORS['text_main']),
            hint_text_color=get_color_from_hex(COLORS['text_dim']),
            cursor_color=get_color_from_hex(COLORS['primary']),
            font_size=dp(15),
            padding=[dp(14), dp(12)],
        )
        return inp
    
    def _do_login(self, *a):
        email = self.email_input.text.strip()
        password = self.pass_input.text.strip()
        
        if not email or not password:
            self.error_label.text = 'E-posta ve şifre gerekli'
            return
        
        self.login_btn.text = 'Giriş yapılıyor...'
        self.error_label.text = ''
        
        api.login(email, password, self._on_login_result)
    
    def _on_login_result(self, success, data):
        def update(dt):
            self.login_btn.text = 'Giriş Yap'
            if success:
                role = api.user.get('role', 'patient') if api.user else 'patient'
                app = App.get_running_app()
                if role == 'doctor' or role == 'physiotherapist':
                    app.switch_screen('doctor_dashboard')
                else:
                    app.switch_screen('patient_dashboard')
            else:
                self.error_label.text = str(data) if data else 'Giriş başarısız'
        
        Clock.schedule_once(update, 0)
    
    def _demo_login(self, role):
        """Demo giriş - API bağlantısı olmadan test et"""
        api.user = {
            'id': 1,
            'name': 'Demo Kullanıcı',
            'role': role,
            'email': f'demo@{role}.com'
        }
        api.token = 'demo_token_12345'
        
        app = App.get_running_app()
        if role == 'doctor':
            app.switch_screen('doctor_dashboard')
        else:
            app.switch_screen('patient_dashboard')
