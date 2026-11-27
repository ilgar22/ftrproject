"""
Madde 1.3-1.5 — hazir MediaPipe heavy modelini mocap ile karsilastirir.

Model egitilmez. Her video icin yeni PoseEngine (VIDEO, 3B dunya acilari).
Kare dondurulmez (preprocess_frame kullanilmaz).
"""

import csv
import io
import json
import os
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

import cv2
import numpy as np

KOK = Path(__file__).resolve().parents[1]
if str(KOK) not in sys.path:
    sys.path.insert(0, str(KOK))

from services.pose_engine import (  # noqa: E402
    JOINT_ANGLES,
    PoseEngine,
    calculate_angle,
    extract_angles,
    extract_visibility,
)

UCO_ZIP = KOK / "veri" / "UCO" / "dataset.zip"
# Zip icindeki dataset_3d.json yalnizca 42 klip tutar (1/03 yok).
# Tum kliplerin kare id ve koordinatlari bu dosyadadir; aci alani kullanilmaz.
UCO_JSON = KOK / "veri" / "UCO" / "dataset_3d_with_angles.json"
REHAB_VIDEO_ZIP = KOK / "veri" / "REHAB24-6" / "videos.zip"
REHAB_JOINT_ZIP = KOK / "veri" / "REHAB24-6" / "3d_joints.zip"
CIKTI_KOK = KOK / "tez" / "madde1_ciktilar"

UCO_FPS = 25.0
REHAB_FPS = 30.0
EKLEM_SIRASI = list(JOINT_ANGLES.keys())
CSV_BASLIK = ["kare", "zaman", "eklem", "aci_mediapipe", "aci_mocap", "gorunurluk"]

# UCO uc noktadan yalnizca bir aci cikar. Anahtarlar dataset_3d kaydindan.
UCO_ACI_KALIBI = (
    (("l_hip", "l_knee", "l_ankle"), "sol_diz"),
    (("r_hip", "r_knee", "r_ankle"), "sag_diz"),
    (("l_shoulder", "l_elbow", "l_wrist"), "sol_dirsek"),
    (("r_shoulder", "r_elbow", "r_wrist"), "sag_dirsek"),
)

# REHAB24-6 joints_names.txt. LeftShoulder=6 koprucuk, kullanilmaz.
REHAB_ACILAR = {
    "sol_dirsek": (7, 8, 9),
    "sag_dirsek": (12, 13, 14),
    "sol_omuz": (8, 7, 16),
    "sag_omuz": (13, 12, 21),
    "sol_kalca": (7, 16, 17),
    "sag_kalca": (12, 21, 22),
    "sol_diz": (16, 17, 18),
    "sag_diz": (21, 22, 23),
}


def _uco_eklem_adi(eklem_anahtarlari):
    """Uc mocap noktasinin hangi sistem acisina denk geldigini bulur."""
    anahtarlar = set(eklem_anahtarlari) - {"angle"}
    for uc, ad in UCO_ACI_KALIBI:
        if set(uc) <= anahtarlar:
            return ad, uc
    return None, None


def uco_mocap_yukle(json_yol=None):
    """(katilimci, egzersiz) -> {eklem, id_aci}. id = video kare numarasi."""
    yol = Path(json_yol) if json_yol else UCO_JSON
    with yol.open("r", encoding="utf-8") as f:
        kayitlar = json.load(f)["data"]
    indeks = {}
    for kayit in kayitlar:
        kareler = kayit.get("frames") or []
        eklem, uc = (None, None)
        if kareler:
            eklem, uc = _uco_eklem_adi(kareler[0].get("joints", {}).keys())
        id_aci = {}
        if eklem:
            for kare in kareler:
                eklemler = kare.get("joints") or {}
                try:
                    noktalar = [
                        (
                            float(eklemler[ad]["x"]),
                            float(eklemler[ad]["y"]),
                            float(eklemler[ad]["z"]),
                        )
                        for ad in uc
                    ]
                    id_aci[int(kare["id"])] = round(calculate_angle(*noktalar), 2)
                except (KeyError, TypeError, ValueError):
                    id_aci[int(kare["id"])] = None
        indeks[(str(kayit["folder"]), str(kayit["exercise"]))] = {
            "eklem": eklem,
            "id_aci": id_aci,
        }
    return indeks


def _zip_uyesi_diske(zf, uye_adi):
    """Tek videoyu gecici dosyaya cikarir. Cagiran siler."""
    fd, yol = tempfile.mkstemp(suffix=".mp4")
    os.close(fd)
    with zf.open(uye_adi) as src, open(yol, "wb") as dst:
        shutil.copyfileobj(src, dst)
    return yol


def _sayi_hucre(deger, basamak):
    if deger is None:
        return ""
    return f"{float(deger):.{basamak}f}"


