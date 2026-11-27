"""
Madde 1 toplu kosu.

  python tez/madde1_toplu.py uco [--kameralar cam2 cam0] [--egzersizler 03 07 04 08]
  python tez/madde1_toplu.py rehab [--egzersizler Ex2 Ex3 Ex4 Ex6]

.csv.tamam olan video atlanir. --sinir N yalnizca ilk N kareyi isler ve .tamam yazmaz.
"""

import argparse
import re
import sys
import time
import zipfile
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
if str(KOK) not in sys.path:
    sys.path.insert(0, str(KOK))

from madde1_calistir import (  # noqa: E402
    CIKTI_KOK,
    REHAB_JOINT_ZIP,
    REHAB_VIDEO_ZIP,
    UCO_ZIP,
    rehab_videoyu_isle,
    uco_mocap_yukle,
    uco_videoyu_isle,
)

UCO_VARSAYILAN = ["03", "07", "04", "08"]
REHAB_VARSAYILAN = ["Ex2", "Ex3", "Ex4", "Ex6"]
UCO_DESEN = re.compile(r"^clips_mp4/(\d+)/(\d{2})/(cam[0-4])\.mp4$")
REHAB_DESEN = re.compile(
    r"^(Ex\d+)/(PM_\d+)-Camera(1[78])-30fps(?:-transposed)?\.mp4$"
)


def _tamam_yolu(csv_yol):
    return Path(str(csv_yol) + ".tamam")


def _tamam_yaz(csv_yol):
    _tamam_yolu(csv_yol).write_text("tamam\n", encoding="utf-8")


def uco_isleri(egzersizler, kameralar):
    istenen_egz = set(egzersizler)
    istenen_kam = set(kameralar)
    isler = []
    with zipfile.ZipFile(UCO_ZIP) as zf:
        for info in zf.infolist():
            ad = info.filename.replace("\\", "/")
            eslesme = UCO_DESEN.match(ad)
            if not eslesme:
                continue
            katilimci, egzersiz, kamera = eslesme.groups()
            if egzersiz not in istenen_egz or kamera not in istenen_kam:
                continue
            csv_yol = CIKTI_KOK / "uco" / f"{katilimci}_{egzersiz}_{kamera}.csv"
            isler.append({
                "ad": f"{katilimci}_{egzersiz}_{kamera}",
                "uye": ad,
                "katilimci": katilimci,
                "egzersiz": egzersiz,
                "kamera": kamera,
                "csv": csv_yol,
            })
    egz_sira = {e: i for i, e in enumerate(egzersizler)}
    kam_sira = {k: i for i, k in enumerate(kameralar)}
    isler.sort(key=lambda j: (
        egz_sira.get(j["egzersiz"], 99),
        int(j["katilimci"]),
        kam_sira.get(j["kamera"], 99),
    ))
    return isler


def rehab_isleri(egzersizler):
    istenen = set(egzersizler)
    isler = []
    with zipfile.ZipFile(REHAB_VIDEO_ZIP) as zf:
        for info in zf.infolist():
            ad = info.filename.replace("\\", "/")
            eslesme = REHAB_DESEN.match(ad)
            if not eslesme:
                continue
            egzersiz, pm, kamera_no = eslesme.groups()
            if egzersiz not in istenen:
                continue
            kamera = f"Camera{kamera_no}"
            csv_yol = CIKTI_KOK / "rehab" / f"{egzersiz}_{pm}_{kamera}.csv"
            isler.append({
                "ad": f"{egzersiz}_{pm}_{kamera}",
                "uye": ad,
                "egzersiz": egzersiz,
                "pm": pm,
                "kamera": kamera,
                "csv": csv_yol,
            })
    egz_sira = {e: i for i, e in enumerate(egzersizler)}
    isler.sort(key=lambda j: (egz_sira.get(j["egzersiz"], 99), j["pm"], j["kamera"]))
    return isler


def _kalan_metni(ort_saniye, kalan_adet):
    if ort_saniye is None or kalan_adet <= 0:
        return "kalan ~ 0 dk"
    dakika = ort_saniye * kalan_adet / 60.0
    return f"kalan ~ {dakika:.1f} dk"


def _kos(isler, isle_fn, sinir):
    n = len(isler)
    if n == 0:
        print("Islenecek video yok.", flush=True)
        return
    islenen_sure = []
    for i, is_ in enumerate(isler, 1):
        csv_yol = is_["csv"]
        if _tamam_yolu(csv_yol).exists():
            print(f"[{i}/{n}] atlandi {is_['ad']}", flush=True)
            continue
        print(f"[{i}/{n}] basladi {is_['ad']}", flush=True)
        t0 = time.perf_counter()
        try:
            kare = isle_fn(is_)
        except Exception as exc:
            print(f"[{i}/{n}] HATA {is_['ad']}: {exc}", flush=True)
            continue
        islenen_sure.append(time.perf_counter() - t0)
        if sinir is None:
            _tamam_yaz(csv_yol)
        kalan_adet = 0
        for sonraki in isler[i:]:
            if not _tamam_yolu(sonraki["csv"]).exists():
                kalan_adet += 1
        ort = sum(islenen_sure) / len(islenen_sure)
        print(
            f"[{i}/{n}] bitti {is_['ad']} ({kare} kare) {_kalan_metni(ort, kalan_adet)}",
            flush=True,
        )


def uco_kos(egzersizler, kameralar, sinir):
    isler = uco_isleri(egzersizler, kameralar)
    print(f"UCO mocap yukleniyor ({len(isler)} video)...", flush=True)
    indeks = uco_mocap_yukle()
    with zipfile.ZipFile(UCO_ZIP) as zf:
        def isle(is_):
            return uco_videoyu_isle(
                zf,
                is_["uye"],
                is_["katilimci"],
                is_["egzersiz"],
                is_["kamera"],
                is_["csv"],
                indeks,
                sinir,
            )
        _kos(isler, isle, sinir)


def rehab_kos(egzersizler, sinir):
    isler = rehab_isleri(egzersizler)
    print(f"REHAB24-6 ({len(isler)} video)", flush=True)
    with zipfile.ZipFile(REHAB_VIDEO_ZIP) as video_zf, zipfile.ZipFile(REHAB_JOINT_ZIP) as joint_zf:
        def isle(is_):
            return rehab_videoyu_isle(
                video_zf,
                joint_zf,
                is_["uye"],
                is_["egzersiz"],
                is_["pm"],
                is_["csv"],
                sinir,
            )
        _kos(isler, isle, sinir)


def main():
    # tez/ calisirken madde1_calistir icinden degil, bu dosyanin dizini import edilir.
    tez_dizin = str(Path(__file__).resolve().parent)
    if tez_dizin not in sys.path:
        sys.path.insert(0, tez_dizin)

    parser = argparse.ArgumentParser(description="MediaPipe mocap karsilastirmasi toplu kosu")
    parser.add_argument("kumesi", choices=["uco", "rehab"])
    parser.add_argument("--kameralar", nargs="+", default=["cam2"])
    parser.add_argument("--egzersizler", nargs="+", default=None)
    parser.add_argument("--sinir", type=int, default=None)
    args = parser.parse_args()
    if args.sinir is not None and args.sinir < 1:
        parser.error("--sinir 1 veya daha buyuk olmali")

    if args.kumesi == "uco":
        egzersizler = args.egzersizler or UCO_VARSAYILAN
        uco_kos(egzersizler, args.kameralar, args.sinir)
    else:
        egzersizler = args.egzersizler or REHAB_VARSAYILAN
        rehab_kos(egzersizler, args.sinir)


if __name__ == "__main__":
    main()
