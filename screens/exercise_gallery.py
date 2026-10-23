"""Doktor egzersiz kutuphanesi."""

import os

import cv2
from kivy.app import App
from kivy.clock import Clock
from kivy.graphics.texture import Texture
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.screenmanager import Screen
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput
from kivy.graphics import Color, Rectangle
from kivy.utils import get_color_from_hex

from services.api_service import api
from widgets.components import COLORS, Card, GlowButton, SolidButton, TopBar, c


class ExerciseGalleryScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._items = []
        self._preview_cap = None
        self._preview_event = None
        self._preview_popup = None
        self._preview_image = None
        self._status = None
        self._grid = None
        self._build()

    def on_enter(self):
        self._load()

    def _build(self):
        root = BoxLayout(orientation='vertical')
        with root.canvas.before:
            Color(*get_color_from_hex(COLORS['bg_dark']))
            self._bg = Rectangle(pos=root.pos, size=root.size)
        root.bind(
            pos=lambda *a: setattr(self._bg, 'pos', root.pos),
            size=lambda *a: setattr(self._bg, 'size', root.size),
        )
        root.add_widget(TopBar(title='Egzersiz Kutuphanesi', back_cb=self._back))
        body = BoxLayout(orientation='vertical', padding=dp(12), spacing=dp(8))
        self._status = Label(
            text='Kutuphane yukleniyor...',
            color=c('text_sub'),
            size_hint_y=None,
            height=dp(24),
            halign='left',
        )
        self._status.bind(size=lambda w, s: setattr(w, 'text_size', (s[0], None)))
        new_btn = SolidButton(text='Yeni kayit', color_hex=COLORS['primary'])
        new_btn.size_hint_y = None
        new_btn.height = dp(46)
        new_btn.bind(on_press=lambda *_: self._new_recording())
        body.add_widget(self._status)
        body.add_widget(new_btn)
        scroll = ScrollView()
        self._grid = GridLayout(cols=1, spacing=dp(10), size_hint_y=None, padding=dp(2))
        self._grid.bind(minimum_height=self._grid.setter('height'))
        scroll.add_widget(self._grid)
        body.add_widget(scroll)
        root.add_widget(body)
        self.add_widget(root)

    def _back(self, *_):
        self._close_preview()
        App.get_running_app().switch_screen('doctor_dashboard', direction='right')

    def _load(self):
        api.get_exercise_library(self._on_loaded)

    def _on_loaded(self, success, data):
        def update(_dt):
            self._grid.clear_widgets()
            if not success:
                self._status.text = str(data or 'Kutuphane alinamadi')
                self._status.color = c('warning')
                data_items = []
            else:
                data_items = data or []
                self._status.text = f'{len(data_items)} egzersiz'
                self._status.color = c('text_sub')
            self._items = list(data_items)
            if not self._items:
                self._grid.add_widget(Label(
                    text='Kutuphane bos. Yeni kayit ile ekleyin.',
                    color=c('text_sub'),
                    size_hint_y=None,
                    height=dp(40),
                ))
                return
            for item in self._items:
                self._grid.add_widget(self._card(item))
        Clock.schedule_once(update, 0)

    def _card(self, item):
        card = Card(orientation='horizontal', spacing=dp(8), size_hint_y=None, height=dp(150))
        thumb = Image(size_hint_x=None, width=dp(110), fit_mode='contain')
        path = item.get('thumbnail_path') or item.get('thumbnail_url') or ''
        if path and (path.startswith('http') or os.path.exists(path)):
            thumb.source = path
        info = BoxLayout(orientation='vertical', spacing=dp(4))
        duration = item.get('duration_seconds')
        if duration is None:
            duration = item.get('duration') or 0
        duration = float(duration)
        info.add_widget(Label(text=item.get('name') or 'Egzersiz', color=c('text_main'), bold=True, halign='left'))
        info.add_widget(Label(text=f'Sure: {int(duration // 60)}:{int(duration % 60):02d}', color=c('text_sub'), halign='left'))
        buttons = BoxLayout(spacing=dp(4), size_hint_y=None, height=dp(36))
        for text, handler in (
            ('Yeniden adlandir', self._rename),
            ('Hastaya ata', self._assign),
            ('Onizle', self._preview),
            ('Sil', self._confirm_delete),
        ):
            btn = GlowButton(text=text)
            btn.font_size = dp(11)
            btn.bind(on_press=lambda _b, it=item, fn=handler: fn(it))
            buttons.add_widget(btn)
        info.add_widget(buttons)
        card.add_widget(thumb)
        card.add_widget(info)
        return card

    def _new_recording(self, *_):
        doctor = App.get_running_app().sm.get_screen('doctor_dashboard')
        doctor._open_upload_popup()

    def _rename(self, item):
        box = BoxLayout(orientation='vertical', spacing=dp(8), padding=dp(8))
        field = TextInput(text=item.get('name') or '', multiline=False)
        box.add_widget(field)
        save = SolidButton(text='Kaydet', color_hex=COLORS['primary'])
        popup = Popup(title='Yeniden adlandir', content=box, size_hint=(0.8, 0.4))
        box.add_widget(save)

        def commit(*_):
            name = field.text.strip()
            if not name or len(name) > 60:
                self._status.text = 'Ad 1-60 karakter olmali'
                self._status.color = c('error')
                return
            previous = item.get('name')
            item['name'] = name
            self._on_loaded(True, self._items)

            def done(ok, data):
                def apply(_dt):
                    if not ok:
                        item['name'] = previous
                        self._status.text = str(data or 'Ad kaydedilemedi')
                        self._status.color = c('error')
                        self._on_loaded(True, self._items)
                    else:
                        self._status.text = 'Ad guncellendi'
                        self._status.color = c('success')
                        self._load()
                Clock.schedule_once(apply, 0)

            api.rename_library_exercise(item.get('id'), name, done)
            popup.dismiss()

        save.bind(on_press=commit)
        popup.open()

    def _assign(self, item):
        from screens.doctor_dashboard import DEMO_PATIENTS
        patients = DEMO_PATIENTS
        box = BoxLayout(orientation='vertical', spacing=dp(8), padding=dp(8))
        labels = [f"{p.get('id')} - {p.get('name')}" for p in patients]
        spinner = Spinner(text=labels[0], values=labels, size_hint_y=None, height=dp(40))
        reps = TextInput(text='10', multiline=False, size_hint_y=None, height=dp(40))
        save = SolidButton(text='Ata', color_hex=COLORS['primary'])
        box.add_widget(Label(text='Hasta', color=c('text_sub'), size_hint_y=None, height=dp(20)))
        box.add_widget(spinner)
        box.add_widget(Label(text='Tekrar sayisi', color=c('text_sub'), size_hint_y=None, height=dp(20)))
        box.add_widget(reps)
        box.add_widget(save)
        popup = Popup(title='Hastaya ata', content=box, size_hint=(0.8, 0.55))

        def commit(*_):
            selected = patients[0]
            for person in patients:
                if f"{person.get('id')} - {person.get('name')}" == spinner.text:
                    selected = person
            try:
                count = int(reps.text.strip())
            except ValueError:
                count = 10
            if count <= 0:
                count = 10

            def done(ok, data):
                def apply(_dt):
                    if ok:
                        self._status.text = f"Atandi: {item.get('name')} ({count})"
                        self._status.color = c('success')
                    else:
                        self._status.text = str(data or 'Atama basarisiz')
                        self._status.color = c('error')
                Clock.schedule_once(apply, 0)

            api.assign_library_exercise(
                item.get('id'), selected.get('id'), count, done, patient_name=selected.get('name', '')
            )
            popup.dismiss()

        save.bind(on_press=commit)
        popup.open()

    def _preview(self, item):
        path = item.get('video_path')
        if not path or not os.path.exists(path):
            self._status.text = 'Video dosyasi bulunamadi'
            self._status.color = c('error')
            return
        self._close_preview()
        root = BoxLayout(orientation='vertical', spacing=dp(8), padding=dp(8))
        self._preview_image = Image(fit_mode='contain')
        close = SolidButton(text='Kapat', color_hex=COLORS['primary'])
        popup = Popup(title='Onizle', content=root, size_hint=(0.9, 0.85))
        close.bind(on_press=lambda *_: self._close_preview())
        popup.bind(on_dismiss=lambda *_: self._close_preview())
        root.add_widget(self._preview_image)
        root.add_widget(close)
        self._preview_popup = popup
        self._preview_cap = cv2.VideoCapture(path)
        if not self._preview_cap.isOpened():
            self._status.text = 'Video acilamadi'
            self._close_preview()
            return
        popup.open()
        self._preview_event = Clock.schedule_interval(self._draw_preview, 1 / 25)

    def _draw_preview(self, _dt):
        if self._preview_cap is None or self._preview_image is None:
            return
        ok, frame = self._preview_cap.read()
        if not ok:
            self._preview_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ok, frame = self._preview_cap.read()
            if not ok:
                return
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb = cv2.flip(rgb, 0)
        texture = Texture.create(size=(frame.shape[1], frame.shape[0]), colorfmt='rgb')
        texture.blit_buffer(rgb.tobytes(), colorfmt='rgb', bufferfmt='ubyte')
        self._preview_image.texture = texture

    def _close_preview(self, *_):
        if self._preview_event:
            self._preview_event.cancel()
            self._preview_event = None
        if self._preview_cap:
            self._preview_cap.release()
            self._preview_cap = None
        if self._preview_popup and self._preview_popup.parent:
            popup = self._preview_popup
            self._preview_popup = None
            popup.dismiss()
        self._preview_popup = None
        self._preview_image = None

    def _confirm_delete(self, item):
        box = BoxLayout(orientation='vertical', spacing=dp(8), padding=dp(8))
        box.add_widget(Label(
            text='Silinsin mi? Atanmis egzersizler durur.',
            color=c('text_main'),
        ))
        yes = SolidButton(text='Sil', color_hex=COLORS['error'])
        box.add_widget(yes)
        popup = Popup(title='Sil', content=box, size_hint=(0.75, 0.4))

        def commit(*_):
            def done(ok, data):
                def apply(_dt):
                    self._status.text = 'Silindi' if ok else str(data or 'Silinemedi')
                    self._status.color = c('success') if ok else c('warning')
                    self._load()
                Clock.schedule_once(apply, 0)
            api.delete_library_exercise(item.get('id'), done)
            popup.dismiss()

        yes.bind(on_press=commit)
        popup.open()
