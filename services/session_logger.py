"""Hasta oturum kaydi: ham kamera karesi ve tekrar karari.

Ekran goruntusu, iskelet cizimi ve dondurulmus kare yazilmaz.
"""

import csv
import json
import time
from datetime import datetime
from pathlib import Path

import cv2


def _guvenli_kimlik(exercise_id):
    """Klasor adinda yol ayraci birakma."""
    if exercise_id is None or str(exercise_id).strip() == "":
        return "egzersiz"
    metin = str(exercise_id).strip()
    temiz = []
    for karakter in metin:
        if karakter.isalnum() or karakter in ("-", "_"):
            temiz.append(karakter)
        else:
            temiz.append("_")
    return "".join(temiz) or "egzersiz"


class SessionLogger:
    """data/oturumlar/<egzersiz>_<zaman>/ altina ham video ve CSV yazar."""

    def __init__(self, exercise_id, root=None, fps=20.0):
        self.exercise_id = exercise_id
        if root is None:
            root = Path(__file__).resolve().parents[1] / "data" / "oturumlar"
        self.root = Path(root)
        self.fps = float(fps)
        damga = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.folder = self.root / f"{_guvenli_kimlik(exercise_id)}_{damga}"
        sira = 2
        while self.folder.exists():
            self.folder = self.root / f"{_guvenli_kimlik(exercise_id)}_{damga}_{sira}"
            sira += 1
        self.folder.mkdir(parents=True)

        self._baslangic_an = time.perf_counter()
        self._baslangic = datetime.now().isoformat(timespec="seconds")
        self._kare_no = 0
        self._tekrar_no = 0
        self._kapali = False
        self._yazar = None

        self._kare_dosya = (self.folder / "kareler.csv").open("w", newline="", encoding="utf-8")
        self._kare_yazici = csv.writer(self._kare_dosya)
        self._kare_yazici.writerow(["video_kare", "zaman_sn"])
        self._kare_dosya.flush()

        self._tekrar_dosya = (self.folder / "tekrarlar.csv").open("w", newline="", encoding="utf-8")
        self._tekrar_yazici = csv.writer(self._tekrar_dosya)
        self._tekrar_yazici.writerow(
            ["tekrar_no", "zaman_sn", "video_kare", "karar", "red_nedeni", "eklem", "kalite"]
        )
        self._tekrar_dosya.flush()

    def _zaman(self):
        return time.perf_counter() - self._baslangic_an

    def _video_ac(self, genislik, yukseklik):
        boyut = (int(genislik), int(yukseklik))
        mp4 = self.folder / "ham_video.mp4"
        yazar = cv2.VideoWriter(
            str(mp4),
            cv2.VideoWriter_fourcc(*"mp4v"),
            self.fps,
            boyut,
        )
        if yazar.isOpened():
            self._yazar = yazar
            return
        yazar.release()
        avi = self.folder / "ham_video.avi"
        yazar = cv2.VideoWriter(
            str(avi),
            cv2.VideoWriter_fourcc(*"MJPG"),
            self.fps,
            boyut,
        )
        if yazar.isOpened():
            self._yazar = yazar
            return
        yazar.release()
        self._yazar = None
        print("[SessionLogger] video yazici acilamadi")

    def write_raw_frame(self, frame_bgr):
        """Ham kareyi yazar. Donus: 1'den baslayan video kare numarasi."""
        if self._kapali or frame_bgr is None:
            return self._kare_no
        if self._yazar is None:
            yukseklik, genislik = frame_bgr.shape[:2]
            self._video_ac(genislik, yukseklik)
        if self._yazar is not None:
            self._yazar.write(frame_bgr)
        self._kare_no += 1
        self._kare_yazici.writerow([self._kare_no, f"{self._zaman():.4f}"])
        self._kare_dosya.flush()
        return self._kare_no

    def log_rep(self, karar, red_nedeni, eklem, kalite):
        """Son yazilan kareye bagli tekrar kararini hemen diske yazar."""
        if self._kapali:
            return
        self._tekrar_no += 1
        self._tekrar_yazici.writerow([
            self._tekrar_no,
            f"{self._zaman():.4f}",
            self._kare_no,
            karar,
            "" if red_nedeni is None else red_nedeni,
            "" if eklem is None else eklem,
            "" if kalite is None else kalite,
        ])
        self._tekrar_dosya.flush()

    def close(self, summary=None):
        """Video ve CSV kapanir, oturum.json yazilir. Klasor yolu doner."""
        if self._kapali:
            return self.folder
        self._kapali = True
        if self._yazar is not None:
            self._yazar.release()
            self._yazar = None
        self._kare_dosya.close()
        self._tekrar_dosya.close()

        ozet = None
        if summary is not None:
            ozet = dict(summary)
            ozet.pop("rep_history", None)
        belge = {
            "baslangic": self._baslangic,
            "bitis": datetime.now().isoformat(timespec="seconds"),
            "kare_sayisi": self._kare_no,
            "tekrar_karar_sayisi": self._tekrar_no,
            "ozet": ozet,
        }
        (self.folder / "oturum.json").write_text(
            json.dumps(belge, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return self.folder
