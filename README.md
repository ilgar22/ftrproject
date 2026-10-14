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
│   └── pose_engine.py          # MediaPipe pose analiz motoru
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

## 🧠 Pose Engine Mantığı

1. **Referans yükleme**: Doktorun videosu Replit'te işlenir → eklem açıları JSON olarak kaydedilir
2. **Gerçek zamanlı analiz**: MediaPipe her frame'de 33 landmark tespit eder
3. **Açı hesaplama**: 8 kritik eklem için açı değerleri çıkarılır
4. **Karşılaştırma**: Sliding window DTW ile referans ile anlık poz karşılaştırılır
5. **Geri bildirim**: >20° fark = uyarı, >35° fark = hata
6. **Tekrar sayma**: Benzerlik eşiği aşılınca tekrar sayacı artar

## 🎨 Demo Modu

API bağlantısı olmadan test etmek için login ekranındaki
**"Demo Hasta"** veya **"Demo Doktor"** butonlarını kullan.
