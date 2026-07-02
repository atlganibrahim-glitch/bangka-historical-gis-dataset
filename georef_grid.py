# -*- coding: utf-8 -*-
"""
Grid Tabanlı Otomatik Georeferanslama — ±100m Hedef
=====================================================
Yöntem:
  1. Haritadaki 1' koordinat grid çizgilerini gradient ile tespit et
  2. ESKİ tahmini konumundan hangi 1' değerine karşılık geldiğini ata
  3. Kesişim noktaları → GCP listesi
  4. Batavia→WGS84 datum düzeltmesi uygula (+0.00163° lon, -0.000255° lat)
  5. CreateCopy + SetGCPs + PolynomialOrder=1 → kesin georef

Beklenen doğruluk: ±50-100m (harita survey doğruluğuna bağlı)
"""
import os, math
import numpy as np
import pandas as pd
from osgeo import gdal, osr
gdal.UseExceptions()

BASE      = os.path.dirname(os.path.abspath(__file__))
ESKI_DIR  = os.path.join(BASE, 'GEOREF_FINAL_STANDARD_164')
CSV_PATH  = os.path.join(BASE, 'bangka_dataset_v2.csv')
OUT_DIR   = os.path.join(BASE, 'GEOREF_GRID')
os.makedirs(OUT_DIR, exist_ok=True)

# Batavia → WGS84 datum düzeltmesi (Bangka bölgesi için hesaplanmış)
DATUM_DLON = +0.001630   # +181m Doğu
DATUM_DLAT = -0.000255   # -28m Güney

# Hedef projeksiyon
SRS_WGS84 = osr.SpatialReference()
SRS_WGS84.ImportFromEPSG(4326)
WKT_WGS84 = SRS_WGS84.ExportToWkt()

# ─── Gradient tabanlı grid çizgisi tespiti ───────────────────────────────────

def read_gray_full(path):
    """Tüm kanalların ortalaması olarak gri görüntü (tam çözünürlük)."""
    ds = gdal.Open(path)
    if ds is None:
        raise FileNotFoundError(path)
    W, H = ds.RasterXSize, ds.RasterYSize
    nb = ds.RasterCount
    if nb >= 3:
        r = ds.GetRasterBand(1).ReadAsArray().astype(np.float32)
        g = ds.GetRasterBand(2).ReadAsArray().astype(np.float32)
        b = ds.GetRasterBand(3).ReadAsArray().astype(np.float32)
        gray = (r + g + b) / 3.0
    else:
        gray = ds.GetRasterBand(1).ReadAsArray().astype(np.float32)
    ds = None
    return gray, W, H


def sobel_row(gray):
    """Her satırdaki yatay kenar gücü (dikey Sobel filtresi toplamı)."""
    # Basit dikey Sobel: [-1, 0, 1] sütunlar
    ky = np.array([-1.0, 0.0, 1.0])
    # Her satır için gradient toplamı
    rows = gray.shape[0]
    # Dikey fark: |I[i+1] - I[i-1]| / 2
    top = np.vstack([gray[0:1], gray[:-1]])
    bot = np.vstack([gray[1:], gray[-1:]])
    grad_y = np.abs(bot - top)
    # Her satırda toplam gradient gücü (yatay entegrasyon)
    return grad_y.mean(axis=1)


def sobel_col(gray):
    """Her sütundaki dikey kenar gücü."""
    left  = np.hstack([gray[:, 0:1], gray[:, :-1]])
    right = np.hstack([gray[:, 1:], gray[:, -1:]])
    grad_x = np.abs(right - left)
    return grad_x.mean(axis=0)


def cluster_peaks(arr, gap=5):
    """Ardışık yüksek değerleri grupla → merkez döndür."""
    if len(arr) == 0:
        return np.array([])
    centers = []
    group = [arr[0]]
    for v in arr[1:]:
        if v - group[-1] <= gap:
            group.append(v)
        else:
            centers.append(int(round(np.mean(group))))
            group = [v]
    centers.append(int(round(np.mean(group))))
    return np.array(centers)


