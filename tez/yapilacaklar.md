# Tez — Yapılacaklar Listesi

## 1. MediaPipe'ın doğruluğunu belirlemek

**Amaç:** Kullandığımız poz kestirim modelinin (MediaPipe Pose Landmarker, heavy) eklem açılarını ne kadar doğru ölçtüğünü belirlemek ve sonucu teze yazmak.

**Model seçimi (tamamlandı):** Neden MediaPipe'ı seçtiğimiz literatür taramasıyla gerekçelendirildi. Bkz. `poz_kestirim_modeli_secimi.md`.

**Doğruluk testi (yapılacak):** Hareket yakalama (mocap) referanslı açık veri kümeleriyle karşılaştırma.

- [ ] **1.1 Veriyi indir.**
  - REHAB24-6: https://zenodo.org/records/13305826
  - UCO Physical Rehabilitation: https://github.com/AVAuco/ucophyrehab
- [ ] **1.2 Egzersizleri seç.** Veri kümelerinden bizim altı egzersizimize benzeyenleri ayır.
- [ ] **1.3 MediaPipe'ı çalıştır.** Seçilen videoları kendi sistemimizdeki ayarlarla (heavy model) MediaPipe'tan geçir, her karedeki eklem noktalarını kaydet.
- [ ] **1.4 Açıları hesapla.** Aynı 8 eklem açısını (sağ/sol dirsek, omuz, kalça, diz) hem MediaPipe noktalarından hem mocap noktalarından hesapla. İki sistemin eklem tanımlarını önce eşleştir.
- [ ] **1.5 Kareleri eşleştir.** Videodaki her kareyi mocap'taki aynı ana denk getir.
- [ ] **1.6 Karşılaştır.** Her açı için MediaPipe ile mocap arasındaki farkı derece olarak hesapla. MediaPipe'ın kişiyi bulduğu kare oranına bak. Sonuçları egzersize ve kamera açısına göre ayrı raporla.
- [ ] **1.7 Teze yaz.**
  - Sonuçları tabloyla ver.
  - Literatürle karşılaştır: UCO çalışmasında MediaPipe'ın 3B açı hatası 11,96° ± 9,99° (Aguilar-Ortega ve ark., 2023).
  - Sınırlılıklara ekle: "Bu test laboratuvar koşullarında yapılmıştır; ev koşullarındaki başarım uçtan uca değerlendirmeyle gösterilmiştir."

## 2. Sistemin fizyoterapistin hareketini doğru algıladığını göstermek

**Amaç:** Gerçek fizyoterapistin referans videolarından sistemin tekrarları doğru ayırdığını, hareketli ve sabit eklemleri doğru belirlediğini ve tutarlı bir şablon kurduğunu göstermek.

**Referans kaynağı (karar verildi):** Fizyoterapistten yeni kayıt istenmez. Referanslar, fizyoterapistin gönderdiği iki videodan (`tez/fizyoterapist_video/fizyoterapist_1.mp4` ve `fizyoterapist_2.mp4`) kesilerek elde edilir.

### Kullanılacak hareketler

Videolardaki 12 hareketten bu çalışmaya uygun 6'sı. Zamanlar video başından itibaren saniye cinsindendir. Tekrar zamanları sistemin açı izinden çıkarılıp video kareleriyle kontrol edilmiştir.

| # | Hareket | Zorluk | Video | Kesilecek bölüm (sn) | Tekrar | Tekrarların zamanı (sn) | Not |
|---|---|---|---|---|---|---|---|
| 1 | Köprü | Kolay | 2 | 87,0 – 103,0 | 2 | 89,7–95,4 · 97,6–102,2 | Her tekrarda üstte 2–3 sn bekleme var |
| 2a | Sırtüstü düz bacak kaldırma — 1. bacak | Kolay | 2 | 109,0 – 117,0 | 2 | 110,9–113,0 · 114,7–116,3 | |
| 2b | Sırtüstü düz bacak kaldırma — 2. bacak | Kolay | 2 | 127,0 – 138,0 | 3 | 129,1–131,0 · 132,3–134,4 · 135,6–137,6 | |
| 3 | Dört ayaktan köpek pozuna geçiş | Orta | 1 | 19,5 – 33,5 | 2 | 21,2–24,5 · 27,6–30,0 | |
| 4 | Yan yatarak bacak kaldırma | Orta | 2 | 153,0 – 164,5 | 4 | 155,1–156,9 · 157,6–159,2 · 159,9–161,5 · 162,3–163,9 | Bacak tekrarlar arasında yere inmiyor, havada bekliyor; yalnızca tek taraf var |
| 5 | Kuş-köpek | Zor | 2 | 5,0 – 16,5 | 4 (2 + 2) | 1. taraf: 7,3–8,7 · 9,5–10,9 — 2. taraf: 11,6–12,8 · 13,7–14,9 | Sağ/sol sırayla; her taraf ayrı referans olarak ele alınır |
| 6 | Ölü böcek | Zor | 2 | 68,0 – 81,5 | 5 | ≈71,3–72,8 · ≈73,3–74,8 · 75,3–76,7 · 77,1–78,6 · 79,0–80,5 | Sağ/sol sırayla (1-3-5 bir taraf, 2-4 diğer taraf; kontrol edilmeli). İlk iki tekrar açı izinde zayıf, zamanları gözle (±0,5 sn) |

