"""
Doktor Paneli - Hasta listesi ve egzersiz takibi
"""

from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.spinner import Spinner
from kivy.graphics import Color, Rectangle, RoundedRectangle, Line
from kivy.utils import get_color_from_hex
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.app import App
import threading

from widgets.components import Card, TopBar, SolidButton, GlowButton, c, COLORS
from services.api_service import api
from services.pose_engine import PoseEngine


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
            color=c('button_text'),
            background_color=(0, 0, 0, 0),
            size_hint_x=None,
            width=dp(70),
        )
        if on_view_cb:
            view_btn.bind(on_press=lambda x: on_view_cb(patient))
        
        self.add_widget(info)
        self.add_widget(view_btn)


class AssignmentCard(Card):
    def __init__(self, assignment, **kwargs):
        super().__init__(orientation='vertical', spacing=dp(4), size_hint_y=None, height=dp(86), **kwargs)
        ex_name = assignment.get('name', 'Egzersiz')
        patient_name = assignment.get('assigned_patient_name') or 'Hasta'
        status = assignment.get('status', 'pending')
        status_text = 'Tamamlandi' if status == 'completed' else 'Bekleniyor'
        status_color = c('success') if status == 'completed' else c('warning')

        title = Label(
            text=ex_name,
            font_size=dp(14),
            bold=True,
            color=c('text_main'),
            halign='left',
            size_hint_y=None,
            height=dp(24),
        )
        title.bind(size=lambda w, s: setattr(w, 'text_size', (s[0], None)))

        details = Label(
            text=f"Hasta: {patient_name}  |  Tekrar: {assignment.get('daily_reps', 0)}",
            font_size=dp(12),
            color=c('text_sub'),
            halign='left',
            size_hint_y=None,
            height=dp(20),
        )
        details.bind(size=lambda w, s: setattr(w, 'text_size', (s[0], None)))

        status_lbl = Label(
            text=f"Durum: {status_text}",
            font_size=dp(12),
            color=status_color,
            halign='left',
            size_hint_y=None,
            height=dp(18),
        )
        status_lbl.bind(size=lambda w, s: setattr(w, 'text_size', (s[0], None)))

        self.add_widget(title)
        self.add_widget(details)
        self.add_widget(status_lbl)


