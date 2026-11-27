# Hareket hataları (Madde 3.1)

Her hareket için 2 hata seçildi:
- **Hata A:** hareketin eksik açıklıkla yapılması (tüm egzersizlerde ortak, `yapilacaklar.md` 3.1).
- **Hata B:** egzersize özgü form hatası.

Seçim kuralları: (1) literatürde sık geçiyor, (2) sağlıklı gönüllü güvenle yapabilir (hata hafif ve kontrollü yapılır, abartılmaz), (3) tek kameradan görülebilir (kameraya doğru / kameradan uzağa olan hareketler seçilmedi).

| Hareket | Hata A | Kaynak | Hata B | Kaynak |
|---|---|---|---|---|
| Köprü | Kalça yeterince kalkmıyor; omuz–kalça–diz düz bir çizgi oluşturmadan iniliyor | [4], [11] | Kalçayı fazla yükseğe itip beli çukurlaştırma (bel hiperekstansiyonu; hareketi kalça yerine belle yapma) | [5], [6], [7] |
| Sırtüstü düz bacak kaldırma | Bacak yeterince kalkmıyor (karşı uyluk seviyesine ulaşmıyor) | [8], [11] | Kalkan bacakta dizin bükülmesi (diz ekstansiyon kaybı / "quadriceps lag") | [9], [10] |
| Dört ayaktan köpek pozuna geçiş | Kalça yeterince yükselmiyor; kollar ve gövde düz çizgiye gelmiyor (yarım köpek pozu) | [11], [12] | Dirseklerin bükülmesi / kol hattının dirsekte kırılması (omuzların çökmesi) | [13], [14] |
| Yan yatarak bacak kaldırma | Bacak yeterli abdüksiyona ulaşmıyor (normal örüntü yaklaşık 40°) | [15], [11] | Bacağı kaldırırken pelvisi yukarı çekme (ipsilateral pelvik elevasyon / lateral pelvik tilt) | [15], [16] |
| Kuş-köpek | Kol ve bacak yere paralel seviyeye kadar uzatılmıyor | [1], [11] | Bacağı fazla kaldırıp beli çukurlaştırma (lomber lordozun artması) | [1], [2], [3] |
| Ölü böcek | Kol ve bacak tam uzatılmıyor (hareket kısa kalıyor) | [11], [19] | Kol/bacak uzarken belin yerden kalkması (lomber ekstansiyon, nötr omurganın kaybı) | [17], [18], [19] |

## Notlar

1. **Hata A için ortak kaynak:** FitAQA [11] egzersiz hataları sınıflandırmasında hareket açıklığı ile ilgili hataları ayrı bir kategori olarak tanımlıyor. Her egzersizdeki "doğru" hareket sınırı ilgili egzersiz tarifinden alınmıştır.
2. **Ölçülebilirlik uyarısı:** Köprü, kuş-köpek ve ölü böcekteki Hata B'ler bel (lomber omurga) hareketidir. MediaPipe'ta omurga noktası yok (bkz. `notlar.md`); sistemimizin 8 açısı bu hatayı yalnızca dolaylı olarak (kalça açısı üzerinden) görebilir. Bunlar literatürde en sık geçen hatalar olduğu için seçildi; sistem yakalayamazsa 3.6'da "yakalanamayan hata türü" olarak raporlanır.
3. **Ölçülebilir alternatif Hata B'ler** (hocayla karar verilecek):
   - Kuş-köpek: kalkan bacakta dizin bükük kalması (tarif: "kalçayı ekstansiyona getir, dizi düzleştir" [1]) — diz açısı ile ölçülür.
   - Yan yatarak bacak kaldırma: çalışan bacakta aşırı diz fleksiyonu [11] — diz açısı ile ölçülür; ancak ayak kameradan uzağa gidebilir, görünürlük kontrol edilmeli.
4. **Güvenlik:** Bel hiperekstansiyonu ve pelvik elevasyon sağlıklı gönüllülerde hafif yapıldığında risk taşımaz; gönüllüye "abartmadan, ağrı olursa dur" talimatı verilir. Ağrı olursa o tekrar yapılmaz.
5. **Kamera:** Köprü, düz bacak, köpek pozu, kuş-köpek ve ölü böcek hatalarının hepsi sagital düzlemdedir (yandan kamera). Yan yatarak bacak kaldırmada pelvik elevasyon frontal düzlemdedir; kamera gönüllünün önünden/arkasından bakmalıdır (fizyoterapist videosundaki görünümle karşılaştırılmalı).

## Kaynaklar

1. American Council on Exercise (ACE). *Bird Dog* — Exercise Library. https://www.acefitness.org/resources/everyone/exercise-library/14/bird-dog/
2. Mike Reinold, DPT. *5 Common Core Exercise Mistakes and Fixes.* https://mikereinold.com/5-common-core-exercise-mistakes-and-fixes/
3. DVRT Restoration. *Bird Dog Module.* https://s3.amazonaws.com/dvrtrestoration/DVRTRestorationBIrdDogModule.pdf
4. Peloton. *Glute Bridge* (fizyoterapist görüşleriyle). https://www.onepeloton.com/en-AU/blog/glute-bridge
5. Acıbadem International. *Glute Bridge: The Underrated Exercise Your Back Will Thank You For.* https://acibademinternational.com/?p=345566
6. NASM. *Why the Glute Bridge Belongs in Almost Every Client Program.* https://www.nasm.org/resource-center/blog/training/why-the-glute-bridge-belongs-in-almost-every-client-program
7. Redefining Strength. *Are You Bridging Wrong?* https://redefiningstrength.com/search/Bridge+wrong
8. MSD/Merck Manual Professional. *Straight Leg Raise* (egzersiz talimatı). https://merckmanuals.com/professional/multimedia/video/straight-leg-raise
9. Physiopedia. *Knee Extension Lag.* https://www.physio-pedia.com/Knee_Extension_Lag
10. Mike Reinold, DPT. *Extension Lag Following Knee Surgery.* https://mikereinold.com/extension-lag-following-knee-surgery/
11. FitAQA: A Benchmark of Fitness Action Quality Assessment for Multimodal Large Language Models (2026). arXiv:2608.08736. https://arxiv.org/abs/2608.08736
12. Chopra. *5 Common Yoga Alignment Mistakes and How to Fix Them.* https://www.chopra.com/blogs/yoga/5-common-yoga-alignment-mistakes-and-how-to-fix-them
13. Donna Farhi. *Downward Facing Dog.* https://donnafarhi.co.nz/downward-facing-dog/
14. DoYouYoga. *Downward Dog.* https://www.doyouyoga.com/downward-dog
15. Kim H., Kwon O., Yi C., Cynn H., Choi H. Lumbar stabilizer muscle activity and pelvic lateral tilting during hip abduction in side-lying (Janda, 1996 normal örüntü tanımıyla). https://www.koreascience.or.kr/article/JAKO201335057740170.pdf
16. Change in Pelvic Motion Caused by Visual Biofeedback Influences Trunk and Hip Muscle Activities During Side-Lying Hip Abduction in Asymptomatic Individuals. https://www.koreascience.or.kr/article/JAKO201930968644240.pdf
17. NASM. *Dead Bug* — Exercise Library. https://www.nasm.org/resource-center/exercise-library/dead-bug
18. Sport Manitoba (N. Prokop). *Dead bug: common mistakes.* https://sportmanitoba.ca/?p=4450
19. Mike Reinold, DPT. *5 Common Core Exercise Mistakes and Fixes* (Dead Bug bölümü). https://mikereinold.com/5-common-core-exercise-mistakes-and-fixes/
