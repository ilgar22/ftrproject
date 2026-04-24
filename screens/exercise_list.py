"""
Egzersiz Listesi Ekranı
"""
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.graphics import Color, Rectangle
from kivy.utils import get_color_from_hex
from kivy.metrics import dp
from kivy.app import App
from widgets.components import TopBar, ExerciseCard, c, COLORS
from services.api_service import api


class ExerciseListScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._build()

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
            title='Egzersizlerim',
            back_cb=lambda: App.get_running_app().switch_screen(
                'patient_dashboard', direction='right')
        ))
        scroll = ScrollView()
        self.content = BoxLayout(
            orientation='vertical', padding=dp(16), spacing=dp(10),
            size_hint_y=None,
        )
        self.content.bind(minimum_height=self.content.setter('height'))
        scroll.add_widget(self.content)
        root.add_widget(scroll)
        self.add_widget(root)

    def on_enter(self):
        api.get_exercises(self._on_loaded)

    def _on_loaded(self, success, data):
        from kivy.clock import Clock
        def update(dt):
            self.content.clear_widgets()
            for ex in (data or []):
                card = ExerciseCard(
                    exercise_data=ex,
                    on_press_cb=self._open,
                )
                self.content.add_widget(card)
        Clock.schedule_once(update, 0)

    def _open(self, ex):
        app = App.get_running_app()
        app.sm.get_screen('exercise_session').load_exercise(ex)
        app.switch_screen('exercise_session')
