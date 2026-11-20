# Tez Notları

## Gelecek çalışmalar — Omurga hareketlerinin değerlendirilmesi

> **Teze yazılacak:** "Gelecek Çalışmalar" bölümünde. Ayrıca kapsam dışı bırakılan hareketlerin gerekçesi olarak Sınırlılıklar bölümünde de anılmalı.
> Not tarihi: 20.11.2026.

**Durum**
- MediaPipe'ta omurga noktası yok. Gövdede yalnızca iki omuz ve iki kalça; başta burun, gözler, kulaklar ve ağız noktaları var. Boyun açısı ancak baş noktaları ile omuzlardan yaklaşık olarak hesaplanabilir.
- Bu nedenle omurga hareketleri (ör. kedi-deve, gövde döndürme) mevcut sistemle değerlendirilemiyor ve çalışmanın kapsamı dışında bırakıldı.
- **Android'de, normal telefon kamerasıyla omurga noktası veren hazır bir kütüphane bulunamadı.**
  - Google ML Kit: MediaPipe ile aynı 33 nokta, omurga yok.
  - Nuitrack: omurga bölgesinde nokta veriyor ama derinlik kamerası gerektiriyor.
- Omurga noktası veren seçenekler yalnızca iOS'ta var:
  - Apple Vision 3B: 17 nokta; omurga boyunca tek nokta (spine), ayrıca baş merkezi ve baş tepesi.
  - Apple ARKit vücut takibi: 7 omurga ve 4 boyun noktası; ancak yalnızca arka kamera, A12 ve sonrası çip gerekiyor. Omurga noktalarının doğruluğunu ölçen bir çalışma bulunamadı.

**Gelecek çalışma önerisi (teze)**
Omurga hareketlerinin değerlendirilmesi, Android ve iOS'ta ortak çalışan ve omurga noktası veren bir poz kestirim modeli yayımlandığında ya da iOS'a özel bir sürümde Apple Vision 3B / ARKit ile ele alınabilir. Bu durumda öznitelik vektörüne gövde, boyun ve baş açıları eklenerek kedi-deve ve gövde döndürme gibi hareketler de kapsama alınabilir.

**Kaynaklar**
- Apple Developer, HumanBodyPose3DObservation.JointName: https://developer.apple.com/documentation/vision/humanbodypose3dobservation/jointname
- Apple Developer, Validating a model for motion capture (ARKit iskeleti): https://developer.apple.com/documentation/arkit/validating-a-model-for-motion-capture
- Apple Developer, ARBodyTrackingConfiguration: https://developer.apple.com/documentation/arkit/arbodytrackingconfiguration
- Google, ML Kit Pose Detection: https://developers.google.com/ml-kit/vision/pose-detection
- 3DiVi, Nuitrack SDK: https://github.com/3DiVi/nuitrack-sdk
