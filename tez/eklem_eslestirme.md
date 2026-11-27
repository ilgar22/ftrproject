# Eklem eşleştirmesi — MediaPipe ↔ mocap (Madde 1.4)

Açı, sistemdeki `calculate_angle` ile üç noktadan hesaplanır (tepe noktası ortadaki eklemdir). Tanımlar `services/pose_engine.py` içindeki `JOINT_ANGLES` ile aynıdır. MediaPipe açıları 3B dünya koordinatlarından alınır.

| Açı | Üç nokta | MediaPipe (indeks) | REHAB24-6 (`joints_names.txt`) | UCO (`dataset_3d` eklem anahtarı) |
|---|---|---|---|---|
| sol_dirsek | omuz – **dirsek** – bilek | 11 – 13 – 15 | LeftArm (7) – LeftForeArm (8) – LeftHand (9) | `l_shoulder`, `l_elbow`, `l_wrist` (egzersiz 09–12) |
| sag_dirsek | omuz – **dirsek** – bilek | 12 – 14 – 16 | RightArm (12) – RightForeArm (13) – RightHand (14) | `r_shoulder`, `r_elbow`, `r_wrist` (egzersiz 13–16) |
| sol_omuz | dirsek – **omuz** – kalça | 13 – 11 – 23 | LeftForeArm (8) – LeftArm (7) – LeftUpLeg (16) | yok (üç nokta kaydedilmemiş) |
| sag_omuz | dirsek – **omuz** – kalça | 14 – 12 – 24 | RightForeArm (13) – RightArm (12) – RightUpLeg (21) | yok |
| sol_kalca | omuz – **kalça** – diz | 11 – 23 – 25 | LeftArm (7) – LeftUpLeg (16) – LeftLeg (17) | yok |
| sag_kalca | omuz – **kalça** – diz | 12 – 24 – 26 | RightArm (12) – RightUpLeg (21) – RightLeg (22) | yok |
| sol_diz | kalça – **diz** – ayak bileği | 23 – 25 – 27 | LeftUpLeg (16) – LeftLeg (17) – LeftFoot (18) | `l_hip`, `l_knee`, `l_ankle` (egzersiz 01–04) |
| sag_diz | kalça – **diz** – ayak bileği | 24 – 26 – 28 | RightUpLeg (21) – RightLeg (22) – RightFoot (23) | `r_hip`, `r_knee`, `r_ankle` (egzersiz 05–08) |

## UCO — hangi açı

`p3d.txt` her satırda çalışan uzvun üç ekleminin x y z değerini tutar (9 sayı). Karşılık gelen isimler `dataset_3d` kaydındaki anahtarlardan okunur:

- Bacak (01–08): kalça, diz, ayak bileği → yalnızca **diz** açısı (`sol_diz` veya `sag_diz`).
- Kol (09–16): omuz, dirsek, bilek → yalnızca **dirsek** açısı (`sol_dirsek` veya `sag_dirsek`).

Bu çalışmanın sırtüstü alt kümesi 03, 07, 04, 08 olduğu için UCO tarafında karşılaştırılan açı dizdir. Diğer yedi açının `aci_mocap` hücresi boş bırakılır. Kayıttaki hazır `angle` alanı kullanılmaz; açı üç noktadan yeniden hesaplanır.

## REHAB24-6 — hangi açı

26 eklemin tamamı vardır; sekiz açının hepsi hesaplanır. `LeftShoulder` (6) ve `RightShoulder` (11) köprücük eklemidir, omuz olarak kullanılmaz. Omuz noktası `LeftArm` / `RightArm`dir.

## Kare eşleştirme ve fps

| Veri kümesi | Video fps | Mocap fps | Eşleştirme |
|---|---:|---:|---|
| UCO | 25 | 25 (kare `id`) | Mocap karesinin `id` alanı video kare numarasıdır (0 tabanlı). Satır sırası kullanılmaz. Örnek: `clips_mp4/1/03` videosu 844 kare, mocap 839 kare, `id` 5’ten 843’e kadar aralıksız gider. |
| REHAB24-6 | 30 | 30 (`*-30fps.npy`) | Video karesi *i* = mocap satırı *i*. Uzun olan kısa olana kesilir. `*-120fps.npy` kullanılmaz. |

UCO koordinat kaynağı: zip içindeki `dataset_3d.json` yalnızca 42 klip içerir (`clips_mp4/1/03` yoktur). Tüm kliplerin `id` ve eklem koordinatları `veri/UCO/dataset_3d_with_angles.json` dosyasındadır. `clips_mp4/1/03` için bu dosyadaki ilk kare ile `p3d.txt` ilk satırı aynı dokuz sayıdır.

Sol/sağ, kişinin kendi sol/sağıdır. Görüntü yatay çevrilmez ve 90° döndürülmez.

## Kaydırma kontrolü (UCO)

Diz açısında mocap −10…+10 kare kaydırıldı. Üç videoda (diz hareketinin belirgin olduğu aralık, cam2) ortalama mutlak hata:

| Video | Aralık (kare) | Minimumun olduğu kayma | Kayma 0 MAE | Minimum MAE |
|---|---|---:|---:|---:|
| 19 / 04 / cam2 | 330–479 | −2 | 4,87° | 4,49° |
| 18 / 08 / cam2 | 40–189 | 0 | 4,60° | 4,60° |
| 18 / 04 / cam2 | 60–209 | +1 | 3,75° | 3,72° |

Minimum her videoda tam 0’da değil (−2, 0, +1). Eğri 0’ın etrafında; kayma 0 ile minimum arasındaki fark en fazla 0,4°. Eşleştirme bu yüzden kaydırılmadı, `id` olduğu gibi kullanıldı.
