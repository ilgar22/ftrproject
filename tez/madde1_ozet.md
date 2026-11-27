# Madde 1.6 — MediaPipe açı doğruluğu (mocap karşılaştırması)

Hazır MediaPipe Pose Landmarker (heavy, VIDEO, 3B dünya açıları) mocap ile karşılaştırıldı. Model eğitilmedi. Açı tanımı sistemle aynıdır (`calculate_angle`). Kare döndürülmedi.

Bu özet `tez/madde1_ciktilar/` altındaki **51** CSV dosyasından üretildi. Bir eklem satırı, hem MediaPipe hem mocap açısı dolu olan karelerdir. UCO'da mocap yalnızca çalışan uzvun açısını verir (bacakta diz, kolda dirsek); diğer eklemlerde mocap hücresi boş olduğu için hata hesaplanmaz.

SD, mutlak hataların örneklem standart sapmasıdır (n−1).

## Sırtüstü — UCO

Egzersizler yatakta sırtüstü: 03/07 düz bacak kaldırma (sol/sağ), 04/08 diz bükme (sol/sağ). Video 25 fps.

### Tüm kareler

| Egzersiz | Kamera | Eklem | MAE (°) | SD (°) | Medyan (°) | Kare |
|---|---|---|---:|---:|---:|---:|
| 03 | cam2 | Sol dirsek | — | — | — | 0 |
| 03 | cam2 | Sağ dirsek | — | — | — | 0 |
| 03 | cam2 | Sol omuz | — | — | — | 0 |
| 03 | cam2 | Sağ omuz | — | — | — | 0 |
| 03 | cam2 | Sol kalça | — | — | — | 0 |
| 03 | cam2 | Sağ kalça | — | — | — | 0 |
| 03 | cam2 | Sol diz | 5,97 | 4,18 | 5,57 | 1086 |
| 03 | cam2 | Sağ diz | — | — | — | 0 |

### Görünürlük > 0,35

Sistemdeki eklem eşiği (`MIN_VISIBILITY = 0,35`). Üç noktanın minimum görünürlüğü bu değerin üstündedir.

| Egzersiz | Kamera | Eklem | MAE (°) | SD (°) | Medyan (°) | Kare |
|---|---|---|---:|---:|---:|---:|
| 03 | cam2 | Sol dirsek | — | — | — | 0 |
| 03 | cam2 | Sağ dirsek | — | — | — | 0 |
| 03 | cam2 | Sol omuz | — | — | — | 0 |
| 03 | cam2 | Sağ omuz | — | — | — | 0 |
| 03 | cam2 | Sol kalça | — | — | — | 0 |
| 03 | cam2 | Sağ kalça | — | — | — | 0 |
| 03 | cam2 | Sol diz | 6,16 | 4,41 | 5,79 | 910 |
| 03 | cam2 | Sağ diz | — | — | — | 0 |

## Ayakta — REHAB24-6

Egzersizler Ex2, Ex3, Ex4, Ex6. Video ve mocap 30 fps; kare *i* mocap satırı *i* ile eşlenir. Sekiz açının tümü hesaplanır.

### Tüm kareler

| Egzersiz | Kamera | Eklem | MAE (°) | SD (°) | Medyan (°) | Kare |
|---|---|---|---:|---:|---:|---:|
| Ex4 | Camera17 | Sol dirsek | 8,17 | 8,84 | 5,59 | 597 |
| Ex4 | Camera17 | Sağ dirsek | 14,20 | 7,93 | 14,08 | 597 |
| Ex4 | Camera17 | Sol omuz | 5,43 | 5,27 | 3,96 | 597 |
| Ex4 | Camera17 | Sağ omuz | 18,96 | 6,31 | 19,56 | 597 |
| Ex4 | Camera17 | Sol kalça | 10,83 | 6,52 | 10,87 | 597 |
| Ex4 | Camera17 | Sağ kalça | 7,69 | 3,29 | 7,58 | 597 |
| Ex4 | Camera17 | Sol diz | 11,25 | 4,10 | 11,10 | 597 |
| Ex4 | Camera17 | Sağ diz | 6,72 | 4,96 | 5,30 | 597 |
| Ex4 | Camera18 | Sol dirsek | 26,00 | 20,90 | 23,97 | 600 |
| Ex4 | Camera18 | Sağ dirsek | 26,33 | 14,81 | 25,10 | 600 |
| Ex4 | Camera18 | Sol omuz | 8,77 | 6,72 | 7,93 | 600 |
| Ex4 | Camera18 | Sağ omuz | 40,61 | 25,55 | 37,19 | 600 |
| Ex4 | Camera18 | Sol kalça | 4,84 | 2,65 | 4,63 | 600 |
| Ex4 | Camera18 | Sağ kalça | 4,39 | 3,14 | 3,71 | 600 |
| Ex4 | Camera18 | Sol diz | 5,39 | 3,88 | 4,72 | 600 |
| Ex4 | Camera18 | Sağ diz | 4,63 | 3,49 | 3,90 | 600 |