**Kapsam dışı bırakılan hareketler ve nedeni**
- Kedi-deve, gövde döndürme: hareket omurgada; MediaPipe'ta omurga noktası yok (bkz. `notlar.md`).
- Köpek pozunda bekleme, yüzüstü kol kaldırma/bekleme: tekrar yok, statik bekleme.
- Yan yatarak istiridye: hareket kameraya doğru (derinlik yönünde), tek kamerayla izlenemiyor.
- Köpek pozunda bacak kaldırma: sağ/sol sırayla ve her tarafta yalnızca 2 tekrar; ölü böcek zor hareket olarak zaten temsil ediliyor.

**Protokolden sapma (teze yazılacak):** Referanslar "başla → bekle → 3 tekrar → bekle → bitir" protokolüyle değil, kesintisiz bir egzersiz akışından kesilerek alındı. Tekrar sayısı hareketlere göre 2–5 arasında değişiyor ve tekrar sayıları video karelerinden gözle doğrulandı.

**Yeni kayıt gerekirse kullanılacak protokol:** "başla" → 1–2 sn başlangıç duruşunda bekleme → 3 tekrar → 1–2 sn bekleme → "bitir". (Başlangıçtaki bekleme gerekli: sistem başlangıç duruşunu ilk karelerden öğreniyor. En az 2–3 tekrar gerekli: tolerans tekrarlar arasındaki farktan öğreniliyor; tek tekrarda sabit 10° kullanılır.)

- [ ] **2.1 Videoları kes.** Yukarıdaki tablodaki her hareketi "Kesilecek bölüm" aralığından ayrı bir video dosyası olarak kes. Kuş-köpek ve ölü böcekte her tarafın tekrarları ayrı referans olarak ele alınır.
- [ ] **2.2 Egzersiz tanımı (araştırmacılar).** Her egzersiz için hangi eklemin hareket ettiğini, hangisinin sabit kalması gerektiğini egzersizin tanımından yazılı olarak belirle. Fizyoterapistten iş istenmez.
- [ ] **2.3 Sistemi çalıştır.** Sistemin bulduğu tekrar sayısını ve hareketli/sabit eklemleri kaydet.
- [ ] **2.4 Karşılaştır.**
  - Tekrar sayısı: sistemin bulduğu sayı tablodaki sayıyla aynı olmalı.
  - Eklemler: sistemin seçtikleri 2.2'deki tanımla uyuşuyor mu?
- [ ] **2.5 Şablonu kendi kendine test et.** Bir tekrarı ayır, şablonu kalan tekrarlardan kur, ayrılan tekrar doğru sayılıyor mu bak. Her tekrar için sırayla yap.
  - Dikkat: 2 tekrarlı hareketlerde (köprü, düz bacak kaldırma 1. bacak, köpek pozuna geçiş, kuş-köpeğin her tarafı) şablon tek tekrardan kurulur ve sistem sabit 10° tolerans kullanır. Bu hareketlerde test, öğrenilen tolerans yerine sabit toleransı sınar; sonuçlarda ayrıca belirtilmeli.
- [ ] **2.6 Teze yaz.** Sonuçları kolay ve zor hareketler için ayrı tablolarla ver; zor hareketlerde hangi adımın bozulduğunu (tekrar ayırma, eklem seçimi, şablon) belirt.

## 3. Sistemin hastanın hareketi doğru yapıp yapmadığını doğru tespit ettiğini göstermek

**Amaç:** Sistemin her tekrar için verdiği "doğru / yanlış" kararının, tekrarın gerçekte doğru mu hatalı mı yapıldığıyla ne kadar uyuştuğunu göstermek. Tezin asıl sonucu bu maddeden çıkacak.

