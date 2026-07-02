# -*- coding: utf-8 -*-
"""
Manuel Georeferanslama Kalibrasyon Karşılaştırıcı
===================================================
QGIS ile manuel georeferanslama yaptıktan sonra bu scripti çalıştırın.

Ne yapar:
  1. Manuel georeferanslanmış TIF dosyasının extent'ini okur
  2. Otomatik hesaplanan extent ile karşılaştırır
  3. Delta (fark) değerlerini bulur
  4. Bu farkı tüm haritalara uygulamak için "offset" katsayısını çıkarır

Kullanım:
  Manuel georeferanslama sonucu GeoTIFF'i aşağıdaki MANUEL_DOSYA
  değişkenine yazın, sonra scripti çalıştırın.
"""
import os
import pandas as pd
from osgeo import gdal
gdal.UseExceptions()

BASE     = os.path.dirname(os.path.abspath(__file__))
ESKI_DIR = os.path.join(BASE, "ESKI_KALIBRE_HARITALAR")
CSV_PATH = os.path.join(BASE, "bangka_dataset.csv")

# ============================================================
# 👇 BURAYA: Manuel georeferansladığınız sheet_id ve dosya yolu
SHEET_ID    = "31-XXIV-q"   # CSV'deki sheet_id değeri
MANUEL_DOSYA = r"D:\İşlenecekHaritalar\31-XXIV-q_manuel.tif"  # QGIS'in kaydettiği dosya
# ============================================================

def get_extent(path):
    """Bir TIF dosyasının extent'ini döndür: (left, top, right, bottom)"""
    ds = gdal.Open(path)
    if not ds:
        raise FileNotFoundError(f"Dosya açılamadı: {path}")
    gt = ds.GetGeoTransform()
    w, h = ds.RasterXSize, ds.RasterYSize
    left   = gt[0]
    top    = gt[3]
    right  = gt[0] + gt[1] * w
    bottom = gt[3] + gt[5] * h
    ds = None
    return left, top, right, bottom

def get_eski_extent(sheet_id):
    path = os.path.join(ESKI_DIR, sheet_id + ".tif")
    return get_extent(path)

def calc_crop_extent(sheet_id, df):
    """Mevcut script mantığıyla hesaplanan crop extent'i"""
    row = df[df['sheet_id'] == sheet_id].iloc[0]
    ml, mr, mt, mb = row['margin_left'], row['margin_right'], row['margin_top'], row['margin_bottom']
    
    el, et, er, eb = get_eski_extent(sheet_id)
    dlon = er - el
    dlat = et - eb  # pozitif
    
    cl = el + ml * dlon
    cr = er - mr * dlon
    ct = et - mt * dlat
    cb = eb + mb * dlat
    return cl, ct, cr, cb


def main():
    if not os.path.exists(MANUEL_DOSYA):
        print(f"HATA: Manuel georeferans dosyası bulunamadı!")
        print(f"  Beklenen: {MANUEL_DOSYA}")
        print(f"\n  QGIS Georeferencer'dan 'Save as...' yapın ve bu yola kaydedin.")
        print(f"  Ya da MANUEL_DOSYA değişkenini güncelleyin.")
        return

    df = pd.read_csv(CSV_PATH)

    print("=" * 65)
    print("GEOREFERANSLAMA KALİBRASYON KARŞILAŞTIRMASI")
    print("=" * 65)
    print(f"Harita: {SHEET_ID}")
    print()

    # Manuel sonuç
    m_left, m_top, m_right, m_bottom = get_extent(MANUEL_DOSYA)
    print(f"Manuel (QGIS) extent:")
    print(f"  Sol(W)  : {m_left:.6f}°")
    print(f"  Sağ(E)  : {m_right:.6f}°")
    print(f"  Kuzey(N): {m_top:.6f}°")
    print(f"  Güney(S): {m_bottom:.6f}°")
    print()

    # Otomatik hesap
    a_left, a_top, a_right, a_bottom = calc_crop_extent(SHEET_ID, df)
    print(f"Otomatik hesaplanan extent:")
    print(f"  Sol(W)  : {a_left:.6f}°")
    print(f"  Sağ(E)  : {a_right:.6f}°")
    print(f"  Kuzey(N): {a_top:.6f}°")
    print(f"  Güney(S): {a_bottom:.6f}°")
    print()

    # Delta (fark)
    d_left   = m_left   - a_left
    d_top    = m_top    - a_top
    d_right  = m_right  - a_right
    d_bottom = m_bottom - a_bottom
    
    print(f"Fark (Manuel - Otomatik):")
    print(f"  ΔSol   : {d_left:+.6f}°  ({d_left*111320:.1f} m)")
    print(f"  ΔSağ   : {d_right:+.6f}°  ({d_right*111320:.1f} m)")
    print(f"  ΔKuzey : {d_top:+.6f}°  ({d_top*111320:.1f} m)")
    print(f"  ΔGüney : {d_bottom:+.6f}°  ({d_bottom*111320:.1f} m)")
    print()

    # Ortalama offset (tutarlıysa tüm haritalara uygulanabilir)
    avg_lon_offset = (d_left + d_right) / 2
    avg_lat_offset = (d_top + d_bottom) / 2
    consistency_lon = abs(d_left - d_right)
    consistency_lat = abs(d_top - d_bottom)
    
    print(f"Ortalama offset (tüm haritalara uygulanacak):")
    print(f"  Boylam (lon): {avg_lon_offset:+.6f}°  ({avg_lon_offset*111320:.1f} m)")
    print(f"  Enlem  (lat): {avg_lat_offset:+.6f}°  ({avg_lat_offset*111320:.1f} m)")
    print()
    
    if consistency_lon < 0.001 and consistency_lat < 0.001:
        print("✅ Offset tutarlı - tüm haritalara uygulanabilir!")
        print()
        print("   crop_margin_geo.py için ekleyin:")
        print(f"   LON_OFFSET = {avg_lon_offset:.6f}")
        print(f"   LAT_OFFSET = {avg_lat_offset:.6f}")
    else:
        print("⚠️  Sol/Sağ veya Kuzey/Güney farkları tutarsız.")
        print("    Bu harita için farklı bir dönüşüm tipi gerekebilir.")
        print(f"    Lon farkı: {consistency_lon:.6f}°, Lat farkı: {consistency_lat:.6f}°")

    # ESKİ extent de göster
    print()
    el, et, er, eb = get_eski_extent(SHEET_ID)
    print(f"ESKİ referans extent:")
    print(f"  Sol={el:.6f}  Sağ={er:.6f}  Kuzey={et:.6f}  Güney={eb:.6f}")


if __name__ == "__main__":
    main()
