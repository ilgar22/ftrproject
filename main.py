"""
PhysioConnect - Fizyoterapi Mobil Uygulamasi
Kivy + MediaPipe ile gelistirilmis hasta egzersiz takip sistemi.
"""

import os

os.environ.setdefault('KIVY_NO_ENV_CONFIG', '1')

from kivy.app import App
from kivy.core.window import Window
from kivy.uix.screenmanager import ScreenManager, SlideTransition
from kivy.utils import get_color_from_hex

from screens.doctor_dashboard import DoctorDashboard
from screens.exercise_list import ExerciseListScreen
from screens.exercise_session import ExerciseSessionScreen
from screens.login_screen import LoginScreen
from screens.patient_dashboard import PatientDashboard
from screens.results_screen import ResultsScreen

Window.clearcolor = get_color_from_hex('#F4F6F9')


class PhysioApp(App):
    title = 'PhysioConnect'

    def build(self):
        self.sm = ScreenManager(transition=SlideTransition())

        screens = [
            LoginScreen(name='login'),
            PatientDashboard(name='patient_dashboard'),
            DoctorDashboard(name='doctor_dashboard'),
            ExerciseListScreen(name='exercise_list'),
            ExerciseSessionScreen(name='exercise_session'),
            ResultsScreen(name='results'),
        ]

        for screen in screens:
            self.sm.add_widget(screen)

        self.sm.current = 'login'
        return self.sm

    def switch_screen(self, screen_name, direction='left'):
        self.sm.transition.direction = direction
        self.sm.current = screen_name

    def on_stop(self):
        for screen in self.sm.screens:
            if hasattr(screen, 'cleanup'):
                screen.cleanup()


if __name__ == '__main__':
    PhysioApp().run()