def csv_yaz(yol, satirlar):
    yol = Path(yol)
    yol.parent.mkdir(parents=True, exist_ok=True)
    gecici = yol.with_suffix(yol.suffix + ".yaziliyor")
    with gecici.open("w", newline="", encoding="utf-8") as f:
        yazici = csv.writer(f)
        yazici.writerow(CSV_BASLIK)
        for s in satirlar:
            yazici.writerow([
                s["kare"],
                s["zaman"],
                s["eklem"],
                _sayi_hucre(s["aci_mediapipe"], 2),
                _sayi_hucre(s["aci_mocap"], 2),
                _sayi_hucre(s["gorunurluk"], 4),
            ])
    gecici.replace(yol)


def videodan_satirlar(video_yol, fps, sinir, mocap_fn, baslangic=0):
    """Video karelerini MediaPipe'tan gecirir. 8 eklem satiri / kare.

    sinir: baslangictan itibaren islenecek kare sayisi. None ise videonun sonuna kadar.
    baslangic: bu kareye kadar tespit yapilmaz (kare numarasi videonun basindan sayilir).
    """
    motor = PoseEngine()
    if motor._landmarker is None:
        motor.release()
        raise RuntimeError("MediaPipe modeli acilamadi")
    cap = cv2.VideoCapture(str(video_yol))
    satirlar = []
    try:
        olculen = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
        if olculen and abs(olculen - fps) > 1.5:
            print(f"uyari: dosya fps {olculen:.2f}, zaman hesabi {fps:.0f} fps", flush=True)
        kare = 0
        islendi = 0
        while cap.isOpened():
            ok, kare_bgr = cap.read()
            if not ok:
                break
            if kare < baslangic:
                kare += 1
                continue
            if sinir is not None and islendi >= sinir:
                break
            zaman = f"{kare / fps:.4f}"
            goruntu, dunya = motor._detect_landmarks(kare_bgr)
            mocap = mocap_fn(kare) or {}
            if goruntu is None:
                acilar = {}
                gorunur = {}
                kisi_var = False
            else:
                kisi_var = True
                acilar = extract_angles(dunya, goruntu, min_visibility=-1.0) if dunya else {}
                gorunur = extract_visibility(goruntu)
            for eklem in EKLEM_SIRASI:
                satirlar.append({
                    "kare": kare,
                    "zaman": zaman,
                    "eklem": eklem,
                    "aci_mediapipe": acilar.get(eklem) if kisi_var else None,
                    "aci_mocap": mocap.get(eklem),
                    "gorunurluk": 0.0 if not kisi_var else float(gorunur.get(eklem, 0.0)),
                })
            kare += 1
            islendi += 1
    finally:
        cap.release()
        motor.release()
    return satirlar


def uco_videoyu_isle(zf, uye_adi, katilimci, egzersiz, kamera, cikti_yol, mocap_indeks, sinir=None):
    """Tek UCO videosu. Mocap acisi yalnizca calisan uzvun eklemindedir."""
    bilgi = mocap_indeks.get((str(katilimci), str(egzersiz)), {})
    eklem = bilgi.get("eklem")
    id_aci = bilgi.get("id_aci") or {}

    def mocap_fn(kare):
        if not eklem or kare not in id_aci or id_aci[kare] is None:
            return {}
        return {eklem: id_aci[kare]}

    gecici = _zip_uyesi_diske(zf, uye_adi)
    try:
        satirlar = videodan_satirlar(gecici, UCO_FPS, sinir, mocap_fn)
    finally:
        os.remove(gecici)
    csv_yaz(cikti_yol, satirlar)
    return len(satirlar) // len(EKLEM_SIRASI)


def rehab_mocap_acilari(dizi):
    """(kare, 26, 4) dizisinden 8 aci. 120 fps dosyasi verilmemelidir."""
    acilar = []
    for kare in dizi:
        satir = {}
        for ad, (i, j, k) in REHAB_ACILAR.items():
            a, b, c = kare[i, :3], kare[j, :3], kare[k, :3]
            if not (np.isfinite(a).all() and np.isfinite(b).all() and np.isfinite(c).all()):
                continue
            satir[ad] = round(calculate_angle(a, b, c), 2)
        acilar.append(satir)
    return acilar


def rehab_npy_oku(zf, egzersiz, pm):
    uye = f"{egzersiz}/{pm}-30fps.npy"
    try:
        ham = zf.read(uye)
    except KeyError:
        return None
    return np.load(io.BytesIO(ham))


def rehab_videoyu_isle(video_zf, joint_zf, uye_adi, egzersiz, pm, cikti_yol, sinir=None):
    """Tek REHAB24-6 videosu. Kare i = mocap satiri i; kisa olana gore kesilir."""
    dizi = rehab_npy_oku(joint_zf, egzersiz, pm)
    if dizi is None:
        mocap_kareleri = []
    else:
        mocap_kareleri = rehab_mocap_acilari(dizi)

    def mocap_fn(kare):
        if kare >= len(mocap_kareleri):
            return {}
        return mocap_kareleri[kare]

    gecici = _zip_uyesi_diske(video_zf, uye_adi)
    try:
        satirlar = videodan_satirlar(gecici, REHAB_FPS, sinir, mocap_fn)
    finally:
        os.remove(gecici)
    csv_yaz(cikti_yol, satirlar)
    return len(satirlar) // len(EKLEM_SIRASI)


