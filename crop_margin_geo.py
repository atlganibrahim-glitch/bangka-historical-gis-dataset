# -*- coding: utf-8 -*-
"""
Bangka Haritaları - Crop Margin Düzeltmeli Georeferencing
==========================================================
Bu script ESKİ kalibre haritaları referans alır:
- ESKİ haritalar = orijinal (lejantlı) haritalar, doğru konumda
- YENİ haritalar = crop (kenar kesilmiş) haritalar
  
Crop haritaları için koordinatlar şu şekilde hesaplanır:
  ESKİ harita extent'i + margin düzeltmesi = CROP haritasının extent'i

Bu yöntem:
- Mevcut kalibrasyonu korur
- Sadece kesilmiş kenar bilgisini koordinata yansıtır
- Datum meselesini ESKİ haritadan miras alır

Kullanım: QGIS Python konsolunda veya terminalde çalıştırın.
"""
import os
import pandas as pd
from osgeo import gdal, osr

gdal.UseExceptions()

BASE      = os.path.dirname(os.path.abspath(__file__))
ESKI_DIR  = os.path.join(BASE, "GEOREF_FINAL_STANDARD_164")
OUTPUT_DIR = os.path.join(BASE, "GEOREF_FINAL_STANDARD_164")
CSV_PATH  = os.path.join(BASE, "bangka_dataset_v2.csv")

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

df = pd.read_csv(CSV_PATH)
mevcut_crop = set(os.listdir(BASE))
eski_dosyalar = set(os.listdir(ESKI_DIR))

print(f"ESKİ kalibre klasörü: {ESKI_DIR}")
print(f"Çıkış klasörü: {OUTPUT_DIR}")
print(f"Toplam kayıt: {len(df)}")
print("-" * 70)

basarili = 0
atlanan  = []

for _, row in df.iterrows():
    sheet_id      = row['sheet_id']
    crop_filename = row.get('crop_filename', '')
    
    # Margin değerleri (orijinal görüntüdeki oran olarak)
    # Örn: margin_left=0.07 → orijinal görüntünün %7'si sol kenardan kesilmiş
    ml = float(row['margin_left'])
    mr = float(row['margin_right'])
    mt = float(row['margin_top'])
    mb = float(row['margin_bottom'])

    # Dosyaları kontrol et
    eski_dosya = f"{sheet_id}.tif"
    if eski_dosya not in eski_dosyalar:
        atlanan.append((sheet_id, f"ESKİ harita bulunamadı: {eski_dosya}"))
        continue
    
    if not isinstance(crop_filename, str) or crop_filename not in mevcut_crop:
        atlanan.append((sheet_id, f"Crop dosyası bulunamadı: {crop_filename}"))
        continue

    eski_path  = os.path.join(ESKI_DIR, eski_dosya)
    crop_path  = os.path.join(BASE, crop_filename)
    output_path = os.path.join(OUTPUT_DIR, f"{sheet_id}.tif")

    try:
        # ESKİ haritanın extent'ini al
        ds_eski = gdal.Open(eski_path)
        if not ds_eski:
            atlanan.append((sheet_id, "ESKİ dosya açılamadı"))
            continue
        
        gt = ds_eski.GetGeoTransform()
        eski_w = ds_eski.RasterXSize
        eski_h = ds_eski.RasterYSize
        proj   = ds_eski.GetProjection()
        
        eski_left   = gt[0]
        eski_top    = gt[3]
        eski_right  = gt[0] + gt[1] * eski_w
        eski_bottom = gt[3] + gt[5] * eski_h
        ds_eski = None
        
        # ESKİ harita tam extent'i
        eski_lon_span = eski_right  - eski_left
        eski_lat_span = eski_top    - eski_bottom  # pozitif değer
        
        # Crop haritasının margin'leri ESKİ haritanın piksel oranına göre
        # NOT: ESKİ harita = lejantlı orijinal (tam sayfa)
        #      Crop harita = lejant kesilmiş versiyon
        # Margin değerleri orijinal haritanın piksel boyutuna göredir
        
        crop_left   = eski_left   + ml * eski_lon_span
        crop_right  = eski_right  - mr * eski_lon_span
        crop_top    = eski_top    - mt * eski_lat_span
        crop_bottom = eski_bottom + mb * eski_lat_span

        # Crop piksel boyutlarını oku
        ds_crop = gdal.Open(crop_path)
        if not ds_crop:
            atlanan.append((sheet_id, "Crop dosyası açılamadı"))
            continue
        cols = ds_crop.RasterXSize
        rows = ds_crop.RasterYSize

        # GeoTransform: (ulx, px_width, 0, uly, 0, px_height)
        # uly = kuzey sınırı (crop_top), px_height negatif (güneye doğru)
        px_x = (crop_right - crop_left) / cols
        px_y = (crop_bottom - crop_top) / rows  # negatif
        gt_new = (crop_left, px_x, 0.0, crop_top, 0.0, px_y)

        srs = osr.SpatialReference()
        srs.ImportFromEPSG(4326)

        # Piksel verisini kopyala, koordinatı doğrudan ata (mevcut yanlış
        # georef'i devre dışı bırakır — reprojeksiyon olmaz)
        driver = gdal.GetDriverByName("GTiff")
        co = ["COMPRESS=LZW", "TILED=YES", "BIGTIFF=IF_NEEDED"]
        out_ds = driver.CreateCopy(output_path, ds_crop, strict=0,
                                   options=co)
        out_ds.SetGeoTransform(gt_new)
        out_ds.SetProjection(srs.ExportToWkt())
        out_ds = None
        ds_crop = None
        basarili += 1

        print(f"OK  {sheet_id:25} | Sol={crop_left:.5f} Ust={crop_top:.5f} "
              f"Sag={crop_right:.5f} Alt={crop_bottom:.5f}")

    except Exception as e:
        atlanan.append((sheet_id, str(e)))
        print(f"HATA {sheet_id}: {e}")
        continue

print("\n" + "=" * 70)
print(f"Tamamlandı: {basarili}/{len(df)} harita başarıyla işlendi")
if atlanan:
    print(f"\nAtlanan {len(atlanan)} harita:")
    for s, r in atlanan:
        print(f"  ✗ {s}: {r}")
else:
    print("Tüm haritalar başarıyla işlendi!")
