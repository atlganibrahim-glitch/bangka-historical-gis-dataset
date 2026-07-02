# -*- coding: utf-8 -*-
import os, sys
from osgeo import gdal
gdal.UseExceptions()

KLASOR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "GEOREF_FINAL_STANDARD_164")

# İlk birkaç GeoTIFF'in koordinatlarını kontrol et
dosyalar = sorted([f for f in os.listdir(KLASOR) if f.endswith('.tif')])[:5]

for dosya in dosyalar:
    yol = os.path.join(KLASOR, dosya)
    ds = gdal.Open(yol)
    if ds:
        gt = ds.GetGeoTransform()
        w = ds.RasterXSize
        h = ds.RasterYSize
        sol  = gt[0]
        ust  = gt[3]
        sag  = gt[0] + gt[1]*w
        alt  = gt[3] + gt[5]*h
        print(f"{dosya}: Sol={sol:.5f}, Ust={ust:.5f}, Sag={sag:.5f}, Alt={alt:.5f}")
        ds = None
    else:
        print(f"{dosya}: ACILAMADI")
