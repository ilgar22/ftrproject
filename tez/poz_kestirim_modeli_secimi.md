# Poz Kestirim Modelinin Seçimi — Tez Notu

> **Tezde mutlaka yer alacak.** Önerilen yer: Yöntem bölümü, "Poz kestirimi" alt başlığı (gerekçe paragrafı) ve Literatür bölümü, "Poz kestirim modelleri" alt başlığı (karşılaştırma).
> Not tarihi: 20.11.2026. Kaynak taraması bu tarihte yapılmıştır; tez tesliminden önce güncel sürümler yeniden kontrol edilmelidir.

---

## 1. Tez metni taslağı

### Poz kestirim modelinin seçimi

Önerilen sistemin hem fizyoterapistin referans kaydı hem de hastanın egzersiz oturumu için akıllı telefon üzerinde çalışması hedeflendiğinden, poz kestirim modelinin seçiminde beş ölçüt gözetilmiştir: (i) cihaz üzerinde gerçek zamanlı çalışma, (ii) Android ve iOS platformlarında hazır destek, (iii) üç boyutlu (3B) çıktı, (iv) rehabilitasyon veya klinik bağlamda doğrulanmış olma ve (v) etkin olarak sürdürülme. Üçüncü ölçüt, önerilen yöntemin eklem açılarını 3B dünya koordinatlarından hesaplamasından kaynaklanmaktadır.

Rode ve ark. (2025), optik hareket yakalama referansıyla 11 açık kaynaklı monoküler poz kestirim modelini karşılaştırmıştır. Doğrudan 3B kestirim yapan modeller arasında en düşük 3B konum hatasını MediaPipe BlazePose'un ağır (heavy) sürümünün dünya koordinatı çıktısı vermiştir (146 mm; tespit oranı %98,8). Aynı çalışmada doğrudan 2B kestirimde en düşük hatayı RTMPose vermiş (72 mm); BlazePose için derinlik hatası ise yüksek bulunmuştur (108 mm). UCO fiziksel rehabilitasyon veri kümesinde MediaPipe, ayakta yapılan egzersizlerde 3B kestirimde en iyi sonucu ve en düşük 3B eklem açısı hatasını (11,96° ± 9,99°) vermiştir (Aguilar-Ortega ve ark., 2023). Klinik ve rehabilitasyon biyomekaniğine yönelik güncel bir kapsam derlemesinde MediaPipe/BlazePose, 2B monoküler yöntemler içinde OpenPose ailesinden sonra en sık doğrulanan ikinci model ailesidir (Delaplace ve ark., 2026).

2B doğrulukta RTMPose'un MediaPipe'tan daha iyi olduğu farklı çalışmalarda gösterilmiştir (Rode ve ark., 2025; Gomez ve ark., 2025). Bununla birlikte RTMPose'un telefonda gerçek zamanlı çalışabilen sürümleri yalnızca 2B çıktı vermekte; 3B sürümü RTMW3D ise yaklaşık 65–98 milyon parametresiyle telefonda gerçek zamanlı kullanım için ağır kalmaktadır (Jiang ve ark., 2024). MoveNet en hızlı model olmakla birlikte doğrulukta daha karmaşık modellerin gerisinde kalmakta ve yalnızca 2B çıktı vermektedir. YOLO26-pose güncel ve hızlı bir 2B modeldir; ancak rehabilitasyon bağlamında eklem açısı doğrulaması bulunmamaktadır. Apple Vision 3B vücut pozu yalnızca Apple platformlarında kullanılabilmektedir. 2B iskeletten 3B'ye geçiş (lifting) yapan MotionAGFormer gibi modeller daha düşük açı hatası bildirmekle birlikte (Medrano-Paredes ve ark., 2025), zamansal pencere gerektirdikleri için gerçek zamanlı olmayan işler için önerilmektedir (Rode ve ark., 2025) ve canlı geri bildirime uygun değildir.

Bu nedenlerle çalışmada, Android ve iOS'ta cihaz üzerinde gerçek zamanlı çalışan ve doğrudan 3B çıktı veren modeller arasında 3B hatası en düşük bildirilen ve rehabilitasyon bağlamında en kapsamlı doğrulanan model olan MediaPipe Pose Landmarker (BlazePose GHUM) kullanılmıştır. Cihazın kapasitesine göre ağır (heavy) sürüm, yetmediği durumda tam (full) sürüm kullanılmaktadır. Tek kameralı kestirimden kaynaklanan derinlik hatası ve fizyoterapi verisinde bildirilen yaklaşık 12°'lik ortalama 3B açı hatası (Leuthold ve ark., 2025) sistemin sınırlılıkları arasında ele alınmıştır.