def kaydirma_hatasi(satirlar, eklem):
    """Ayni videoda mocap'i -10..+10 kare kaydirinca diz/eklem MAE."""
    mp = {}
    mo = {}
    for s in satirlar:
        if s["eklem"] != eklem:
            continue
        mp[s["kare"]] = s["aci_mediapipe"]
        mo[s["kare"]] = s["aci_mocap"]
    tablo = []
    for kayma in range(-10, 11):
        hatalar = []
        for kare, aci_mp in mp.items():
            aci_mo = mo.get(kare + kayma)
            if aci_mp is None or aci_mo is None:
                continue
            hatalar.append(abs(float(aci_mp) - float(aci_mo)))
        if hatalar:
            tablo.append((kayma, float(np.mean(hatalar)), len(hatalar)))
    return tablo


def _kaydirma_minimum(tablo):
    if not tablo:
        return []
    en_kucuk = min(mae for _, mae, _ in tablo)
    return [kayma for kayma, mae, _ in tablo if abs(mae - en_kucuk) < 1e-9]


def uco_kaydirma_kontrol(n_video=3, sinir=None, egzersiz="03", kamera="cam2", baslangic=0, secim=None):
    """UCO videolarinda diz hatasinin kaydirma minimumunu basar.

    secim: [(katilimci, egzersiz, kamera, baslangic, sinir), ...]
    Verilmezse egzersiz/kamera ile ilk n video, ortak baslangic/sinir kullanilir.
    """
    import re

    indeks = uco_mocap_yukle()
    if secim is None:
        desen = re.compile(r"^clips_mp4/(\d+)/(\d{2})/(cam[0-4])\.mp4$")
        adaylar = []
        with zipfile.ZipFile(UCO_ZIP) as zf:
            for info in zf.infolist():
                eslesme = desen.match(info.filename.replace("\\", "/"))
                if not eslesme:
                    continue
                katilimci, egz, kam = eslesme.groups()
                if egz == egzersiz and kam == kamera:
                    adaylar.append((int(katilimci), egz, kam))
        adaylar.sort()
        secim = [
            (str(kat), egz, kam, baslangic, sinir)
            for kat, egz, kam in adaylar[:n_video]
        ]
    raporlar = []
    with zipfile.ZipFile(UCO_ZIP) as zf:
        for katilimci, egz, kam, bas, uzunluk in secim:
            uye = f"clips_mp4/{katilimci}/{egz}/{kam}.mp4"
            bilgi = indeks.get((str(katilimci), str(egz)), {})
            eklem = bilgi.get("eklem")
            id_aci = bilgi.get("id_aci") or {}

            def mocap_fn(kare, _eklem=eklem, _id_aci=id_aci):
                if not _eklem or kare not in _id_aci or _id_aci[kare] is None:
                    return {}
                return {_eklem: _id_aci[kare]}

            gecici = _zip_uyesi_diske(zf, uye)
            try:
                satirlar = videodan_satirlar(gecici, UCO_FPS, uzunluk, mocap_fn, baslangic=bas)
            finally:
                os.remove(gecici)
            tablo = kaydirma_hatasi(satirlar, eklem) if eklem else []
            minimumlar = _kaydirma_minimum(tablo)
            ad = f"{katilimci}_{egz}_{kam}"
            raporlar.append({
                "ad": ad,
                "eklem": eklem,
                "baslangic": bas,
                "tablo": tablo,
                "minimumlar": minimumlar,
            })
            print(f"kaydirma {ad} eklem={eklem} kare {bas}..", flush=True)
            for kayma, mae, n in tablo:
                isaret = "  <-- min" if kayma in minimumlar else ""
                print(f"  {kayma:+d}  MAE {mae:.2f}  n={n}{isaret}", flush=True)
            if minimumlar == [0]:
                print("  minimum kayma 0", flush=True)
            else:
                print(f"  UYARI: minimum kayma 0 degil: {minimumlar}", flush=True)
    return raporlar


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="UCO kare kaydirma kontrolu")
    parser.add_argument("--n", type=int, default=3)
    parser.add_argument("--sinir", type=int, default=None)
    parser.add_argument("--baslangic", type=int, default=0)
    parser.add_argument("--egzersiz", default="03")
    parser.add_argument("--kamera", default="cam2")
    args = parser.parse_args()
    uco_kaydirma_kontrol(args.n, args.sinir, args.egzersiz, args.kamera, args.baslangic)
