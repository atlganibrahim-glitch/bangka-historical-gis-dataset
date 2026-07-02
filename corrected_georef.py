# -*- coding: utf-8 -*-
"""
Bangka Haritaları - Düzeltilmiş Otomatik Georeferencing
========================================================
Bu script:
1. Sheet ID'den Batavia Datum koordinatlarını hesaplar
2. Batavia (EPSG:4211) -> WGS 84 (EPSG:4326) datum dönüşümü yapar
3. Crop margin'lerini koordinatlara yansıtır
4. GeoTIFF olarak kaydeder

Yazar: Otomatik üretildi
Tarih: 2026
"""
import os
import sys
import pandas as pd
from osgeo import gdal, osr

gdal.UseExceptions()

# ==============================================================================
# AYARLAR
# ==============================================================================
INPUT_DIR    = os.path.dirname(os.path.abspath(__file__))   # crop_xxx.jpg burada
OUTPUT_DIR   = os.path.join(INPUT_DIR, "DUZELTILMIS_HARITALAR")
CSV_PATH     = os.path.join(INPUT_DIR, "bangka_dataset.csv")

# Subgrid haritası (Hollanda 1:25.000 sistemine göre)
# Her büyük hücre 20' x 20' (20 dakika), 4x4 = 16 alt hücreye bölünmüş
# Her alt hücre 5' x 5' (5 dakika)
SUBGRID_MAP = {
    'a': (0, 0), 'b': (1, 0), 'c': (2, 0), 'd': (3, 0),
    'e': (0, 1), 'f': (1, 1), 'g': (2, 1), 'h': (3, 1),
    'i': (0, 2), 'k': (1, 2), 'l': (2, 2), 'm': (3, 2),
    'n': (0, 3), 'o': (1, 3), 'p': (2, 3), 'q': (3, 3)
}

# Her subgrid hücresi 5 dakika = 5/60 derece
SUBGRID_SIZE = 5.0 / 60.0  # derece cinsinden (~9.25 km)

# Hollanda Hindiçin haritacılık sistemi - büyük hücre 20' x 20'
BIG_CELL = 20.0 / 60.0  # = 4 * SUBGRID_SIZE

# Roma rakamı karşılıkları
ROMAN_MAP = {
    'XXIII': 23, 'XXIV': 24, 'XXV': 25,
    'XXVI': 26, 'XXVII': 27, 'XXVIII': 28
}

# ==============================================================================
# DATUM DÖNÜŞÜM KURULUMU
# Batavia (EPSG:4211) -> WGS 84 (EPSG:4326)
# ==============================================================================
src_srs = osr.SpatialReference()
src_srs.ImportFromEPSG(4211)  # Batavia

dst_srs = osr.SpatialReference()
dst_srs.ImportFromEPSG(4326)  # WGS 84

transform = osr.CoordinateTransformation(src_srs, dst_srs)


def roman_to_int(roman):
    if roman not in ROMAN_MAP:
        raise ValueError(f"Bilinmeyen Roma rakamı: '{roman}'")
    return ROMAN_MAP[roman]


def batavia_to_wgs84(lon, lat):
    """Batavia datum koordinatını WGS 84'e dönüştür."""
    result = transform.TransformPoint(lon, lat)
    return result[0], result[1]  # (lon_wgs84, lat_wgs84)


