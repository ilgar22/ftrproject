"""
UI Bileşenleri - Yeniden kullanılabilir widget'lar
"""

from kivy.uix.widget import Widget
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.graphics import Color, RoundedRectangle, Rectangle, Line
from kivy.utils import get_color_from_hex
from kivy.metrics import dp
from kivy.animation import Animation
from kivy.properties import StringProperty, NumericProperty, ColorProperty
from kivy.uix.progressbar import ProgressBar


# ─── RENK PALETİ ─────────────────────────────────────────────────────────────
COLORS = {
    'bg_dark':     '#0F1923',
    'bg_card':     '#1A2533',
    'bg_surface':  '#1E2D40',
    'primary':     '#00D4FF',
    'primary_dim': '#0099BB',
    'success':     '#00FF88',
    'warning':     '#FFB800',
    'error':       '#FF4444',
    'text_main':   '#FFFFFF',
    'text_sub':    '#8899AA',
    'text_dim':    '#445566',
    'border':      '#2A3F55',
}


def c(key):
    """Renk kısayolu"""
    return get_color_from_hex(COLORS[key])


# ─── GRADIENT BUTON ───────────────────────────────────────────────────────────
class GlowButton(Button):
    """Işıltılı, modern buton"""
    
    def __init__(self, text='', accent_color=None, **kwargs):
        super().__init__(**kwargs)
        self.text = text
        self.accent = accent_color or get_color_from_hex(COLORS['primary'])
        self.background_color = (0, 0, 0, 0)
        self.color = get_color_from_hex(COLORS['text_main'])
        self.font_size = dp(15)
        self.bold = True
        self.size_hint_y = None
        self.height = dp(52)
        
        with self.canvas.before:
            self._color = Color(*self.accent, 0.15)
            self._bg = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(12)])
            Color(*self.accent, 0.8)
            self._border = Line(
                rounded_rectangle=[*self.pos, *self.size, dp(12)],
                width=1.2
            )
        
        self.bind(pos=self._update, size=self._update)
    
    def _update(self, *a):
        self._bg.pos = self.pos
        self._bg.size = self.size
        self._border.rounded_rectangle = [*self.pos, *self.size, dp(12)]
    
    def on_press(self):
        anim = Animation(opacity=0.7, duration=0.08)
        anim += Animation(opacity=1.0, duration=0.08)
        anim.start(self)


class SolidButton(Button):
    """Düz dolgulu buton"""
    
    def __init__(self, text='', color_hex='#00D4FF', **kwargs):
        super().__init__(**kwargs)
        self.text = text
        self.fill_color = get_color_from_hex(color_hex)
        self.background_color = (0, 0, 0, 0)
        self.color = get_color_from_hex('#0F1923')
        self.font_size = dp(15)
        self.bold = True
        self.size_hint_y = None
        self.height = dp(52)
        
        with self.canvas.before:
            self._fc = Color(*self.fill_color)
            self._bg = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(12)])
        
        self.bind(pos=self._update, size=self._update)
    
    def _update(self, *a):
        self._bg.pos = self.pos
        self._bg.size = self.size


# ─── KART BİLEŞENİ ───────────────────────────────────────────────────────────
class Card(BoxLayout):
    """Yuvarlak köşeli kart"""
    
    def __init__(self, bg_color=None, padding=None, **kwargs):
        super().__init__(**kwargs)
        fill = bg_color or get_color_from_hex(COLORS['bg_card'])
        self.padding = padding or [dp(16), dp(14)]
        
        with self.canvas.before:
            Color(*fill)
            self._bg = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(14)])
            Color(*get_color_from_hex(COLORS['border']))
            self._bd = Line(
                rounded_rectangle=[*self.pos, *self.size, dp(14)],
                width=0.8
            )
        
        self.bind(pos=self._update, size=self._update)
    
    def _update(self, *a):
        self._bg.pos = self.pos
        self._bg.size = self.size
        self._bd.rounded_rectangle = [*self.pos, *self.size, dp(14)]


# ─── EGZERSİZ LİSTE KARTI ────────────────────────────────────────────────────
class ExerciseCard(Card):
    """Egzersiz liste öğesi kartı"""
    
    def __init__(self, exercise_data, on_press_cb=None, **kwargs):
        super().__init__(orientation='horizontal', spacing=dp(12),
                         size_hint_y=None, height=dp(88), **kwargs)
        
        self.exercise = exercise_data
        self.on_press_cb = on_press_cb
        
        # İkon alanı
        icon_box = BoxLayout(size_hint_x=None, width=dp(56))
        with icon_box.canvas.before:
            Color(*get_color_from_hex(COLORS['primary']), 0.15)
            RoundedRectangle(pos=icon_box.pos, size=icon_box.size, radius=[dp(10)])
        icon_label = Label(
            text='🏃',
            font_size=dp(28),
        )
        icon_box.add_widget(icon_label)
        
        # İçerik
        info_box = BoxLayout(orientation='vertical', spacing=dp(2))
        
        name_lbl = Label(
            text=exercise_data.get('name', 'Egzersiz'),
            font_size=dp(15),
            bold=True,
            color=c('text_main'),
            halign='left',
            size_hint_y=None,
            height=dp(22),
        )
        name_lbl.bind(size=lambda w, s: setattr(w, 'text_size', (s[0], None)))
        
        reps_text = f"Günlük: {exercise_data.get('daily_reps', 0)} tekrar"
        if exercise_data.get('schedule'):
            reps_text += f" · {exercise_data.get('schedule', '')}"
        
        detail_lbl = Label(
            text=reps_text,
            font_size=dp(12),
            color=c('text_sub'),
            halign='left',
            size_hint_y=None,
            height=dp(18),
        )
        detail_lbl.bind(size=lambda w, s: setattr(w, 'text_size', (s[0], None)))
        
        # Durum badge
        status = exercise_data.get('status', 'pending')
        status_colors = {
            'completed': COLORS['success'],
            'pending':   COLORS['warning'],
            'skipped':   COLORS['error'],
        }
        status_texts = {
            'completed': '✓ Tamamlandı',
            'pending':   '⏳ Bekliyor',
            'skipped':   '✗ Atlandı',
        }
        
        status_lbl = Label(
            text=status_texts.get(status, ''),
            font_size=dp(11),
            color=get_color_from_hex(status_colors.get(status, COLORS['text_dim'])),
            halign='left',
            size_hint_y=None,
            height=dp(16),
        )
        status_lbl.bind(size=lambda w, s: setattr(w, 'text_size', (s[0], None)))
        
        info_box.add_widget(name_lbl)
        info_box.add_widget(detail_lbl)
        info_box.add_widget(status_lbl)
        
        # Ok butonu
        arrow_btn = Button(
            text='›',
            font_size=dp(28),
            color=c('primary'),
            background_color=(0, 0, 0, 0),
            size_hint_x=None,
            width=dp(36),
        )
        arrow_btn.bind(on_press=lambda x: self.on_press_cb and
                       self.on_press_cb(self.exercise))
        
        self.add_widget(icon_box)
        self.add_widget(info_box)
        self.add_widget(arrow_btn)


