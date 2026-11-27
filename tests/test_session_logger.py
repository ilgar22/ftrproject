"""SessionLogger: ham video, kare zamani ve tekrar karari."""

import csv
import json
import os
import sys
import tempfile
import unittest

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.session_logger import SessionLogger


def _video_yolu(klasor):
    mp4 = os.path.join(klasor, "ham_video.mp4")
    if os.path.exists(mp4) and os.path.getsize(mp4) > 0:
        return mp4
    return os.path.join(klasor, "ham_video.avi")


class SessionLoggerTests(unittest.TestCase):
    def test_ham_video_ve_tekrar_satirlari(self):
        with tempfile.TemporaryDirectory() as kok:
            kayit = SessionLogger("diz", root=kok, fps=20.0)
            for sira in range(1, 31):
                kare = np.zeros((48, 64, 3), dtype=np.uint8)
                kare[:, :, 1] = sira
                no = kayit.write_raw_frame(kare)
                self.assertEqual(no, sira)
                if sira == 10:
                    kayit.log_rep("sayildi", "", "", 0.9)
                if sira == 20:
                    kayit.log_rep("reddedildi", "amplitude", "sol_kalca", 0.3)
            klasor = kayit.close({"total_reps": 1, "rep_history": [{"rep": 1}]})

            self.assertTrue(os.path.isdir(klasor))
            self.assertTrue(os.path.exists(os.path.join(klasor, "oturum.json")))

            with open(os.path.join(klasor, "kareler.csv"), encoding="utf-8", newline="") as f:
                kareler = list(csv.DictReader(f))
            self.assertEqual(len(kareler), 30)
            self.assertEqual(kareler[0]["video_kare"], "1")
            self.assertEqual(kareler[-1]["video_kare"], "30")

            with open(os.path.join(klasor, "tekrarlar.csv"), encoding="utf-8", newline="") as f:
                tekrarlar = list(csv.DictReader(f))
            self.assertEqual(len(tekrarlar), 2)
            self.assertEqual(tekrarlar[0]["video_kare"], "10")
            self.assertEqual(tekrarlar[0]["karar"], "sayildi")
            self.assertEqual(tekrarlar[1]["video_kare"], "20")
            self.assertEqual(tekrarlar[1]["karar"], "reddedildi")
            self.assertEqual(tekrarlar[1]["red_nedeni"], "amplitude")
            self.assertEqual(tekrarlar[1]["eklem"], "sol_kalca")

            with open(os.path.join(klasor, "oturum.json"), encoding="utf-8") as f:
                belge = json.load(f)
            self.assertEqual(belge["kare_sayisi"], 30)
            self.assertEqual(belge["tekrar_karar_sayisi"], 2)
            self.assertNotIn("rep_history", belge["ozet"])
            self.assertEqual(belge["ozet"]["total_reps"], 1)

            cap = cv2.VideoCapture(_video_yolu(str(klasor)))
            self.assertTrue(cap.isOpened())
            ok, kare = cap.read()
            sayi = 0
            yukseklik = genislik = None
            while ok and kare is not None:
                sayi += 1
                yukseklik, genislik = kare.shape[:2]
                ok, kare = cap.read()
            cap.release()
            self.assertEqual(sayi, 30)
            self.assertEqual((genislik, yukseklik), (64, 48))


if __name__ == "__main__":
    unittest.main()
