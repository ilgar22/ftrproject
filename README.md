# PhysioConnect - Mobil Uygulama

Kivy + MediaPipe ile geliştirilmiş fizyoterapi takip uygulaması.

## 📁 Proje Yapısı

```
physio_app/
├── main.py                     # Uygulama giriş noktası
├── requirements.txt            # Python bağımlılıkları
├── buildozer.spec              # Android APK derleme ayarları
│
├── services/
│   ├── api_service.py          # Replit backend API bağlantısı
│   ├── pose_engine.py          # MediaPipe pose analiz motoru (heavy, 3B)
│   └── phase_aligner.py        # Faz şablonu + çevrimiçi hizalama / tekrar sayımı
│
├── screens/
│   ├── login_screen.py         # Giriş ekranı
│   ├── patient_dashboard.py    # Hasta ana paneli
│   ├── doctor_dashboard.py     # Doktor ana paneli
│   ├── exercise_list.py        # Egzersiz listesi
│   ├── exercise_session.py     # ★ Kamera + canlı pose analizi
│   └── results_screen.py       # Seans sonuç raporu
│
└── widgets/
    └── components.py           # Ortak UI bileşenleri
```

## ⚙️ Kurulum (PC'de Test)

```bash
# 1. Sanal ortam oluştur
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 2. Bağımlılıkları yükle
pip install -r requirements.txt

# 3. Replit URL'ini ayarla
# services/api_service.py dosyasında şu satırı düzenle:
# BASE_URL = "https://YOUR-APP.replit.app/api"

# 4. Çalıştır
python main.py
```

## 📱 Android APK Derleme

```bash
# Buildozer yükle (Linux/macOS)
pip install buildozer

# İlk derleme (uzun sürer ~15-20 dk)
buildozer android debug

# APK konumu: bin/physioconnect-1.0.0-debug.apk
```

## 🔌 Replit API Entegrasyonu

Uygulama backend adresini ortam değişkeninden okur:

- `PHYSIO_API_BASE_URL=https://YOUR-APP.replit.app`
- Uygulama bunu otomatik olarak `.../api` formatına çevirir.

Windows PowerShell örneği:

```powershell
$env:PHYSIO_API_BASE_URL="https://YOUR-APP.replit.app"
python main.py
```

Alternatif olarak `services/api_service.py` içindeki varsayılan URL'i doğrudan değiştirebilirsin.

Uygulama şu endpoint'leri bekler:

| Endpoint | Method | Açıklama |
|---|---|---|
| `/api/auth/login` | POST | Giriş |
| `/api/exercises` | GET | Hasta egzersizleri |
| `/api/exercises/{id}` | GET | Egzersiz detayı |
| `/api/exercises/{id}/pose-data` | GET | Referans pose JSON |
| `/api/exercises/{id}/results` | POST | Seans sonucu gönder |
| `/api/patient/progress` | GET | İlerleme istatistikleri |
| `/api/doctor/patients` | GET | Hasta listesi |

### Pose Data Formatı (GET /pose-data)

```json
[
  {
    "frame": 0,
    "angles": {
      "sol_diz": 145.2,
      "sag_diz": 143.8,
      "sol_kalca": 165.0,
      "sag_kalca": 164.5,
      "sol_omuz": 90.0,
      "sag_omuz": 88.5
    }
  },
  ...
]
```

## 🧠 Pose Engine Mantığı (v3)

1. **Poz kestirimi**: MediaPipe Pose Landmarker **heavy** modeli (`services/pose_landmarker_heavy.task`,
   ilk çalıştırmada otomatik indirilir; `POSE_MODEL_VARIANT=full|lite` ile değiştirilebilir).
   Eklem açıları 3B **dünya koordinatlarından** (metre, kalça merkezli) hesaplanır; kamera açısına bağımlılık azalır.
   Açıların yanına el ve ayak bileği **konumları** eklenir (kalça merkezli, gövde boyuna normalize 3B koordinat — 12 öznitelik).
2. **Referans şablonu** (`services/phase_aligner.py` → `build_template`): doktor videosundaki açı izleri
   lider eklemin ilerleme sinyaline göre tekrarlara bölünür; her tekrar 48 faz örneğine yeniden örneklenir.
   Faz başına öznitelik **ortalaması** ve tekrarlar arası değişkenlikten öğrenilen **tolerans (sigma)** çıkarılır (açılar derece, konumlar gövde birimi).
   Sabit açı eşikleri yoktur; tolerans referanstan gelir.
3. **Çevrimiçi hizalama** (`OnlineAligner`): canlı akış, döngüsel şablona kare kare dinamik programlama ile
   hizalanır (kal / 1 / 2 / 3 faz ilerle, unutma katsayılı maliyet, histerezisli yol seçimi).
   Tempo farkı (hızlı/yavaş yapma) hizalamada çözülür.
4. **Tekrar sayımı**: şablon sonundan başına **sarma** = bir tekrar. Tekrar, lider eklem tepe fazına
   ulaşmışsa ve döngü boyunca ortalama kalite eşiği aşılmışsa sayılır; aksi halde başarısız deneme olarak
   raporlanır (`amplitude`: tam açılmadı, `form`: referansa uymadı).
5. **Geri bildirim**: hizalanan fazdaki eklem z-skoru (|açı − ortalama| / sigma): <1,5 doğru, 1,5–2,5 uyarı, >2,5 hata.

Sentetik testler: `python tests/test_phase_aligner.py`

### Pose Data Formatı (v3)

```json
{
  "frames": [{"frame": 0, "angles": {"sol_diz": 175.2, ...}, "progress": 0.0}, ...],
  "profile": {"rep_joint": "sol_diz", "joint_ranges": {...}, "reference_reps": 4},
  "template": {"phases": 48, "joints": [...], "mu": [[...]], "sigma": [[...]],
               "weights": [...], "peak_phase": 24, "lead_joints": ["sol_diz", "sag_diz"]}
}
```
Eski format (yalnızca `frames`) yüklenirse şablon istemci tarafında kurulur.

## 🎨 Demo Modu

API bağlantısı olmadan test etmek için login ekranındaki
**"Demo Hasta"** veya **"Demo Doktor"** butonlarını kullan.