def hesapla_koordinatlar(sheet_id, margin_left, margin_right, margin_top, margin_bottom):
    """
    Sheet ID'den tam koordinatları hesapla.
    
    Hollanda haritacılık sistemi:
    - Sütun numarası (31, 32, 33...): Her sütun 20' enlem aralığı
    - Roma rakamı (XXIII, XXIV...): Her satır 20' boylam aralığı  
    - Alt kod (a-q): 4x4 grid içinde 5'x5' hücre
    
    Referans noktası: 105°D, -1°G (Batavia datum)
    """
    parts = sheet_id.split('-')
    if len(parts) != 3:
        raise ValueError(f"Geçersiz sheet_id formatı: '{sheet_id}' (Beklenen: NN-ROMAN-xx)")

    col_str, row_roman, sub_code = parts
    col_num = int(col_str)
    row_num = roman_to_int(row_roman)

    # Büyük hücrenin sol-üst köşesi (Batavia datum)
    # Hollanda sistemi: sütun 32 = 105° doğudan başlıyor
    # Her sütun 20' = 0.3333°
    base_lon = 105.0 + (col_num - 32) * BIG_CELL
    
    # Satır 25 = -2° (güney enlem, negatif)
    # Aşağıya gidildikçe enlem azalır
    base_lat = -2.0 - (row_num - 25) * BIG_CELL
    
    # Alt kodu ayrıştır (örn: "ni" = n ve i kombinasyonu → 2 hücre birleşimi)
    coords = []
    for ch in sub_code:
        if ch not in SUBGRID_MAP:
            raise KeyError(f"Bilinmeyen alt hücre kodu: '{ch}' (sheet_id='{sheet_id}')")
        coords.append(SUBGRID_MAP[ch])

    xs = [c[0] for c in coords]
    ys = [c[1] for c in coords]

    # Alt hücre sınırları (Batavia datum)
    left_lon_bat  = base_lon + min(xs) * SUBGRID_SIZE
    right_lon_bat = base_lon + (max(xs) + 1) * SUBGRID_SIZE
    top_lat_bat   = base_lat - min(ys) * SUBGRID_SIZE
    bottom_lat_bat = base_lat - (max(ys) + 1) * SUBGRID_SIZE

    # Crop margin'lerini uygula
    # Marginlar orijinal görüntünün piksel yüzdesi olarak verilmiş
    # Gerçek kapsama alanını hesapla
    full_lon_span = right_lon_bat - left_lon_bat
    full_lat_span = top_lat_bat   - bottom_lat_bat  # pozitif değer

    # Marginlar kesilmeden ÖNCE tüm alanı kaplıyor, biz kırpıyoruz
    # margin_left = sol taraftan ne kadar kesildi (oran)
    # Yani crop görüntüsünün sol sınırı = orijinal sol + margin_left * toplam_genişlik
    crop_left_lon_bat   = left_lon_bat   + margin_left  * full_lon_span
    crop_right_lon_bat  = right_lon_bat  - margin_right * full_lon_span
    crop_top_lat_bat    = top_lat_bat    - margin_top    * full_lat_span
    crop_bottom_lat_bat = bottom_lat_bat + margin_bottom * full_lat_span

    # Batavia -> WGS 84 dönüşümü (4 köşe)
    # Sol-Üst
    tl_lon, tl_lat = batavia_to_wgs84(crop_left_lon_bat,  crop_top_lat_bat)
    # Sağ-Alt
    br_lon, br_lat = batavia_to_wgs84(crop_right_lon_bat, crop_bottom_lat_bat)
    # Sağ-Üst
    tr_lon, tr_lat = batavia_to_wgs84(crop_right_lon_bat, crop_top_lat_bat)
    # Sol-Alt
    bl_lon, bl_lat = batavia_to_wgs84(crop_left_lon_bat,  crop_bottom_lat_bat)

    return tl_lon, tl_lat, tr_lon, tr_lat, bl_lon, bl_lat, br_lon, br_lat


# ==============================================================================
# ANA İŞLEM
# ==============================================================================
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

df = pd.read_csv(CSV_PATH)
mevcut_dosyalar = set(os.listdir(INPUT_DIR))

print(f"Toplam harita: {len(df)}")
print(f"Giriş: {INPUT_DIR}")
print(f"Çıkış: {OUTPUT_DIR}")
print("-" * 60)

basarili = 0
atlanan  = []

for _, row in df.iterrows():
    sheet_id     = row['sheet_id']
    crop_filename = row.get('crop_filename', '')
    margin_left   = float(row['margin_left'])
    margin_right  = float(row['margin_right'])
    margin_top    = float(row['margin_top'])
    margin_bottom = float(row['margin_bottom'])

    # Dosyayı bul
    if isinstance(crop_filename, str) and crop_filename in mevcut_dosyalar:
        bulunan_dosya = crop_filename
    else:
        atlanan.append((sheet_id, "crop dosyası bulunamadı"))
        continue

    input_path  = os.path.join(INPUT_DIR,  bulunan_dosya)
    output_path = os.path.join(OUTPUT_DIR, f"{sheet_id}.tif")

    try:
        tl_lon, tl_lat, tr_lon, tr_lat, bl_lon, bl_lat, br_lon, br_lat = \
            hesapla_koordinatlar(sheet_id, margin_left, margin_right, margin_top, margin_bottom)

        # GDAL ile georeferencing
        # outputBounds = [left, bottom, right, top] (WGS 84)
        left_wgs84  = min(tl_lon, bl_lon)
        right_wgs84 = max(tr_lon, br_lon)
        top_wgs84   = max(tl_lat, tr_lat)
        bottom_wgs84 = min(bl_lat, br_lat)

        options = gdal.TranslateOptions(
            format        = "GTiff",
            outputBounds  = [left_wgs84, bottom_wgs84, right_wgs84, top_wgs84],
            outputSRS     = "EPSG:4326",
            creationOptions = ["COMPRESS=LZW", "TILED=YES"]
        )

        out_ds = gdal.Translate(output_path, input_path, options=options)
        out_ds = None
        basarili += 1
        print(f"  OK  {sheet_id:25} | Sol={left_wgs84:.5f} Ust={top_wgs84:.5f} Sag={right_wgs84:.5f} Alt={bottom_wgs84:.5f}")

    except Exception as e:
        atlanan.append((sheet_id, str(e)))
        print(f" HATA {sheet_id:25} | {e}")
        continue

print("\n" + "=" * 60)
print(f"Tamamlandı: {basarili} harita başarıyla işlendi")
if atlanan:
    print(f"Atlanan ({len(atlanan)}):")
    for s, r in atlanan:
        print(f"  - {s}: {r}")