**Fizyoterapistten bu maddede hiçbir iş istenmez.** Hataları, gösterimi ve etiketlemeyi araştırmacılar yapar.

- [ ] **3.1 Hataları tanımla (araştırmacılar).** Her egzersiz için **2 hata** belirlenir:
  - Hata A: hareketin eksik açıklıkla yapılması (tüm egzersizlerde ortak).
  - Hata B: egzersize özgü bir form hatası (ör. sabit kalması gereken eklemin hareket etmesi, gövde kompansasyonu).
- [ ] **3.2 Gönüllüleri kaydet.** 2 gönüllü × 6 egzersiz × 15 tekrar = 180 tekrar. Her egzersizde 15 tekrar: **5 doğru + 5 hata A + 5 hata B.** Referans olarak 2. maddedeki fizyoterapist kaydından kurulan şablon kullanılır.

  **15 tekrarın yapılış protokolü**
  1. *Hazırlık (kayıttan önce):* Araştırmacı, fizyoterapistin referans videosunu göstererek her egzersizin doğru hâlini ve iki hatasını gönüllüye anlatır; gönüllü her birini bir kez dener. Hata açık ama doğal yapılmalı, abartılmamalı.
  2. *Sıra listesi:* Her gönüllü ve her egzersiz için 15 tekrarın sırası önceden karışık olarak belirlenir (ör. D, A, D, B, B, D, A, ...) ve kâğıda yazılır. Aynı türden en fazla 2 tekrar art arda gelir. Bloklar hâlinde (önce 5 doğru, sonra 5 A ...) yapılmaz; sıra etkisi ve sistemin bir duruma takılması sonuçları bozar.
  3. *Kamera:* Fizyoterapistin referans kaydındaki görünüm (önden/yandan), aynı telefon, tüm vücut kadrajda, yaklaşık 2 m mesafe.
  4. *Uygulama ayarı:* Günlük hedef 15'ten büyük girilir (ör. 30); aksi hâlde uygulama hedefe ulaşınca oturumu kendisi kapatır.
  5. *Isınma tekrarı:* Oturum başında 1 doğru tekrar yapılır ve analize **katılmaz**. Ön deneyde ilk tekrar çoğu zaman hizalamanın oturmasına harcandığı için bu tekrar o kaybı karşılar.
  6. *Her tekrar:* Araştırmacı tekrardan önce türünü söyler ("doğru" / "A" / "B"). Gönüllü başlangıç duruşundan başlar, tekrarı fizyoterapistle benzer tempoda yapar, başlangıç duruşuna döner ve 1–2 sn bekler.
  7. *Araştırmacı notu:* Her tekrarın planlanan türü ve sırası kaydedilir. Bu not etiketlemenin (3.4) başlangıç noktasıdır.
  8. *Süre:* Bir oturum (1 ısınma + 15 tekrar) yaklaşık 1,5–2 dk. Gönüllü başına 6 oturum ve aralarda dinlenme ile yaklaşık 1 saat.

- [ ] **3.3 Sistemin kararlarını kaydet.** Uygulama oturum boyunca şunları saklamalı:
  - ham kamera videosu (ekran kaydı değil),
  - her tekrar için verdiği karar ve zamanı (sayıldı / reddedildi ve nedeni).
  Bu kayıt olmadan sistemin kararları etiketlerle tekrar tekrar eşleştirilemez.
- [ ] **3.4 Etiketle (araştırmacı).** Her tekrarın etiketi planlanan türdür (doğru / A / B). Bir araştırmacı videoları sistemin sonucunu görmeden izler ve gönüllünün tekrarı gerçekten istendiği gibi yapıp yapmadığını kontrol eder; uymayan tekrarın etiketi düzeltilir veya tekrar analizden çıkarılır.
- [ ] **3.5 Karşılaştır.**
  - Tekrar sayısı: sistemin saydığı ile doğru etiketli tekrar sayısı arasındaki fark.
  - Duyarlılık: hatalı etiketli tekrarların ne kadarını sistem reddetti?
  - Özgüllük: doğru etiketli tekrarların ne kadarını sistem kabul etti?
  - Hata türü: sistemin red nedeni etiketteki hata türüyle uyuşuyor mu?
- [ ] **3.6 Teze yaz.** Sonuçları egzersiz bazında, kolay ve zor hareketler için ayrı ver. Sistemin yakalayamadığı hata türlerini açıkça belirt. Sınırlılıklara ekle: "Hata türleri ve etiketler araştırmacılar tarafından belirlenmiş; bağımsız bir klinisyen değerlendirmesi yapılmamıştır."