# ─── İSTATİSTİK KARTI ────────────────────────────────────────────────────────
class StatCard(Card):
    """Tek istatistik gösteren mini kart"""
    
    def __init__(self, icon, value, label, accent=None, **kwargs):
        super().__init__(orientation='vertical', spacing=dp(4),
                         size_hint_x=0.5, **kwargs)
        
        icon_lbl = Label(text=icon, font_size=dp(26),
                         size_hint_y=None, height=dp(34))
        
        val_lbl = Label(
            text=str(value),
            font_size=dp(22),
            bold=True,
            color=accent or c('primary'),
            size_hint_y=None,
            height=dp(28),
        )
        
        desc_lbl = Label(
            text=label,
            font_size=dp(11),
            color=c('text_sub'),
            size_hint_y=None,
            height=dp(18),
        )
        
        self.add_widget(icon_lbl)
        self.add_widget(val_lbl)
        self.add_widget(desc_lbl)


# ─── BENZERLIK GÖSTERGESI ────────────────────────────────────────────────────
class SimilarityMeter(BoxLayout):
    """Canlı benzerlik yüzdesi göstergesi"""
    
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', spacing=dp(4),
                         size_hint_y=None, height=dp(60), **kwargs)
        
        self.score_label = Label(
            text='0%',
            font_size=dp(32),
            bold=True,
            color=c('text_sub'),
            size_hint_y=None,
            height=dp(40),
        )
        
        self.bar = ProgressBar(
            max=100,
            value=0,
            size_hint_y=None,
            height=dp(8),
        )
        
        self.add_widget(self.score_label)
        self.add_widget(self.bar)
    
    def update(self, score_0_to_1):
        pct = int(score_0_to_1 * 100)
        self.bar.value = pct
        self.score_label.text = f'{pct}%'
        
        if pct >= 75:
            self.score_label.color = c('success')
        elif pct >= 50:
            self.score_label.color = c('warning')
        else:
            self.score_label.color = c('error')


# ─── FEEDBACK PANEL ──────────────────────────────────────────────────────────
class FeedbackPanel(Card):
    """Gerçek zamanlı hata mesajları paneli"""
    
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', spacing=dp(4),
                         size_hint_y=None, height=dp(100), **kwargs)
        
        title = Label(
            text='Geri Bildirim',
            font_size=dp(12),
            bold=True,
            color=c('text_sub'),
            size_hint_y=None,
            height=dp(18),
            halign='left',
        )
        title.bind(size=lambda w, s: setattr(w, 'text_size', (s[0], None)))
        
        self.msg_label = Label(
            text='✓ Hareketi bekleniyor...',
            font_size=dp(13),
            color=c('text_main'),
            halign='left',
            valign='top',
        )
        self.msg_label.bind(
            size=lambda w, s: setattr(w, 'text_size', (s[0], None))
        )
        
        self.add_widget(title)
        self.add_widget(self.msg_label)
    
    def update(self, feedback_list):
        if not feedback_list:
            self.msg_label.text = '✓ Hareketi doğru yapıyorsunuz!'
            self.msg_label.color = c('success')
        else:
            msgs = '\n'.join([f'⚠ {f}' for f in feedback_list[:3]])
            self.msg_label.text = msgs
            self.msg_label.color = c('warning')


# ─── BAŞLIK BARI ─────────────────────────────────────────────────────────────
class TopBar(BoxLayout):
    """Üst navigasyon çubuğu"""
    
    def __init__(self, title='', back_cb=None, **kwargs):
        super().__init__(
            orientation='horizontal',
            size_hint_y=None,
            height=dp(56),
            padding=[dp(8), 0],
            spacing=dp(8),
            **kwargs
        )
        
        with self.canvas.before:
            Color(*get_color_from_hex(COLORS['bg_surface']))
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=lambda *a: setattr(self._bg, 'pos', self.pos),
                  size=lambda *a: setattr(self._bg, 'size', self.size))
        
        if back_cb:
            back_btn = Button(
                text='‹',
                font_size=dp(28),
                color=c('primary'),
                background_color=(0, 0, 0, 0),
                size_hint_x=None,
                width=dp(44),
            )
            back_btn.bind(on_press=lambda x: back_cb())
            self.add_widget(back_btn)
        
        title_lbl = Label(
            text=title,
            font_size=dp(17),
            bold=True,
            color=c('text_main'),
        )
        self.add_widget(title_lbl)
