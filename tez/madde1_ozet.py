"""
Madde 1.6 — CSV ciktilarindan Turkce ozet tablo (tez/madde1_ozet.md).
"""

import csv
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

KOK = Path(__file__).resolve().parents[1]
CIKTI_KOK = KOK / "tez" / "madde1_ciktilar"
OZET_YOL = KOK / "tez" / "madde1_ozet.md"

EKLEMLER = [
    "sol_dirsek", "sag_dirsek", "sol_omuz", "sag_omuz",
    "sol_kalca", "sag_kalca", "sol_diz", "sag_diz",
]
EKLEM_TR = {
    "sol_dirsek": "Sol dirsek",
    "sag_dirsek": "Sağ dirsek",
    "sol_omuz": "Sol omuz",
    "sag_omuz": "Sağ omuz",
    "sol_kalca": "Sol kalça",
    "sag_kalca": "Sağ kalça",
    "sol_diz": "Sol diz",
    "sag_diz": "Sağ diz",
}
GORUNURLUK_ESIK = 0.35


def _tr(sayi, basamak=2):
    if sayi is None or not np.isfinite(sayi):
        return "—"
    return f"{sayi:.{basamak}f}".replace(".", ",")


def _istatistik(hatalar):
    dizi = np.asarray(list(hatalar), dtype=np.float64)
    if dizi.size == 0:
        return None
    sd = float(np.std(dizi, ddof=1)) if dizi.size >= 2 else float("nan")
    return {
        "mae": float(np.mean(dizi)),
        "sd": sd,
        "medyan": float(np.median(dizi)),
        "n": int(dizi.size),
    }


def _csv_oku(yol):
    with yol.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _dosyalari_topla():
    """dataset -> egzersiz -> kamera -> list of csv paths."""
    gruplar = defaultdict(list)
    if not CIKTI_KOK.exists():
        return gruplar
    for veri, klasor in (("uco", "uco"), ("rehab", "rehab")):
        kok = CIKTI_KOK / klasor
        if not kok.exists():
            continue
        for yol in sorted(kok.glob("*.csv")):
            parca = yol.stem.split("_")
            if veri == "uco" and len(parca) >= 3:
                egzersiz, kamera = parca[1], parca[2]
            elif veri == "rehab" and len(parca) >= 3:
                egzersiz, kamera = parca[0], parca[-1]
            else:
                continue
            gruplar[(veri, egzersiz, kamera)].append(yol)
    return gruplar


def _grup_olc(yollar):
    """Eklem bazinda mutlak hatalar ve kare bazinda kisi tespiti."""
    tum = defaultdict(list)
    esikli = defaultdict(list)
    kare_sayisi = 0
    bulunan = 0
    for yol in yollar:
        satirlar = _csv_oku(yol)
        kareler = defaultdict(lambda: {"bulundu": False})
        for satir in satirlar:
            try:
                kare = int(satir["kare"])
            except (KeyError, ValueError):
                continue
            kayit = kareler[kare]
            mp_metin = (satir.get("aci_mediapipe") or "").strip()
            mo_metin = (satir.get("aci_mocap") or "").strip()
            try:
                gor = float(satir.get("gorunurluk") or 0.0)
            except ValueError:
                gor = 0.0
            if mp_metin or gor > 0.0:
                kayit["bulundu"] = True
            if not mp_metin or not mo_metin:
                continue
            eklem = satir.get("eklem") or ""
            hata = abs(float(mp_metin) - float(mo_metin))
            tum[eklem].append(hata)
            if gor > GORUNURLUK_ESIK:
                esikli[eklem].append(hata)
        kare_sayisi += len(kareler)
        bulunan += sum(1 for k in kareler.values() if k["bulundu"])
    return tum, esikli, bulunan, kare_sayisi


def _tablo(satirlar):
    baslik = "| Egzersiz | Kamera | Eklem | MAE (°) | SD (°) | Medyan (°) | Kare |"
    cizgi = "|---|---|---|---:|---:|---:|---:|"
    govde = [baslik, cizgi]
    for s in satirlar:
        govde.append(
            f"| {s['egzersiz']} | {s['kamera']} | {s['eklem']} | "
            f"{_tr(s['mae'])} | {_tr(s['sd'])} | {_tr(s['medyan'])} | {s['n']} |"
        )
    return "\n".join(govde)


def _eklem_satirlari(gruplar, olculer, alan):
    satirlar = []
    for anahtar in _sirali_anahtarlar(gruplar):
        veri, egzersiz, kamera = anahtar
        hatalar = olculer[anahtar][alan]
        for eklem in EKLEMLER:
            ist = _istatistik(hatalar.get(eklem, []))
            satirlar.append({
                "veri": veri,
                "egzersiz": egzersiz,
                "kamera": kamera,
                "eklem": EKLEM_TR.get(eklem, eklem),
                "mae": None if ist is None else ist["mae"],
                "sd": None if ist is None else ist["sd"],
                "medyan": None if ist is None else ist["medyan"],
                "n": 0 if ist is None else ist["n"],
            })
    return satirlar


def _sirali_anahtarlar(gruplar):
    def anahtar(k):
        veri, egzersiz, kamera = k
        veri_sira = 0 if veri == "uco" else 1
        return (veri_sira, egzersiz, kamera)
    return sorted(gruplar.keys(), key=anahtar)


def _havuz(olculer, veri, alan):
    hatalar = []
    for (v, _, _), olcu in olculer.items():
        if v != veri:
            continue
        for dizi in olcu[alan].values():
            hatalar.extend(dizi)
    return _istatistik(hatalar)