class DoctorDashboard(Screen):
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._upload_popup = None
        self._selected_video_path = ''
        self._selected_patient_id = None
        self._selected_patient_name = ''
        self._patients = []
        self._build()
    
    def on_enter(self):
        api.get_patients(self._on_patients_loaded)
        api.get_doctor_assignments(self._on_assignments_loaded)
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
            color=c('button_text'),
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
            ('Hasta', '3', 'Toplam Hasta', c('primary')),
            ('Aktif', '2', 'Aktif Bugun',  c('success')),
            ('Risk', '1', 'Dusuk Uyum',  c('warning')),
        ]:
            card = Card(orientation='vertical', spacing=dp(2))
            card.add_widget(Label(text=icon, font_size=dp(14),
                                   size_hint_y=None, height=dp(26)))
            card.add_widget(Label(text=val, font_size=dp(18), bold=True,
                                   color=accent, size_hint_y=None, height=dp(22)))
            card.add_widget(Label(text=label, font_size=dp(11), color=c('text_sub'),
                                   size_hint_y=None, height=dp(16)))
            stats.add_widget(card)
        
        content.add_widget(stats)

        upload_card = Card(orientation='vertical', spacing=dp(8), size_hint_y=None, height=dp(130))
        upload_card.add_widget(Label(
            text='Yeni egzersiz yukle',
            font_size=dp(15),
            bold=True,
            color=c('text_main'),
            halign='left',
            size_hint_y=None,
            height=dp(24),
        ))
        self.upload_status = Label(
            text='Doktor videosu secin ve hastaya atin',
            font_size=dp(12),
            color=c('text_sub'),
            halign='left',
            size_hint_y=None,
            height=dp(20),
        )
        self.upload_status.bind(size=lambda w, s: setattr(w, 'text_size', (s[0], None)))
        upload_btn = SolidButton(text='Galeriden Video Sec ve Ata', color_hex=COLORS['primary'])
        upload_btn.bind(on_press=lambda *_: self._open_upload_popup())
        upload_card.add_widget(self.upload_status)
        upload_card.add_widget(upload_btn)
        content.add_widget(upload_card)
        
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

        asg_title = Label(
            text='Atanan Egzersiz Durumlari',
            font_size=dp(16),
            bold=True,
            color=c('text_main'),
            halign='left',
            size_hint_y=None,
            height=dp(28),
        )
        asg_title.bind(size=lambda w, s: setattr(w, 'text_size', (s[0], None)))
        content.add_widget(asg_title)

        self.assignments_box = BoxLayout(
            orientation='vertical',
            spacing=dp(8),
            size_hint_y=None,
        )
        self.assignments_box.bind(minimum_height=self.assignments_box.setter('height'))
        content.add_widget(self.assignments_box)
        
        content.add_widget(BoxLayout(size_hint_y=None, height=dp(30)))
        
        scroll.add_widget(content)
        root.add_widget(scroll)
        self.add_widget(root)
    
    def _on_patients_loaded(self, success, data):
        def update(dt):
            self.patients_box.clear_widgets()
            patients = data if success and data else DEMO_PATIENTS
            self._patients = patients
            for pt in patients:
                card = PatientCard(pt, on_view_cb=self._view_patient)
                self.patients_box.add_widget(card)
        Clock.schedule_once(update, 0)
    
    def _view_patient(self, patient):
        api.get_doctor_assignments(
            lambda success, data: self._show_patient_assignments(patient, data if success else [])
        )

    def _show_patient_assignments(self, patient, assignments):
        def update(_):
            pid = patient.get('id')
            patient_name = patient.get('name', 'Hasta')
            filtered = [
                item for item in (assignments or [])
                if item.get('assigned_patient_id') == pid
            ]

            root = BoxLayout(orientation='vertical', spacing=dp(8), padding=dp(10))
            title = Label(
                text=f"{patient_name} - Doktor Atamalari",
                font_size=dp(15),
                bold=True,
                color=c('text_main'),
                size_hint_y=None,
                height=dp(28),
            )
            root.add_widget(title)

            list_wrap = ScrollView()
            list_box = BoxLayout(
                orientation='vertical',
                spacing=dp(8),
                size_hint_y=None,
            )
            list_box.bind(minimum_height=list_box.setter('height'))

            if not filtered:
                list_box.add_widget(Label(
                    text='Bu hasta icin atanmis egzersiz yok',
                    font_size=dp(12),
                    color=c('text_sub'),
                    size_hint_y=None,
                    height=dp(36),
                ))
            else:
                for ex in filtered:
                    status = ex.get('status', 'pending')
                    status_text = 'Tamamlandi' if status == 'completed' else 'Bekleniyor'
                    status_color = c('success') if status == 'completed' else c('warning')

                    row = Card(orientation='vertical', spacing=dp(4), size_hint_y=None, height=dp(92))
                    line1 = Label(
                        text=ex.get('name', 'Egzersiz'),
                        font_size=dp(14),
                        bold=True,
                        color=c('text_main'),
                        halign='left',
                        size_hint_y=None,
                        height=dp(24),
                    )
                    line1.bind(size=lambda w, s: setattr(w, 'text_size', (s[0], None)))

                    line2 = Label(
                        text=f"Program: {ex.get('schedule', 'Gunluk')}  |  Tekrar: {ex.get('daily_reps', 0)}",
                        font_size=dp(12),
                        color=c('text_sub'),
                        halign='left',
                        size_hint_y=None,
                        height=dp(20),
                    )
                    line2.bind(size=lambda w, s: setattr(w, 'text_size', (s[0], None)))

                    line3 = Label(
                        text=f"Durum: {status_text}",
                        font_size=dp(12),
                        color=status_color,
                        halign='left',
                        size_hint_y=None,
                        height=dp(20),
                    )
                    line3.bind(size=lambda w, s: setattr(w, 'text_size', (s[0], None)))

                    row.add_widget(line1)
                    row.add_widget(line2)
                    row.add_widget(line3)
                    list_box.add_widget(row)

            list_wrap.add_widget(list_box)
            root.add_widget(list_wrap)

            close_btn = SolidButton(text='Kapat', color_hex=COLORS['primary'])
            popup = Popup(
                title='Hasta Detay',
                content=root,
                size_hint=(0.85, 0.82),
            )
            close_btn.bind(on_press=lambda *_: popup.dismiss())
            root.add_widget(close_btn)
            popup.open()

        Clock.schedule_once(update, 0)

    def _on_assignments_loaded(self, success, data):
        def update(dt):
            self.assignments_box.clear_widgets()
            assignments = data if success and data else []
            if not assignments:
                self.assignments_box.add_widget(Label(
                    text='Henuz atanmis egzersiz yok',
                    font_size=dp(12),
                    color=c('text_sub'),
                    size_hint_y=None,
                    height=dp(36),
                ))
                return
            for item in assignments:
                self.assignments_box.add_widget(AssignmentCard(item))
        Clock.schedule_once(update, 0)

    def _open_upload_popup(self):
        root = BoxLayout(orientation='vertical', spacing=dp(8), padding=dp(10))
        available_patients = self._patients or DEMO_PATIENTS
        patient_items = [f"{p.get('id')} - {p.get('name', 'Hasta')}" for p in available_patients]
        default_patient = available_patients[0] if available_patients else {'id': None, 'name': 'Hasta'}
        self._selected_patient_id = default_patient.get('id')
        self._selected_patient_name = default_patient.get('name', 'Hasta')

        name_input = TextInput(
            text='Biceps Curl Doktor Referansi',
            multiline=False,
            size_hint_y=None,
            height=dp(40),
            background_normal='',
            background_active='',
            background_color=get_color_from_hex(COLORS['bg_surface']),
            foreground_color=get_color_from_hex(COLORS['text_main']),
        )
        reps_input = TextInput(
            text='12',
            multiline=False,
            size_hint_y=None,
            height=dp(40),
            background_normal='',
            background_active='',
            background_color=get_color_from_hex(COLORS['bg_surface']),
            foreground_color=get_color_from_hex(COLORS['text_main']),
        )
        schedule_input = TextInput(
            text='Sabah ve Aksam',
            multiline=False,
            size_hint_y=None,
            height=dp(40),
            background_normal='',
            background_active='',
            background_color=get_color_from_hex(COLORS['bg_surface']),
            foreground_color=get_color_from_hex(COLORS['text_main']),
        )
        patient_spinner = Spinner(
            text=patient_items[0] if patient_items else 'Hasta bulunamadi',
            values=patient_items,
            size_hint_y=None,
            height=dp(40),
            background_normal='',
            background_color=get_color_from_hex(COLORS['bg_surface']),
            color=c('text_main'),
        )
        patient_spinner.bind(text=lambda _, value: self._on_patient_selected(value, available_patients))

        path_label = Label(text='Video secilmedi', color=c('text_sub'), halign='left', size_hint_y=None, height=dp(20))
        path_label.bind(size=lambda w, s: setattr(w, 'text_size', (s[0], None)))

        choose_btn = GlowButton(text='Video Dosyasi Sec')
        choose_btn.bind(on_press=lambda *_: self._choose_video_file(path_label))

        submit_btn = SolidButton(text='Pose Hesapla ve Hastaya Ata', color_hex=COLORS['success'])
        submit_btn.bind(on_press=lambda *_: self._start_upload_flow(
            name_input.text.strip(),
            reps_input.text.strip(),
            schedule_input.text.strip(),
            self._selected_video_path,
        ))

        root.add_widget(Label(text='Egzersiz adi', color=c('text_sub'), size_hint_y=None, height=dp(18)))
        root.add_widget(name_input)
        root.add_widget(Label(text='Gunluk tekrar', color=c('text_sub'), size_hint_y=None, height=dp(18)))
        root.add_widget(reps_input)
        root.add_widget(Label(text='Program', color=c('text_sub'), size_hint_y=None, height=dp(18)))
        root.add_widget(schedule_input)
        root.add_widget(Label(text='Hasta secimi', color=c('text_sub'), size_hint_y=None, height=dp(18)))
        root.add_widget(patient_spinner)
        root.add_widget(path_label)
        root.add_widget(choose_btn)
        root.add_widget(submit_btn)
        self._upload_popup = Popup(
            title='Doktor videosundan egzersiz olustur',
            content=root,
            size_hint=(0.85, 0.85),
        )
        self._upload_popup.open()

    def _choose_video_file(self, path_label):
        chooser = FileChooserListView(filters=['*.mp4', '*.mov', '*.avi', '*.mkv'])
        wrap = BoxLayout(orientation='vertical', spacing=dp(8), padding=dp(8))
        pick_btn = SolidButton(text='Sec', color_hex=COLORS['primary'])
        cancel_btn = GlowButton(text='Iptal')

        popup = Popup(title='Video sec', content=wrap, size_hint=(0.9, 0.9))
        pick_btn.bind(on_press=lambda *_: self._on_file_picked(chooser.selection, path_label, popup))
        cancel_btn.bind(on_press=lambda *_: popup.dismiss())

        wrap.add_widget(chooser)
        wrap.add_widget(pick_btn)
        wrap.add_widget(cancel_btn)
        popup.open()

    def _on_file_picked(self, selection, path_label, popup):
        if selection:
            self._selected_video_path = selection[0]
            path_label.text = f'Secilen: {self._selected_video_path}'
        popup.dismiss()

    def _start_upload_flow(self, name, reps, schedule, video_path):
        if not video_path:
            self.upload_status.text = 'Lutfen once video secin'
            self.upload_status.color = c('warning')
            return
        if self._selected_patient_id is None:
            self.upload_status.text = 'Lutfen bir hasta secin'
            self.upload_status.color = c('warning')
            return

        if self._upload_popup:
            self._upload_popup.dismiss()
            self._upload_popup = None

        self.upload_status.text = 'Video analiz ediliyor, pose cikariliyor...'
        self.upload_status.color = c('warning')

        threading.Thread(
            target=self._process_video_upload,
            args=(name, reps, schedule, video_path, self._selected_patient_id, self._selected_patient_name),
            daemon=True
        ).start()

    def _process_video_upload(self, name, reps, schedule, video_path, patient_id, patient_name):
        engine = PoseEngine()
        Clock.schedule_once(lambda *_: self._set_upload_status(
            'Adim 1/5: Video alindi, offline analiz baslatildi', 'warning'
        ), 0)

        def on_progress(progress, frame_idx=0, total_frames=0):
            pct = int(progress * 100)
            if pct < 20:
                step = 'Adim 2/5: Karelerden pose landmark cikariliyor'
            elif pct < 45:
                step = 'Adim 3/5: Eklem acilari hesaplanıyor'
            elif pct < 70:
                step = 'Adim 4/5: Normalize trajektori olusturuluyor'
            else:
                step = 'Adim 5/5: Zamansal referans model kuruluyor'
            detail = f"{step} ({frame_idx}/{total_frames})" if total_frames else step
            Clock.schedule_once(lambda *_: self._set_upload_status(detail, 'warning'), 0)

        pose_sequence = engine.extract_reference_from_video(video_path, callback_progress=on_progress)
        engine.release()

        frames = pose_sequence.get('frames', []) if isinstance(pose_sequence, dict) else (pose_sequence or [])
        if not frames:
            Clock.schedule_once(lambda *_: self._set_upload_status(
                'Video analizi basarisiz: pose verisi bulunamadi', 'error'
            ), 0)
            return

        payload = {
            'name': name or 'Doktor Egzersizi',
            'daily_reps': int(reps) if str(reps).isdigit() else 10,
            'schedule': schedule or 'Gunluk',
            'description': 'Doktor videosundan olusturuldu',
            'assigned_patient_id': patient_id,
            'assigned_patient_name': patient_name,
        }
        Clock.schedule_once(lambda *_: self._set_upload_status(
            'Referans model hazir, hastaya ataniyor...', 'warning'
        ), 0)
        api.create_exercise_from_video(payload, pose_sequence, video_path, self._on_exercise_created)

    def _on_exercise_created(self, success, data):
        def update(_):
            if success:
                name = data.get('name', 'Egzersiz')
                patient = data.get('assigned_patient_name', 'hasta')
                self._set_upload_status(f'{name} -> {patient} atandi', 'success')
                api.get_doctor_assignments(self._on_assignments_loaded)
            else:
                self._set_upload_status(f'Atama hatasi: {data}', 'error')
        Clock.schedule_once(update, 0)

    def _on_patient_selected(self, spinner_value, available_patients):
        for p in available_patients:
            label = f"{p.get('id')} - {p.get('name', 'Hasta')}"
            if label == spinner_value:
                self._selected_patient_id = p.get('id')
                self._selected_patient_name = p.get('name', 'Hasta')
                return

    def _set_upload_status(self, text, tone='text_sub'):
        self.upload_status.text = text
        self.upload_status.color = c(tone)
