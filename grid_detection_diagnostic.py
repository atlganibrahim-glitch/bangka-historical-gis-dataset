# -*- coding: utf-8 -*-
"""
Grid Tabanlı Otomatik Georeferanslama - Teşhis
===============================================
Haritadaki baskılı 1' koordinat grid çizgilerini tespit eder.
Bu çizgilerin piksel konumları + bilinen koordinatları → kesin GCP'ler

Yöntem:
  1. Yatay koyu çizgileri tespit et (enlem gridleri)
  2. Dikey koyu çizgileri tespit et (boylam gridleri)
  3. ESKI yaklaşık konumundan hangi 1' değerine karşılık geldiğini bul
  4. GCP listesi oluştur → gdal.GCP → Affine dönüşüm
"""
import os
import numpy as np
from osgeo import gdal, osr
gdal.UseExceptions()

BASE     = r'D:\İşlenecekHaritalar'
ESKI_DIR = os.path.join(BASE, 'GEOREF_FINAL_STANDARD_164')

# Test haritası
CROP_FILE  = os.path.join(BASE, 'crop_000.jpg')
SHEET_ID   = '31-XXIV-q'
ESKI_FILE  = os.path.join(ESKI_DIR, SHEET_ID + '.tif')


def get_eski_extent(eski_path):
    ds = gdal.Open(eski_path)
    gt = ds.GetGeoTransform()
    w, h = ds.RasterXSize, ds.RasterYSize
    return gt[0], gt[3], gt[0]+gt[1]*w, gt[3]+gt[5]*h


def detect_grid_lines(img_path, dark_threshold=100, min_coverage=0.20, scale=4):
    """
    Haritadaki grid çizgilerini tespit et.
    
    dark_threshold: bu değerin altındaki piksel = koyu
    min_coverage: bir çizginin satır/sütun boyunca kaplama oranı (0-1)
    
    Döndürür: (row_positions, col_positions) - tam çözünürlükte piksel indexleri
    """
    ds = gdal.Open(img_path)
    W, H = ds.RasterXSize, ds.RasterYSize
    nw, nh = W // scale, H // scale

    nb = ds.RasterCount
    if nb >= 3:
        r = ds.GetRasterBand(1).ReadAsArray(0,0,W,H,nw,nh).astype(np.float32)
        g = ds.GetRasterBand(2).ReadAsArray(0,0,W,H,nw,nh).astype(np.float32)
        b = ds.GetRasterBand(3).ReadAsArray(0,0,W,H,nw,nh).astype(np.float32)
        gray = 0.299*r + 0.587*g + 0.114*b
    else:
        gray = ds.GetRasterBand(1).ReadAsArray(0,0,W,H,nw,nh).astype(np.float32)
    ds = None

    dark = gray < dark_threshold

    # Satır bazında: kaçı koyu?
    row_cov = dark.mean(axis=1)
    # Sütun bazında: kaçı koyu?
    col_cov = dark.mean(axis=0)

    # Grid çizgisi = min_coverage'dan fazla koyu piksel içeren satır/sütun
    row_lines_s = np.where(row_cov >= min_coverage)[0]
    col_lines_s = np.where(col_cov >= min_coverage)[0]

    # Gruplay: ardışık piksel grubunun ortasını al
    def cluster_centers(arr, gap=3):
        if len(arr) == 0:
            return np.array([])
        centers = []
        group = [arr[0]]
        for i in arr[1:]:
            if i - group[-1] <= gap:
                group.append(i)
            else:
                centers.append(int(np.mean(group)))
                group = [i]
        centers.append(int(np.mean(group)))
        return np.array(centers)

    row_centers = cluster_centers(row_lines_s)
    col_centers = cluster_centers(col_lines_s)

    # Tam çözünürlüğe çevir
    row_full = row_centers * scale + scale // 2
    col_full = col_centers * scale + scale // 2

    return row_full, col_full, W, H


