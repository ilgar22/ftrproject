"""
Sonuç Ekranı - Egzersiz seansı sonuçlarını gösterir
"""

from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.utils import get_color_from_hex
from kivy.metrics import dp
from kivy.app import App

from widgets.components import (
    Card, StatCard, SolidButton, GlowButton, TopBar, c, COLORS
)


class ResultsScreen(Screen):
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._build()
    
    def show_results(self, summary):
        self.summary = summary
        acc = summary.get('accuracy_score', 0)
        
        # Renk
        if acc >= 75:
            color = c('success')
            emoji = 'COK IYI'
            msg = 'Harika iş!'
        elif acc >= 50:
            color = c('warning')
            emoji = 'IYI'
            msg = 'İyi gidiyorsunuz!'
        else:
            color = c('error')
            emoji = 'DEVAM'
            msg = 'Pratik yapın!'
        
        self.result_emoji.text = emoji
        self.result_msg.text = msg
        self.result_msg.color = color
        self.accuracy_label.text = f'{acc}%'
        self.accuracy_label.color = color
        
        self.reps_val.text = str(summary.get('total_reps', 0))
        self.correct_val.text = str(summary.get('correct_reps', 0))
        dur = summary.get('duration_seconds', 0)
        self.duration_val.text = f'{dur // 60}:{dur % 60:02d}'
        
        # Hataları listele
        self.errors_container.clear_widgets()
        joint_errors = summary.get('joint_errors', {})
        if joint_errors:
            for joint, count in joint_errors.items():
                row = BoxLayout(size_hint_y=None, height=dp(34), spacing=dp(8))
                row.add_widget(Label(
                    text=f'Hata: {joint}',
                    font_size=dp(13),
                    color=c('warning'),
                    halign='left',
                ))
                row.add_widget(Label(
                    text=f'{count}x hata',
                    font_size=dp(13),
                    color=c('text_sub'),
                    halign='right',
                ))
                self.errors_container.add_widget(row)
        else:
            self.errors_container.add_widget(Label(
                text='Eklem hatasi yok, cok iyi.',
                font_size=dp(13),
                color=c('success'),
                size_hint_y=None,
                height=dp(34),
            ))
    
    def _build(self):
        root = BoxLayout(orientation='vertical')
        
        with root.canvas.before:
            Color(*get_color_from_hex(COLORS['bg_dark']))
            bg = Rectangle(pos=root.pos, size=root.size)
        root.bind(
            pos=lambda *a: setattr(bg, 'pos', root.pos),
            size=lambda *a: setattr(bg, 'size', root.size),
        )
        
        root.add_widget(TopBar(
            title='Seans Sonucu',
            back_cb=lambda: App.get_running_app().switch_screen(
                'patient_dashboard', direction='right')
        ))
        
        scroll = ScrollView()
        content = BoxLayout(
            orientation='vertical',
            padding=dp(20),
            spacing=dp(14),
            size_hint_y=None,
        )
        content.bind(minimum_height=content.setter('height'))
        
        # Büyük skor
        self.result_emoji = Label(
            text='SONUC',
            font_size=dp(34),
            size_hint_y=None,
            height=dp(70),
        )
        content.add_widget(self.result_emoji)
        
        self.result_msg = Label(
            text='Harika iş!',
            font_size=dp(22),
            bold=True,
            color=c('success'),
            size_hint_y=None,
            height=dp(32),
        )
        content.add_widget(self.result_msg)
        
        self.accuracy_label = Label(
            text='0%',
            font_size=dp(48),
            bold=True,
            color=c('success'),
            size_hint_y=None,
            height=dp(60),
        )
        content.add_widget(self.accuracy_label)
        
        acc_sub = Label(
            text='Doğruluk Oranı',
            font_size=dp(13),
            color=c('text_sub'),
            size_hint_y=None,
            height=dp(22),
        )
        content.add_widget(acc_sub)
        
        # İstatistik satırı
        stats_row = BoxLayout(spacing=dp(10), size_hint_y=None, height=dp(90))
        
        self.reps_val    = Label(text='0', font_size=dp(24), bold=True, color=c('primary'))
        self.correct_val = Label(text='0', font_size=dp(24), bold=True, color=c('success'))
        self.duration_val = Label(text='0:00', font_size=dp(24), bold=True, color=c('warning'))
        
        for val, lbl in [
            (self.reps_val, 'Toplam Tekrar'),
            (self.correct_val, 'Doğru Tekrar'),
            (self.duration_val, 'Süre'),
        ]:
            card = Card(orientation='vertical', spacing=dp(4), size_hint_x=1/3)
            card.add_widget(val)
            card.add_widget(Label(text=lbl, font_size=dp(11), color=c('text_sub'),
                                   size_hint_y=None, height=dp(18)))
            stats_row.add_widget(card)
        
        content.add_widget(stats_row)
        
        # Eklem hata raporu
        error_title = Label(
            text='Eklem Analizi',
            font_size=dp(15),
            bold=True,
            color=c('text_main'),
            halign='left',
            size_hint_y=None,
            height=dp(28),
        )
        error_title.bind(size=lambda w, s: setattr(w, 'text_size', (s[0], None)))
        content.add_widget(error_title)
        
        error_card = Card(orientation='vertical', spacing=dp(4))
        self.errors_container = BoxLayout(
            orientation='vertical',
            spacing=dp(4),
            size_hint_y=None,
        )
        self.errors_container.bind(
            minimum_height=self.errors_container.setter('height')
        )
        error_card.add_widget(self.errors_container)
        content.add_widget(error_card)
        
        # Butonlar
        back_btn = SolidButton(
            text='Dashboard\'a Dön',
            color_hex=COLORS['primary'],
        )
        back_btn.bind(on_press=lambda x: App.get_running_app().switch_screen(
            'patient_dashboard', direction='right'))
        content.add_widget(back_btn)
        
        content.add_widget(BoxLayout(size_hint_y=None, height=dp(20)))
        
        scroll.add_widget(content)
        root.add_widget(scroll)
        self.add_widget(root)