def _tespit_tablosu(olculer):
    baslik = "| Veri kümesi | Egzersiz | Kamera | Bulunan kare | Toplam kare | Oran |"
    cizgi = "|---|---|---|---:|---:|---:|"
    govde = [baslik, cizgi]
    ad = {"uco": "UCO", "rehab": "REHAB24-6"}
    for anahtar in _sirali_anahtarlar({k: None for k in olculer}):
        veri, egzersiz, kamera = anahtar
        bulunan, toplam = olculer[anahtar]["tespit"]
        oran = (100.0 * bulunan / toplam) if toplam else float("nan")
        govde.append(
            f"| {ad[veri]} | {egzersiz} | {kamera} | {bulunan} | {toplam} | {_tr(oran, 1)}% |"
        )
    return "\n".join(govde)


def _genel_satir(baslik, ist):
    if ist is None:
        return f"| {baslik} | — | — | — | 0 |"
    return (
        f"| {baslik} | {_tr(ist['mae'])} | {_tr(ist['sd'])} | "
        f"{_tr(ist['medyan'])} | {ist['n']} |"
    )


def ozet_yaz():
    gruplar = _dosyalari_topla()
    olculer = {}
    for anahtar, yollar in gruplar.items():
        tum, esikli, bulunan, toplam = _grup_olc(yollar)
        olculer[anahtar] = {
            "tum": tum,
            "esikli": esikli,
            "tespit": (bulunan, toplam),
            "video": len(yollar),
        }

    uco_tum = [s for s in _eklem_satirlari(gruplar, olculer, "tum") if s["veri"] == "uco"]
    uco_esik = [s for s in _eklem_satirlari(gruplar, olculer, "esikli") if s["veri"] == "uco"]
    rehab_tum = [s for s in _eklem_satirlari(gruplar, olculer, "tum") if s["veri"] == "rehab"]
    rehab_esik = [s for s in _eklem_satirlari(gruplar, olculer, "esikli") if s["veri"] == "rehab"]

    video_sayisi = sum(o["video"] for o in olculer.values())
    parcalar = [
        "# Madde 1.6 — MediaPipe açı doğruluğu (mocap karşılaştırması)",
        "",
        "Hazır MediaPipe Pose Landmarker (heavy, VIDEO, 3B dünya açıları) mocap ile karşılaştırıldı. "
        "Model eğitilmedi. Açı tanımı sistemle aynıdır (`calculate_angle`). "
        "Kare döndürülmedi.",
        "",
        f"Bu özet `tez/madde1_ciktilar/` altındaki **{video_sayisi}** CSV dosyasından üretildi. "
        "Bir eklem satırı, hem MediaPipe hem mocap açısı dolu olan karelerdir. "
        "UCO'da mocap yalnızca çalışan uzvun açısını verir (bacakta diz, kolda dirsek); "
        "diğer eklemlerde mocap hücresi boş olduğu için hata hesaplanmaz.",
        "",
        "SD, mutlak hataların örneklem standart sapmasıdır (n−1).",
        "",
        "## Sırtüstü — UCO",
        "",
        "Egzersizler yatakta sırtüstü: 03/07 düz bacak kaldırma (sol/sağ), 04/08 diz bükme (sol/sağ). Video 25 fps.",
        "",
        "### Tüm kareler",
        "",
        _tablo(uco_tum) if uco_tum else "_CSV yok._",
        "",
        "### Görünürlük > 0,35",
        "",
        "Sistemdeki eklem eşiği (`MIN_VISIBILITY = 0,35`). Üç noktanın minimum görünürlüğü bu değerin üstündedir.",
        "",
        _tablo(uco_esik) if uco_esik else "_CSV yok._",
        "",
        "## Ayakta — REHAB24-6",
        "",
        "Egzersizler Ex2, Ex3, Ex4, Ex6. Video ve mocap 30 fps; kare *i* mocap satırı *i* ile eşlenir. Sekiz açının tümü hesaplanır.",
        "",
        "### Tüm kareler",
        "",
        _tablo(rehab_tum) if rehab_tum else "_CSV yok._",
        "",
        "### Görünürlük > 0,35",
        "",
        _tablo(rehab_esik) if rehab_esik else "_CSV yok._",
        "",
        "## Kişinin bulunduğu kare oranı",
        "",
        "Bir kare, MediaPipe o karede kişiyi bulduğunda (en az bir eklem açısı veya görünürlük > 0) sayılır.",
        "",
        _tespit_tablosu(olculer) if olculer else "_CSV yok._",
        "",
        "## Genel özet",
        "",
        "Tüm egzersiz, kamera ve (mocap'ı olan) eklemler birlikte. Sırtüstü = UCO, ayakta = REHAB24-6.",
        "",
        "| Konum | MAE (°) | SD (°) | Medyan (°) | Kare |",
        "|---|---:|---:|---:|---:|",
        _genel_satir("Sırtüstü (UCO), tüm kareler", _havuz(olculer, "uco", "tum")),
        _genel_satir("Sırtüstü (UCO), görünürlük > 0,35", _havuz(olculer, "uco", "esikli")),
        _genel_satir("Ayakta (REHAB24-6), tüm kareler", _havuz(olculer, "rehab", "tum")),
        _genel_satir("Ayakta (REHAB24-6), görünürlük > 0,35", _havuz(olculer, "rehab", "esikli")),
        "",
        "## Literatür",
        "",
        "UCO çalışmasında MediaPipe 3B açı hatası 11,96° ± 9,99° (Aguilar-Ortega ve ark., 2023). "
        "O çalışma ayakta yapılan egzersizleri de içerir; buradaki sırtüstü ve ayakta sonuçlar ayrı raporlanmıştır.",
        "",
    ]
    OZET_YOL.write_text("\n".join(parcalar), encoding="utf-8")
    print(f"yazildi: {OZET_YOL}", flush=True)


if __name__ == "__main__":
    ozet_yaz()