---

## 2. Karşılaştırma tablosu (Literatür bölümü için)

| Model | Telefonda gerçek zamanlı | 3B çıktı | Platform | Rehabilitasyonda doğrulama | Kaynak |
|---|---|---|---|---|---|
| MediaPipe Pose (BlazePose GHUM) | Evet | Evet (dünya koordinatı) | Android, iOS, Web | Geniş | Rode 2025; Aguilar-Ortega 2023; Delaplace 2026 |
| RTMPose | Evet (kendi entegrasyonuyla) | Hayır (RTMW3D telefon için ağır) | Hazır mobil SDK yok | Sınırlı, 2B'de güçlü | Rode 2025; Gomez 2025; Jiang 2023, 2024 |
| MoveNet | Evet (en hızlı) | Hayır | Android, iOS, Web | Sınırlı | Batić 2025; Çoklu kişi kıyas çalışması 2025 |
| YOLO26-pose | Evet | Hayır | Dışa aktarımla (CoreML, TFLite) | Açı doğrulaması yok | Jocher 2026; Diamant 2025 |
| Apple Vision 3B | Evet | Evet | Yalnızca iOS | Bulunamadı | Apple Developer belgeleri |
| MotionAGFormer (lifting) | Hayır | Evet | — | Var, 3B açıda en iyilerden | Medrano-Paredes 2025; Rode 2025 |

Temel sayısal bulgular:
- Rode ve ark. (2025): doğrudan 3B'de en iyi BlazePose World Heavy (146 mm, %98,8 tespit, 147 kare/s; derinlik hatası 108 mm). Doğrudan 2B'de en iyi RTMPose (72 mm). Testler masaüstü GPU'da yapılmış; telefon testi yok.
- Aguilar-Ortega ve ark. (2023, UCO): 3B eklem açısında en iyi MediaPipe, 11,96° ± 9,99°.
- Gomez ve ark. (2025): uzman işaretlemesine karşı ortalama açı hatası RTMPose 5,62°, MoveNet 6,14°, MediaPipe 6,33°. Son işlemeden sonra üç model benzer düzeye geliyor.
- Leuthold ve ark. (2025): fizyoterapi egzersizlerinde (Vicon referanslı) BlazePose 3B ortalama açı hatası 12,3° (std 6,6°).
- Medrano-Paredes ve ark. (2025): IMU referanslı günlük yaşam aktivitelerinde MotionAGFormer RMSE 9,27°.
- Jiang ve ark. (2023): RTMPose Snapdragon 865 üzerinde ncnn ile telefonda çalıştırılmış.
- MediaPipe v0.10.35 (Nisan 2026): Android NPU hızlandırması; proje etkin olarak sürdürülüyor.

---

## 3. Tezde dikkat edilecekler

- **"En iyi poz kestirim modeli" denmemeli.** 2B doğrulukta RTMPose önde. Savunulabilir ifade: "Android ve iOS'ta cihaz üzerinde gerçek zamanlı çalışan ve doğrudan 3B çıktı veren modeller arasında 3B hatası en düşük bildirilen ve rehabilitasyonda en kapsamlı doğrulanan model."
- **Telefon iddiası Rode ve ark.'na dayandırılmamalı.** O çalışmanın tüm ölçümleri masaüstü GPU'da (RTX 4080) yapılmış.
- **Bildirideki [19] numaralı kaynak (Sensors 2026, 26(18), 5890):** Üç model de (MediaPipe, OpenPose, HRNet) yüksek güvenilirlik göstermiş (ICC ≥ 0,90). Ancak genel başarı oranı en düşük olan MediaPipe. "MediaPipe daha güvenilir" ifadesi bu kaynakla tam örtüşmüyor; tezde düzeltilmeli.
- **Uygulama notu:** MediaPipe telefonda yerel Android (Kotlin/Java) ve iOS (Swift) kütüphaneleriyle çalışır. Mevcut Kivy/Python prototipinin telefona taşınması ayrı bir uygulama işi olarak Sistem bölümünde anlatılmalı.