def assign_minute_coords(pixel_positions, extent_min, extent_max, is_lat=True):
    """
    Piksel pozisyonlarına en yakın tam dakika koordinatını ata.
    
    pixel_positions: piksel indexleri (0 = sol/üst)
    extent_min, extent_max: ESKI'den alınan tahmini koordinat aralığı
    is_lat: True=enlem (y, üstten aşağı azalır), False=boylam (x, soldan sağa artar)
    """
    N = len(pixel_positions)
    if N == 0:
        return []

    total_px = None  # dışarıdan verilecek

    results = []
    for px in pixel_positions:
        # Piksel → koordinat (yaklaşık)
        # image_height or width verilmesi gerekiyor, basitçe extent kullan
        # Burada sadece yaklaşık koordinatı hesapla
        results.append(px)
    return results


def find_grid_gcp(crop_path, eski_path):
    """
    Crop haritasındaki grid çizgilerinden GCP'ler üret.
    """
    # ESKI tahmini extent
    el, et, er, eb = get_eski_extent(eski_path)

    # Grid çizgilerini tespit et
    # Farklı eşik değerleri dene
    for threshold in [80, 100, 120]:
        row_px, col_px, W, H = detect_grid_lines(crop_path, dark_threshold=threshold,
                                                   min_coverage=0.15)
        if len(row_px) >= 2 and len(col_px) >= 2:
            break

    print(f'  Piksel boyutu     : {W} x {H}')
    print(f'  Eşik değeri       : {threshold}')
    print(f'  Yatay grid çizgi  : {len(row_px)} adet  @ piksel={row_px.tolist()}')
    print(f'  Dikey grid çizgi  : {len(col_px)} adet  @ piksel={col_px.tolist()}')

    if len(row_px) < 2 or len(col_px) < 2:
        print('  UYARI: Yeterli grid çizgisi bulunamadı!')
        return None

    # Piksel → koordinat (ESKI tabanlı yaklaşık)
    # Enlem: üst=et, alt=eb, ters yön (y artar = lat azalır)
    def px_to_lat(y_px):
        return et + (y_px / H) * (eb - et)

    def px_to_lon(x_px):
        return el + (x_px / W) * (er - el)

    print()
    print('  Grid çizgisi koordinatları (ESKI tabanlı yaklaşık):')
    print('  Yatay (enlem):')
    lat_approx = []
    for y in row_px:
        lat = px_to_lat(y)
        lat_min = round(lat * 60)  # en yakın tam dakika
        lat_exact = lat_min / 60.0
        lat_approx.append(lat_exact)
        print(f'    y={y:5d}px  →  lat_approx={lat:.6f}°  →  lat_1min={lat_exact:.6f}°  ({lat_min//60}°{abs(lat_min)%60}\')')

    print('  Dikey (boylam):')
    lon_approx = []
    for x in col_px:
        lon = px_to_lon(x)
        lon_min = round(lon * 60)  # en yakın tam dakika
        lon_exact = lon_min / 60.0
        lon_approx.append(lon_exact)
        print(f'    x={x:5d}px  →  lon_approx={lon:.6f}°  →  lon_1min={lon_exact:.6f}°  ({lon_min//60}°{abs(lon_min)%60}\')')

    # GCP oluştur: tüm kesişim noktaları
    print()
    print('  GCP kesişim noktaları:')
    gcps = []
    for i, y_px in enumerate(row_px):
        for j, x_px in enumerate(col_px):
            lat = lat_approx[i]
            lon = lon_approx[j]
            gcp = gdal.GCP(lon, lat, 0, float(x_px), float(y_px))
            gcps.append(gcp)
            if i == 0 and j < 3:  # sadece ilk birkaçını göster
                print(f'    ({x_px}px, {y_px}px) → ({lon:.6f}°, {lat:.6f}°)')

    print(f'  Toplam GCP: {len(gcps)}')
    return gcps, W, H


# ─── ÇALIŞTIR ───────────────────────────────────────────────────────────────
print('=' * 60)
print('GRİD TABANLI GEOREFERANs TEŞHİSİ')
print('=' * 60)
print(f'Harita: {SHEET_ID}')
print()

result = find_grid_gcp(CROP_FILE, ESKI_FILE)

if result:
    gcps, W, H = result
    print()
    print('✅ Grid GCP\'leri başarıyla oluşturuldu.')
    print('   Sonraki adım: Bu GCP\'ler ile affine dönüşüm uygula.')
else:
    print('❌ Grid tespit edilemedi — farklı renk kanalı veya eşik deneyin.')