### Görünürlük > 0,35

| Egzersiz | Kamera | Eklem | MAE (°) | SD (°) | Medyan (°) | Kare |
|---|---|---|---:|---:|---:|---:|
| Ex4 | Camera17 | Sol dirsek | 8,63 | 9,02 | 6,06 | 547 |
| Ex4 | Camera17 | Sağ dirsek | 14,20 | 7,93 | 14,08 | 597 |
| Ex4 | Camera17 | Sol omuz | 4,80 | 5,03 | 3,75 | 547 |
| Ex4 | Camera17 | Sağ omuz | 18,96 | 6,31 | 19,56 | 597 |
| Ex4 | Camera17 | Sol kalça | 10,83 | 6,52 | 10,87 | 597 |
| Ex4 | Camera17 | Sağ kalça | 7,69 | 3,29 | 7,58 | 597 |
| Ex4 | Camera17 | Sol diz | 11,25 | 4,10 | 11,10 | 597 |
| Ex4 | Camera17 | Sağ diz | 6,72 | 4,96 | 5,30 | 597 |
| Ex4 | Camera18 | Sol dirsek | 25,30 | 21,14 | 22,91 | 553 |
| Ex4 | Camera18 | Sağ dirsek | 18,41 | 13,01 | 22,36 | 150 |
| Ex4 | Camera18 | Sol omuz | 8,77 | 6,72 | 7,93 | 600 |
| Ex4 | Camera18 | Sağ omuz | 28,32 | 8,81 | 25,45 | 150 |
| Ex4 | Camera18 | Sol kalça | 5,54 | 2,58 | 5,45 | 435 |
| Ex4 | Camera18 | Sağ kalça | 4,92 | 3,63 | 3,76 | 150 |
| Ex4 | Camera18 | Sol diz | 5,57 | 4,33 | 4,52 | 435 |
| Ex4 | Camera18 | Sağ diz | 2,62 | 2,14 | 2,70 | 150 |

## Kişinin bulunduğu kare oranı

Bir kare, MediaPipe o karede kişiyi bulduğunda (en az bir eklem açısı veya görünürlük > 0) sayılır.

| Veri kümesi | Egzersiz | Kamera | Bulunan kare | Toplam kare | Oran |
|---|---|---|---:|---:|---:|
| UCO | 03 | cam2 | 1184 | 1350 | 87,7% |
| REHAB24-6 | Ex4 | Camera17 | 597 | 600 | 99,5% |
| REHAB24-6 | Ex4 | Camera18 | 600 | 600 | 100,0% |

## Genel özet

Tüm egzersiz, kamera ve (mocap'ı olan) eklemler birlikte. Sırtüstü = UCO, ayakta = REHAB24-6.

| Konum | MAE (°) | SD (°) | Medyan (°) | Kare |
|---|---:|---:|---:|---:|
| Sırtüstü (UCO), tüm kareler | 5,97 | 4,18 | 5,57 | 1086 |
| Sırtüstü (UCO), görünürlük > 0,35 | 6,16 | 4,41 | 5,79 | 910 |
| Ayakta (REHAB24-6), tüm kareler | 12,77 | 14,35 | 8,20 | 9576 |
| Ayakta (REHAB24-6), görünürlük > 0,35 | 11,12 | 10,45 | 8,23 | 7299 |

## Literatür

UCO çalışmasında MediaPipe 3B açı hatası 11,96° ± 9,99° (Aguilar-Ortega ve ark., 2023). O çalışma ayakta yapılan egzersizleri de içerir; buradaki sırtüstü ve ayakta sonuçlar ayrı raporlanmıştır.
