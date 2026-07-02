# -*- coding: utf-8 -*-
"""
ESKİ (lejantlı) ve YENİ (crop) GeoTIFF koordinatlarini karsilastir.
Aradaki offset farkini hesapla.
"""
import os
from osgeo import gdal
gdal.UseExceptions()

BASE = os.path.dirname(os.path.abspath(__file__))
ESKI = os.path.join(BASE, "GEOREF_FINAL_STANDARD_164")
YENI = os.path.join(BASE, "GEOREF_FINAL_STANDARD_164")

eski_dosyalar = set(f for f in os.listdir(ESKI) if f.endswith('.tif') and not f.endswith('.aux.xml'))

print(f"{'Sheet':25} {'ESKI Sol':>12} {'ESKI Ust':>12} {'YENI Sol':>12} {'YENI Ust':>12} {'dLon':>10} {'dLat':>10}")
print("-"*100)

offsets_lon = []
offsets_lat = []

for dosya in sorted(eski_dosyalar):
    eski_yol = os.path.join(ESKI, dosya)
    yeni_yol = os.path.join(YENI, dosya)
    
    if not os.path.exists(yeni_yol):
        continue
    
    ds_e = gdal.Open(eski_yol)
    ds_y = gdal.Open(yeni_yol)
    
    if not ds_e or not ds_y:
        continue
    
    gt_e = ds_e.GetGeoTransform()
    gt_y = ds_y.GetGeoTransform()
    
    eski_sol = gt_e[0]
    eski_ust = gt_e[3]
    yeni_sol = gt_y[0]
    yeni_ust = gt_y[3]
    
    d_lon = eski_sol - yeni_sol
    d_lat = eski_ust - yeni_ust
    
    offsets_lon.append(d_lon)
    offsets_lat.append(d_lat)
    
    print(f"{dosya:25} {eski_sol:12.6f} {eski_ust:12.6f} {yeni_sol:12.6f} {yeni_ust:12.6f} {d_lon:10.6f} {d_lat:10.6f}")
    
    ds_e = None
    ds_y = None

if offsets_lon:
    print("\n" + "="*100)
    print(f"Ortalama LON farki: {sum(offsets_lon)/len(offsets_lon):+.6f} derece")
    print(f"Ortalama LAT farki: {sum(offsets_lat)/len(offsets_lat):+.6f} derece")
    print(f"Min/Max LON farki:  {min(offsets_lon):.6f} / {max(offsets_lon):.6f}")
    print(f"Min/Max LAT farki:  {min(offsets_lat):.6f} / {max(offsets_lat):.6f}")
