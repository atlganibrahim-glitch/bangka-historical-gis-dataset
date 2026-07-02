import os
import pandas as pd
from osgeo import gdal

gdal.UseExceptions()

INPUT_DIR = "."  
OUTPUT_DIR = "KIRPILMIS_RESIMLER"

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

df = pd.read_csv('bangka_dataset.csv')
mevcut_dosyalar = [f for f in os.listdir(INPUT_DIR) if f.endswith(('.jpg', '.tif', '.png'))]

print("Haritalarin lejantlari piksel verilerine gore kesiliyor...\n" + "-"*50)

basarili = 0
atlanan = []

for index, row in df.iterrows():
    sheet_id = row['sheet_id']
    image_idx = row['image_idx']
    
    bulunan_dosya = None
    aranan_baslangic = f"{int(image_idx):03d}_"
    for dosya in mevcut_dosyalar:
        if dosya.startswith(aranan_baslangic):
            bulunan_dosya = dosya
            break
            
    if not bulunan_dosya:
        continue
        
    input_path = os.path.join(INPUT_DIR, bulunan_dosya)
    output_path = os.path.join(OUTPUT_DIR, bulunan_dosya) 
    
    try:
        # Sütun isimlerindeki kırpılma ihtimaline karşı esnek kontrol
        ml = int(row['margin_left']) if 'margin_left' in df.columns else int(row['margin_lef'])
        mt = int(row['margin_top'])
        cw = int(row['crop_w'])
        ch = int(row['crop_h'])
        
        # Piksel penceresine göre kırpma ayarı
        options = gdal.TranslateOptions(srcWin=[ml, mt, cw, ch])
        out_ds = gdal.Translate(output_path, input_path, options=options)
        out_ds = None 
        
        basarili += 1
        print(f"Kırpıldı: {bulunan_dosya}")
        
    except Exception as e:
        atlanan.append((sheet_id, str(e)))

print("-" * 50)
print(f"1. Asama Bitti! {basarili} adet harita lejantlardan temizlendi ve '{OUTPUT_DIR}' klasorune kaydedildi.")