---

## 4. Kaynakça (APA)

> [D] işaretli künyelerde yazar adları veya yayın bilgileri bu taramada tam doğrulanamadı; yayın sayfasından tamamlanmalı.

- Aguilar-Ortega, R., ve ark. (2023). UCO Physical Rehabilitation: New dataset and study of human pose estimation methods on physical rehabilitation exercises. *Sensors, 23*(21), 8862. https://doi.org/10.3390/s23218862 [D: yazar listesi]
- Apple Inc. (t.y.). *VNDetectHumanBodyPose3DRequest*. Apple Developer Documentation. https://developer.apple.com/documentation/vision/vndetecthumanbodypose3drequest
- Batić, D., Kachavarapu, S., Nait Irahal, F., Meyer, D., & Meyer, C. (2025). Towards AI-based at-home physiotherapy for the elderly: Comparing MoveNet with ViTPose in human pose estimation. *ISBS Proceedings Archive, 43*(1), 9. https://commons.nmu.edu/isbs/vol43/iss1/9
- Bazarevsky, V., Grishchenko, I., Raveendran, K., Zhu, T., Zhang, F., & Grundmann, M. (2020). BlazePose: On-device real-time body pose tracking. *arXiv:2006.10204*.
- Delaplace, F., Piche, E., Chorin, F., & Zory, R. (2026). Video-based markerless motion capture for clinical and rehabilitation biomechanics: A PRISMA-ScR scoping review of validated architectures, clinical readiness, and emerging methods. *arXiv:2609.18667*.
- Diamant, A. (2025). AI pose analysis and kinematic profiling of range-of-motion variations in resistance training. *arXiv:2510.20012*.
- Gomez, [?], Garrido-Lopez, [?], Fierrez, J., Morales, A., Tolosana, R., Rueda, [?], & Navarro, [?] (2025). Comparison of visual trackers for biomechanical analysis of running. *arXiv:2505.04713*. [D: ad baş harfleri]
- Google AI Edge. (2026). *MediaPipe v0.10.35* [Yazılım sürümü]. GitHub. https://github.com/google-ai-edge/mediapipe
- Jiang, T., Lu, P., Zhang, L., Ma, N., Han, R., Lyu, C., Li, Y., & Chen, K. (2023). RTMPose: Real-time multi-person pose estimation based on MMPose. *arXiv:2303.07399*.
- Jiang, T., Xie, X., & Li, Y. (2024). RTMW: Real-time multi-person 2D and 3D whole-body pose estimation. *arXiv:2407.08634*.
- Jocher, G., Qiu, J., Liu, M., Lyu, S., Akyon, F. C., & Kalfaoglu, M. E. (2026). Ultralytics YOLO26: Unified real-time end-to-end vision models. *arXiv:2606.03748*.
- Leuthold, T., Xiloyannis, M., & Zimmermann, Y. (2025). Physics informed human posture estimation based on 3D landmarks from monocular RGB-videos. *arXiv:2512.06783*.
- Medrano-Paredes, M., Fernández-González, C., Díaz-Pernas, F.-J., Saoudi, H., González-Alonso, J., & Martínez-Zarzuela, M. (2025). Paving the way towards kinematic assessment using monocular video: A preclinical benchmark of state-of-the-art deep-learning-based 3D human pose estimators against inertial sensors in daily living activities. *arXiv:2510.02264*. [D: Artificial Intelligence Review'da yayımlandığı bildiriliyor; dergi künyesi kontrol edilmeli]
- Multi-person 2D human pose estimation: A benchmark for real-time applications. (2025). *Research Square* (ön baskı). [D: yazarlar]
- Qualcomm. (t.y.). *RTMPose-Body2d: Optimized for mobile deployment*. Qualcomm AI Hub. https://huggingface.co/qualcomm/RTMPose-Body2d
- Reliability and validity of AI-based pose estimation algorithms for assessing lower-limb flexibility and joint range of motion. (2026). *Sensors, 26*(18), 5890. https://doi.org/10.3390/s26185890 [D: yazarlar]
- Rode, D., Dunkel, A., Willi, R., Wolf, P., Xiloyannis, M., & Riener, R. (2025). Assessment of monocular human pose estimation models for clinical movement analysis. *Scientific Reports, 15*. https://doi.org/10.1038/s41598-025-22626-7
