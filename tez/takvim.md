# Tez Çalışma Takvimi — 20 Kasım → 18 Aralık 2026

Hedef: `yapilacaklar.md` dosyasındaki üç maddenin (testler + teze yazım) 18 Aralık 2026 Cuma günü bitmiş olması.
Güncelleme: 20.11.2026 — referanslar mevcut fizyoterapist videolarından kesiliyor; **fizyoterapistten hiçbir iş istenmiyor.**

## Ön koşullar (ilk hafta bitmeli)

- **Uygulama değişiklikleri** (Madde 3 bunlara bağlı):
  - Hasta oturumunda ham kamera videosunun ve her tekrar kararının (zaman, sayıldı/reddedildi, neden) kaydedilmesi.
  - Video yükleme yolundaki döndürme hatasının düzeltilmesi (`pose_engine.py` yüklenen videoyu 90° döndürüyor).
  - Günlük hedefin 15'ten büyük girilebilmesi (oturum hedefe ulaşınca kendiliğinden kapanmasın).
- **Gönüllüler:** 2 kişi; 7–8 Aralık için tarihleri ilk gün kesinleşmeli.

## Hafta 1 — 23–27 Kasım: Hazırlık, Madde 1 başlangıcı, Madde 2

| Gün | İş | Madde |
|---|---|---|
| Pzt 23 | Veri kümelerini indir, erişim koşullarını kontrol et (REHAB24-6, UCO) | 1.1 |
| Pzt 23 | Veri kümelerinden bizim 6 harekete benzeyenleri seç | 1.2 |
| Pzt 23 | Gönüllü tarihlerini kesinleştir | — |
| Pzt 23 – Sal 24 | Fizyoterapist videolarından 6 hareketi tablodaki aralıklarla kes | 2.1 |
| Sal 24 | Her hareket için hareketli/sabit eklemleri yazılı belirle | 2.2 |
| Sal 24 – Çar 25 | Literatür taraması: her hareket için en sık bildirilen 2 hatayı belirle (A ve B) | 3.1 |
| Sal 24 – Per 26 | MediaPipe'ı veri kümelerinde çalıştır, 8 açıyı iki sistemden hesapla, kareleri eşleştir | 1.3–1.5 |
| Çar 25 – Per 26 | Uygulama değişiklikleri (oturum kaydı, döndürme düzeltmesi, hedef ayarı) ve testi | 3.3 ön koşulu |
| Per 26 – Cum 27 | Sistemi kesilen videolarda çalıştır; tekrar sayısı ve eklem uyumunu karşılaştır | 2.3–2.4 |

## Hafta 2 — 30 Kasım – 4 Aralık: Madde 1 ve 2 sonuçları, gönüllü hazırlığı

| Gün | İş | Madde |
|---|---|---|
| Pzt 30 – Sal 1 | Şablonun kendi kendine testi (bir tekrarı ayırıp kalanlardan şablon kurma) | 2.5 |
| Pzt 30 – Çar 2 | MediaPipe–mocap karşılaştırması, sonuç tabloları | 1.6 |
| Çar 2 – Per 3 | Gönüllü kayıt düzenini hazırla: sıra listeleri, kamera yeri, uygulama hedefi | 3.2 |
| Per 3 | Isınma tekrarı dahil bir deneme oturumu yap; ilk tekrarın kaybını kontrol et | 3.2 |
| Per 3 – Cum 4 | Madde 1 ve Madde 2 sonuçlarını teze yazmaya başla | 1.7, 2.6 |

## Hafta 3 — 7–11 Aralık: Gönüllü kayıtları ve etiketleme

| Gün | İş | Madde |
|---|---|---|
| Pzt 7 – Sal 8 | Gönüllü kayıtları (2 kişi × 6 hareket × 15 tekrar = 180 tekrar; gönüllü başına ~1 saat) | 3.2, 3.3 |
| Çar 9 – Per 10 | Etiket kontrolü: araştırmacı videoları sistem sonucunu görmeden izler, planlanan türle uymayan tekrarları düzeltir | 3.4 |
| Pzt 7 – Per 10 (paralel) | Madde 1 ve Madde 2 yazımını bitir | 1.7, 2.6 |
| Cum 11 | Sistem kararları ile etiketlerin karşılaştırılmasına başla | 3.5 |

## Hafta 4 — 14–18 Aralık: Analiz ve yazım

| Gün | İş | Madde |
|---|---|---|
| Pzt 14 – Sal 15 | Karşılaştırmayı tamamla: sayım hatası, duyarlılık, özgüllük, hata türü uyumu | 3.5 |
| Çar 16 – Per 17 | Madde 3 sonuçlarını teze yaz | 3.6 |
| Cum 18 | Son kontrol: üç maddenin tabloları, sınırlılıklar, kaynakça | — |

## Riskler

- **Uygulama değişiklikleri:** İlk hafta bitmezse deneme oturumu (3 Aralık) ve gönüllü kayıtları (7–8 Aralık) kayar.
- **Gönüllüler:** 7–8 Aralık'a gelemezlerse Madde 3 sıkışır; yedek tarih olarak 9 Aralık tutulmalı.
- **Veri kümesi erişimi:** Erişim izin gerektirirse Madde 1 yalnızca serbest erişilebilen veri kümesiyle yürütülür.
- **İlk tekrar kaybı:** Her oturumun başındaki ısınma tekrarı bunu karşılıyor; 3 Aralık'taki deneme oturumunda doğrulanmalı.
- **2 tekrarlı referanslar:** Köprü, düz bacak kaldırma (1. bacak), köpek pozuna geçiş ve kuş-köpeğin her tarafında şablon az tekrardan kuruluyor; Madde 2 sonuçlarında ayrıca belirtilmeli.
