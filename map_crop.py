import pandas as pd
from PIL import Image
import cv2
import numpy as np
import os

# --- AYARLAR ---
csv_path = 'bangka_dataset.csv'
input_dir = '.'  # Haritalar bu klasörde
output_dir = 'recovered_maps'
os.makedirs(output_dir, exist_ok=True)

# Veri setini oku
df = pd.read_csv(csv_path)

print("🚀 Paint'ten Gelen Kusursuz Oranla Kırpma Başlıyor...")
print("💡 Alt marj %15.89 olarak ayarlandı. Hem ada kurtulacak hem lejant gidecek!\n")

basarili = 0

for index, row in df.iterrows():
    img_name = row['filename']
    crop_name = row['crop_filename']
    
    img_path = os.path.join(input_dir, img_name)
    if not os.path.exists(img_path):
        # Büyük/küçük harf varyasyonlarını kontrol et
        if os.path.exists(os.path.join(input_dir, img_name.lower())):
            img_path = os.path.join(input_dir, img_name.lower())
        elif os.path.exists(os.path.join(input_dir, img_name.upper())):
            img_path = os.path.join(input_dir, img_name.upper())
        else:
            continue

    # 1. GÜVENLİ OKUMA (Türkçe karakterler için)
    try:
        stream = open(img_path, "rb")
        bytes_data = bytearray(stream.read())
        numpyarray = np.asarray(bytes_data, dtype=np.uint8)
        cv2_img = cv2.imdecode(numpyarray, cv2.IMREAD_UNCHANGED)
        stream.close()
    except Exception as e:
        print(f"❌ Okuma hatası: {img_name} - {e}")
        continue

    if cv2_img is None:
        print(f"❌ Okunamadı (Dosya bozuk olabilir): {img_name}")
        continue

    # OpenCV'yi PIL'e çevir (Kırpma işlemi için)
    cv2_img_rgb = cv2.cvtColor(cv2_img, cv2.COLOR_BGR2RGB)
    img = Image.fromarray(cv2_img_rgb)

    # 2. HİBRİT ORANLAR VE KIRPMA
    w = row['width_px']
    h = row['height_px']
    m_left = row['margin_left']
    m_right = row['margin_right']
    m_top = row['margin_top']
    
    # İŞTE GÜNCELLENMİŞ KUSURSUZ ORAN:
    # Eski 4352'den 250 piksel daha yukarı çıktık, yeni Y koordinatımız: 4102
    m_bottom = 1 - (4102 / 5174) 

    left = int(w * m_left)
    top = int(h * m_top)
    right = int(w * (1 - m_right))
    bottom = int(h * (1 - m_bottom))

    try:
        # PIL ile kırp
        cropped_img = img.crop((left, top, right, bottom))
        
        # 3. GÜVENLİ KAYDETME (Türkçe karakterler için)
        cv2_cropped = cv2.cvtColor(np.array(cropped_img), cv2.COLOR_RGB2BGR)
        
        output_path = os.path.join(output_dir, crop_name)
        ext = os.path.splitext(crop_name)[1]
        if not ext:
            ext = '.jpg'
            
        is_success, im_buf_arr = cv2.imencode(ext, cv2_cropped)
        if is_success:
            im_buf_arr.tofile(output_path)
            print(f"✅ Başarılı: {img_name} -> {crop_name}")
            basarili += 1
        else:
            print(f"❌ Kaydedilemedi: {img_name}")
            
    except Exception as e:
        print(f"❌ Kırpma/Kaydetme hatası ({img_name}): {e}")

print(f"\n🏁 İşlem bitti! Toplam {basarili} adet harita kusursuz şekilde kırpıldı.")