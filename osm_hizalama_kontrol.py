# -*- coding: utf-8 -*-
"""
OSM Hizalama Kontrol Scripti
=============================
QGIS konsolunda çalıştırın.

Yapılan işlem:
  Bilinen bir OSM noktasının (yol kavşağı, kıyı koordinatı vb.)
  harita üzerindeki görünen koordinatı ile gerçek WGS84 koordinatını
  karşılaştırarak sistematik kaymayı hesaplar.

Kullanım:
  1. QGIS'de bir harita katmanını açın (CROP_KALIBRE_HARITALAR)
  2. OSM'de tanımlayabileceğiniz bir noktayı bulun
     (örn: bir yol kavşağı, köy, kıyı burnu)
  3. QGIS koordinat çubuğundan hem haritada hem OSM'de
     o noktanın koordinatını okuyun
  4. Aşağıdaki değerleri doldurun ve çalıştırın
"""

# === BURAYA GİRİN ===
# Harita üzerinde bir nokta seçin; QGIS koordinat çubuğunda
# imleç o noktanın üzerindeyken okuyun:

# Haritada göründüğü yer (CROP_KALIBRE üzerinde)
HARITA_LON = 106.123  # örnek — değiştirin!
HARITA_LAT = -2.456   # örnek — değiştirin!

# Aynı fiziksel noktanın OSM/Google'daki gerçek koordinatı
# (OSM'de sağ tık → "Bu konumu kopyala" veya koordinat barından)
GERCEK_LON = 106.125  # örnek — değiştirin!
GERCEK_LAT = -2.453   # örnek — değiştirin!
# ====================

delta_lon = GERCEK_LON - HARITA_LON
delta_lat = GERCEK_LAT - HARITA_LAT

# Metreye çevir (yaklaşık, Bangka enleminde)
M_PER_DEG_LON = 111320 * abs(import_cos(-2.0 * 3.14159 / 180))  # cos(-2°)
M_PER_DEG_LAT = 111320

# Basit hesap
import math
cos_lat = math.cos(math.radians(HARITA_LAT))
dx_m = delta_lon * 111320 * cos_lat
dy_m = delta_lat * 111320

print("=" * 55)
print("OSM HIZALAma KONTROLÜ")
print("=" * 55)
print(f"  Haritadaki koordinat : {HARITA_LON:.6f}, {HARITA_LAT:.6f}")
print(f"  Gerçek koordinat     : {GERCEK_LON:.6f}, {GERCEK_LAT:.6f}")
print()
print(f"  ΔLon : {delta_lon:+.6f}° ({dx_m:+.1f} m Doğu)")
print(f"  ΔLat : {delta_lat:+.6f}° ({dy_m:+.1f} m Kuzey)")
print()
print(f"  Toplam kayma : {math.sqrt(dx_m**2 + dy_m**2):.1f} m")
yön = math.degrees(math.atan2(dx_m, dy_m))
print(f"  Yön          : {yön:.1f}° (0=K, 90=D, 180=G, 270=B)")
print()
if abs(dx_m) < 100 and abs(dy_m) < 100:
    print("✅ Kayma < 100m — Georeferanslama yeterli iyi!")
elif abs(dx_m) < 500 and abs(dy_m) < 500:
    print("⚠️  Kayma 100-500m arasında — Datum farkı veya georeflama hatası")
else:
    print("❌ Kayma > 500m — Büyük hata, datum dönüşümü gerekebilir")
