# Madde 2.3–2.4 — Sistemin fizyoterapist videolarındaki sonuçları

**Yöntem:** 8 kesilmiş video (`tez/fizyoterapist_video/kesilmis/`) `PoseEngine.extract_reference_from_video` ile (döndürmesiz, heavy model, VIDEO modu) işlendi; şablon `phase_aligner.build_template` ile kuruldu. Ham çıktılar: `tez/madde2_ciktilar/<video>.json`. Betik: `tez/madde2_calistir.py`.

- **Gerçek tekrar:** `yapilacaklar.md` tablosu (video kareleriyle doğrulandı).
- **Gerçek hareketli eklemler:** `eklem_tanimlari.md` (İş 5).
- **Sistemin hareketli eklemleri:** `lead_joints` (10.–90. yüzdelik aralığı ≥ 15°). Parantez içinde açı değişimi.
- **Sistemin sabit eklemleri:** `stable_profile`.

| Video | Gerçek tekrar | Sistemin tekrarı | Gerçek hareketli eklemler | Sistemin hareketli eklemleri | Sistemin sabit eklemleri | Uyuyor mu? |
|---|---|---|---|---|---|---|
| 01_kopru | 2 | 2 | Sol kalça, sağ kalça | sol_kalca (32°), sol_diz (22°) | sol_dirsek, sol_omuz | Tekrar: **Evet**. Eklem: **Kısmen** — kalça doğru; diz hareketli bulundu (tabloda sabit); sağ taraf görünmüyor. |
| 02a_duz_bacak_1 | 2 | 2 | Kalkan bacağın kalçası | sol_diz (77°), sol_kalca (45°), sag_diz (77°), sag_kalca (17°) | sol_dirsek, sol_omuz | Tekrar: **Evet**. Eklem: **Hayır** — kalça doğru, ama iki diz de hareketli bulundu (kalkan diz düz kalmalı). |
| 02b_duz_bacak_2 | 3 | 3 | Kalkan bacağın kalçası (diğer bacak) | sol_diz (87°), sag_diz (85°), sol_kalca (47°) | sol_dirsek, sol_omuz | Tekrar: **Evet**. Eklem: **Hayır** — dizler hareketli bulundu; kalkan bacak 2a ile aynı (sol) bulundu. |
| 03_kopek_gecis | 2 | 2 | Omuzlar, dizler, kalçalar | sag_diz (93°), sag_omuz (40°) | sag_dirsek, sag_kalca | Tekrar: **Evet**. Eklem: **Kısmen** — sağ diz/omuz ve sabit dirsek doğru; kalça yalnızca 10° değişti; sol taraf görünmüyor. |
| 04_yan_bacak | 4 | **1** | Üstteki bacağın kalçası | sag_kalca (34°), sag_dirsek (20°) | sol_omuz, sag_omuz, sol_kalca, sag_diz | Tekrar: **Hayır**. Eklem: **Kısmen** — kalça ve sabit eklemler doğru; dirsek fazladan hareketli bulundu. |
| 05a_kus_kopek_1 | 2 | 2 | Kalkan kolun omzu, kalkan bacağın kalçası ve dizi | sag_kalca (83°), sag_diz (78°), sol_omuz (60°), sol_diz (15°) | sol_dirsek, sag_dirsek, sag_omuz, sol_kalca | Tekrar: **Evet**. Eklem: **Kısmen** — sağ bacak + sol kol doğru; destek dizi (sol_diz) eşikte (15°). |
| 05b_kus_kopek_2 | 2 | 2 | Kalkan kolun omzu, kalkan bacağın kalçası ve dizi | sol_diz (64°), sol_kalca (58°), sag_omuz (49°), sag_kalca (18°), sag_dirsek (18°), sag_diz (16°) | sol_dirsek, sol_omuz | Tekrar: **Evet**. Eklem: **Kısmen** — sol bacak + sağ kol doğru; destek tarafı eklemleri eşiğin hemen üstünde (16–18°). |
| 06_olu_bocek | 5 | **1** | Omuzlar, kalçalar, dizler | sol_kalca (73°), sol_omuz (70°), sol_diz (68°), sag_diz (115°), sag_kalca (80°) | sol_dirsek | Tekrar: **Hayır**. Eklem: **Kısmen** — sağ omuz ve sağ dirsek bulunamadı; diğerleri doğru. |

## Özet

- **Tekrar sayısı:** 8 videonun 6'sında doğru (75%). Hatalı olanlar: yan yatarak bacak kaldırma (1/4) ve ölü böcek (1/5).
- **Eklem seçimi:** Hiçbir videoda tam uyum yok; 6 videoda kısmi, 2 videoda (düz bacak kaldırma) uyumsuz.
- **Kolay hareketler** (köprü, düz bacak kaldırma): tekrar sayısı 3/3 doğru; eklem seçimi sorunlu.
- **Orta/zor hareketler** (köpek pozu, yan bacak, kuş-köpek, ölü böcek): tekrar sayısı 3/5 doğru; bozulan adım **tekrar ayırma** (yan bacak, ölü böcek).

## Hataların olası nedenleri (2.6 için not)

1. **Yan yatarak bacak kaldırma (1/4):** Bacak tekrarlar arasında yere inmiyor. Tekrar ayırma, ilerleme sinyalinin dinlenme düzeyine (< 0,25) inmesini bekliyor; bacak havada beklediği için sinyal bu düzeye inmiyor ve 4 tekrar tek tekrar olarak görülüyor. (`yapilacaklar.md` notuyla uyumlu.)
2. **Ölü böcek (1/5):** Taraflar sırayla çalışıyor. İlerleme sinyali tüm lider eklemlerin ortalaması; bir tarafın kalça/dizi açılırken diğer tarafınki kapanıyor, ortalama sinyal birbirini götürüyor ve tekrarlar ayrılamıyor. Taraflara göre ayrı sinyal ya da tarafa göre ayrı referans gerekebilir.
3. **Uzak taraf görünmüyor (köprü, köpek pozu, ölü böcek):** Yandan çekimde kameradan uzak taraftaki eklemlerin görünürlüğü düşük (< 0,35) ya da karelerin %80'inden azında bulunuyor; bu eklemler ne hareketli ne sabit olarak sınıflandırılıyor.
4. **Düz bacak kaldırmada dizler:** Yandan görünümde iki bacak üst üste geliyor; MediaPipe sağ/sol bacağı karıştırabiliyor. Kalkan dizin 77–87° "bükülmesi" fiziksel olarak yok (videoda diz düz); 2a ve 2b'de kalkan bacağın aynı (sol) bulunması da bu karışmayı destekliyor. **Videoda hangi bacağın kalktığı gözle kontrol edilmeli.**
5. **Eşik etkisi (kuş-köpek):** Destek tarafındaki eklemler 15–18° değişiyor; 15° eşiğinin hemen üstünde kaldıkları için hareketli sayılıyor.
6. **Köprüde diz:** Kalça kalkarken uyluğun açısı değiştiği için diz açısı da ~20° değişiyor. Bu bir sistem hatası değil; `eklem_tanimlari.md` tablosunda köprü için dizin "sabit" yazılması gözden geçirilmeli.