def detect_grid_lines(crop_path, scale=2):
    """
    Gradient tabanlı grid çizgisi tespiti.
    scale: bellek için indirgenme katsayısı (1=tam, 2=yarı, 4=çeyrek)
    """
    ds = gdal.Open(crop_path)
    W, H = ds.RasterXSize, ds.RasterYSize
    nw, nh = max(1, W//scale), max(1, H//scale)
    nb = ds.RasterCount
    if nb >= 3:
        r = ds.GetRasterBand(1).ReadAsArray(0,0,W,H,nw,nh).astype(np.float32)
        g = ds.GetRasterBand(2).ReadAsArray(0,0,W,H,nw,nh).astype(np.float32)
        b = ds.GetRasterBand(3).ReadAsArray(0,0,W,H,nw,nh).astype(np.float32)
        gray = (r + g + b) / 3.0
    else:
        gray = ds.GetRasterBand(1).ReadAsArray(0,0,W,H,nw,nh).astype(np.float32)
    ds = None

    # Gradient profilleri
    row_grad = sobel_row(gray)
    col_grad = sobel_col(gray)

    # k*std eşiği ile pik bul
    def find_peaks(arr, k=2.5):
        thresh = arr.mean() + k * arr.std()
        cands = np.where(arr > thresh)[0]
        return cluster_peaks(cands, gap=3)

    row_peaks_s = find_peaks(row_grad, k=2.5)
    col_peaks_s = find_peaks(col_grad, k=2.5)

    # Tam çözünürlüğe çevir
    row_peaks = (row_peaks_s * scale + scale // 2).clip(0, H - 1)
    col_peaks = (col_peaks_s * scale + scale // 2).clip(0, W - 1)

    return row_peaks, col_peaks, W, H


# ─── GCP atama ───────────────────────────────────────────────────────────────

ONE_MIN = 1.0 / 60.0   # 1 dakika = 0.01667°


def assign_arc_minutes(pixel_positions, total_pixels, coord_min, coord_max,
                        is_lat=True):
    """
    Piksel pozisyonlarına en yakın tam dakika koordinatını ata.
    
    is_lat=True: y ekseninde, küçük piksel = kuzey (büyük koordinat)
    is_lat=False: x ekseninde, küçük piksel = batı (küçük koordinat)
    
    Döner: list of (pixel, exact_coord_in_degrees)
    """
    def px_to_coord(px):
        frac = px / total_pixels
        if is_lat:
            # Y arttıkça lat azalır (güneye gider)
            return coord_min + frac * (coord_max - coord_min)
        else:
            return coord_min + frac * (coord_max - coord_min)

    results = []
    for px in pixel_positions:
        approx = px_to_coord(px)
        # En yakın tam dakikaya yuvarlama
        exact_min = round(approx / ONE_MIN)
        exact_coord = exact_min * ONE_MIN
        # Atama makul mi? (ESKİ aralığın içinde olmalı + 1' tolerans)
        lo = min(coord_min, coord_max) - ONE_MIN * 1.5
        hi = max(coord_min, coord_max) + ONE_MIN * 1.5
        if lo <= exact_coord <= hi:
            results.append((int(px), float(exact_coord)))

    return results


def make_gcps(row_assignments, col_assignments, W, H, crop_N, crop_S, crop_W, crop_E):
    """
    Yatay (enlem) ve dikey (boylam) çizgilerin kesişiminden GCP'ler üret.
    Batavia→WGS84 datum düzeltmesi bu aşamada uygulanır.
    """
    gcps = []
    for (y_px, lat) in row_assignments:
        for (x_px, lon) in col_assignments:
            # Datum düzeltmesi (Batavia → WGS84)
            lon_wgs = lon + DATUM_DLON
            lat_wgs = lat + DATUM_DLAT
            gcp = gdal.GCP(lon_wgs, lat_wgs, 0.0, float(x_px), float(y_px))
            gcps.append(gcp)
    return gcps


# ─── Ana işlev ───────────────────────────────────────────────────────────────

def process_sheet(sheet_id, crop_path, eski_path, output_path,
                  ml=0.07, mr=0.063, mt=0.078, mb=0.207):
    """
    Bir harita sayfasını grid tabanlı georeferanslama ile işle.
    Döner: (gcp_count, rmse) veya None (başarısız)
    """
    # ESKI tahmini extent
    ds_e = gdal.Open(eski_path)
    if not ds_e:
        return None
    gt = ds_e.GetGeoTransform()
    ew, eh = ds_e.RasterXSize, ds_e.RasterYSize
    eski_W = gt[0]
    eski_N = gt[3]
    eski_E = gt[0] + gt[1] * ew
    eski_S = gt[3] + gt[5] * eh
    ds_e = None

    # Crop'un gercek cografik kapsami (margin degerlerinden)
    eski_lon_span = eski_E - eski_W
    eski_lat_span = eski_N - eski_S   # pozitif: N > S
    crop_W = eski_W + ml * eski_lon_span
    crop_E = eski_E - mr * eski_lon_span
    crop_N = eski_N - mt * eski_lat_span  # uste dogru kesilmis
    crop_S = eski_S + mb * eski_lat_span  # alta dogru kesilmis

    # Crop grid cizgilerini tespit et
    row_px, col_px, CW, CH = detect_grid_lines(crop_path, scale=2)

    if len(row_px) < 2 or len(col_px) < 2:
        return None

    # Piksel -> yaklasik koordinat -> tam dakika ata
    # Crop boyutlari uzerinden eslestir (ESKi degil, crop kapsami!)
    lat_gcps = assign_arc_minutes(row_px, CH, crop_N, crop_S, is_lat=True)
    lon_gcps = assign_arc_minutes(col_px, CW, crop_W, crop_E, is_lat=False)

    if len(lat_gcps) < 2 or len(lon_gcps) < 2:
        return None

    # GCP'ler oluştur
    gcps = make_gcps(lat_gcps, lon_gcps, CW, CH,
                     eski_N, eski_S, eski_W, eski_E)

    if len(gcps) < 4:
        return None

    # GeoTIFF oluştur
    ds_src = gdal.Open(crop_path)
    if not ds_src:
        return None

    driver = gdal.GetDriverByName('GTiff')
    co = ['COMPRESS=LZW', 'TILED=YES', 'BIGTIFF=IF_NEEDED']
    ds_out = driver.CreateCopy(output_path, ds_src, strict=0, options=co)
    ds_out.SetGCPs(gcps, WKT_WGS84)

    # Polynomial order 1 (affine) ile GeoTransform hesapla ve uygula
    gdal.GCPsToGeoTransform_internal = None  # temizle
    gt_new = gdal.GCPsToGeoTransform(gcps)
    if gt_new:
        ds_out.SetGeoTransform(gt_new)
        ds_out.SetProjection(WKT_WGS84)

    ds_out = None
    ds_src = None

    # RMSE hesapla
    if gt_new:
        errors = []
        for gcp in gcps:
            lon_est = gt_new[0] + gcp.GCPPixel * gt_new[1] + gcp.GCPLine * gt_new[2]
            lat_est = gt_new[3] + gcp.GCPPixel * gt_new[4] + gcp.GCPLine * gt_new[5]
            dx = (lon_est - gcp.GCPX) * 111320 * abs(math.cos(math.radians(gcp.GCPY)))
            dy = (lat_est - gcp.GCPY) * 111320
            errors.append(math.sqrt(dx**2 + dy**2))
        rmse = math.sqrt(sum(e**2 for e in errors) / len(errors))
    else:
        rmse = -1

    return len(gcps), round(rmse, 2)


# ─── Batch işleme ────────────────────────────────────────────────────────────

def main():
    df = pd.read_csv(CSV_PATH)
    eski_dosyalar = set(os.listdir(ESKI_DIR))

    basarili, atlanan = 0, []

    print('GRİD TABANLI GEOREFERANsLAMA')
    print('Hedef: ±100m (Bangka 1932 haritaları)')
    print('=' * 70)

    for _, row in df.iterrows():
        sid  = row['sheet_id']
        cf   = str(row.get('crop_filename', ''))

        eski_path  = os.path.join(ESKI_DIR, sid + '.tif')
        crop_path  = os.path.join(BASE, cf)
        out_path   = os.path.join(OUT_DIR, sid + '.tif')

        if not os.path.exists(eski_path):
            atlanan.append((sid, 'ESKI yok'))
            continue
        if not os.path.exists(crop_path):
            atlanan.append((sid, 'Crop yok'))
            continue

        try:
            result = process_sheet(sid, crop_path, eski_path, out_path)
            if result is None:
                atlanan.append((sid, 'Grid tespit edilemedi'))
                print(f'  UYARI {sid}: grid < 4 GCP')
            else:
                gcp_n, rmse = result
                status = '✓' if rmse < 100 else '!'
                print(f'  {status} {sid:25} | GCP={gcp_n:2d} | RMSE={rmse:6.1f}m')
                basarili += 1
        except Exception as e:
            atlanan.append((sid, str(e)))
            print(f'  ✗ HATA {sid}: {e}')

    print()
    print('=' * 70)
    print(f'Tamamlandı: {basarili}/{len(df)} harita')
    print(f'Çıktı: {OUT_DIR}')
    if atlanan:
        print(f'\nAtlanan {len(atlanan)} harita:')
        for s, r in atlanan:
            print(f'  ✗ {s}: {r}')


if __name__ == '__main__':
    main()
