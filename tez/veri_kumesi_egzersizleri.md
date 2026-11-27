# Veri kümelerindeki benzer egzersizler (Madde 1.2)

Benzerlik ölçütü: aynı eklemler hareket ediyor mu?

Kaynaklar:
- REHAB24-6: https://zenodo.org/records/13305826 (6 egzersiz, Ex1–Ex6)
- UCO Physical Rehabilitation: https://github.com/AVAuco/ucophyrehab (16 egzersiz, sol/sağ taraf)

Benzerlik: **Tam** = aynı eklem ve aynı pozisyon; **Kısmi** = aynı eklem, farklı pozisyon veya hareketin sadece bir kısmı.

| Bizim hareket | Veri kümesi | Veri kümesindeki egzersiz adı | Hareket eden eklemler | Benzerlik |
|---|---|---|---|---|
| 1. Köprü | REHAB24-6 | Ex6 – Squats | Kalça (ekstansiyon), diz | Kısmi (ayakta; köprüde sırtüstü) |
| 1. Köprü | UCO | 04 / 08 – Bending the knee with bed support (sol/sağ) | Kalça, diz (sırtüstü) | Kısmi (aynı pozisyon, kalça kaldırma yok) |
| 2. Sırtüstü düz bacak kaldırma | UCO | 03 / 07 – Lift the extended leg (sol/sağ) | Kalça (fleksiyon), diz düz | **Tam** |
| 3. Dört ayaktan köpek pozuna geçiş | REHAB24-6 | Ex3 – Push-ups (ayakta, eller masada) | Omuz, dirsek, gövde | Zayıf (ayakta yapılıyor; sadece kol hareketi benzer) |
| 3. Dört ayaktan köpek pozuna geçiş | REHAB24-6 | Ex2 – Arm VW | Omuz (fleksiyon), dirsek | Kısmi (sadece üst vücut) |
| 4. Yan yatarak bacak kaldırma | REHAB24-6 | Ex4 – Leg abduction | Kalça (abdüksiyon), diz düz | Kısmi (aynı eklem hareketi, farklı pozisyon) |
| 5. Kuş-köpek | UCO | 09 / 13 – Shoulder flexion (sol/sağ) | Omuz (fleksiyon), dirsek düz | Kısmi (kol kısmı, oturarak) |
| 5. Kuş-köpek | REHAB24-6 | Ex4 – Leg abduction | Kalça | Kısmi (bacak kısmı; kuş-köpekte kalça ekstansiyonu) |
| 6. Ölü böcek | UCO | 03 / 07 – Lift the extended leg | Kalça (fleksiyon), diz (sırtüstü) | Kısmi (bacak kısmı) |
| 6. Ölü böcek | UCO | 09 / 13 – Shoulder flexion | Omuz (fleksiyon) | Kısmi (kol kısmı, oturarak) |
| 3a. Üç bacaklı köpek pozu (tek bacak kaldırmalı aşağı bakan köpek) | REHAB24-6 | Ex3 – Push-ups (ayakta, eller masada) | Omuz, dirsek (sadece üst vücut) | Zayıf (pozisyon farklı: ayakta; sadece kol hareketi benzer) |
| 3a. Üç bacaklı köpek pozu | — | Karşılığı yok (REHAB24-6 ve UCO'da kalça ekstansiyonu + aşağı bakan köpek pozisyonu yok) | Omuz (fleksiyon), kalça (ekstansiyon), diz düz | Yok – fizyoterapist kayıtlarından alınacak |
| Oturarak bacak kaldırma (ek) | UCO | 01 / 05 – Bending the knee without support while sitting (sol/sağ) | Diz (ekstansiyon), kalça | Bizim 6 hareketimizde yok; oturarak yapılıyor |

## Ek veri kümesi: Physio2.2M (erişim talep edildi)

Physio2.2M (Rode ve ark., Scientific Reports, 2025): 25 katılımcı, senkron RGB video + Vicon hareket yakalama (46 marker). Yedi egzersiz: squat, köprü, kuş (bird), abdüksiyon, omuz, diz, germe. Açık erişimli değil; yazarlardan e-posta ile erişim talep edildi, cevap bekleniyor.

| Bizim hareket | Veri kümesi | Veri kümesindeki egzersiz adı | Hareket eden eklemler | Benzerlik |
|---|---|---|---|---|
| 1. Köprü | Physio2.2M | Bridge | Kalça (ekstansiyon), diz | **Tam** (beklenen) |
| 4. Yan yatarak bacak kaldırma | Physio2.2M | Abduction | Kalça (abdüksiyon) | Tam veya kısmi (pozisyon kontrol edilecek) |
| 5. Kuş-köpek | Physio2.2M | Bird | Omuz (fleksiyon), kalça (ekstansiyon) | **Tam** (beklenen) |

## Notlar
- Tam eşleşme sadece bir hareket için var: sırtüstü düz bacak kaldırma ↔ UCO 03/07.
- REHAB24-6 sayfasında Ex4 (Leg abduction) için pozisyon yazmıyor; videolardan kontrol edilmeli.
- Köprü, dört ayak → köpek pozu ve kuş-köpek için birebir karşılık yok; eklem bazında kısmi karşılaştırma yapılabilir.
- REHAB24-6'da eklem isimleri dosyasının adı `joints_names.txt` (görev listesinde `joint_names.txt` yazıyor).
- UCO veri kümesi GitHub'da doğrudan indirilmiyor: inforeha@uco.es adresine ad, kurum ve araştırma amacıyla e-posta gönderilmeli. Ek kaynak: https://zenodo.org/records/17935737
