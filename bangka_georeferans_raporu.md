# Bangka Adası Tarihi Topografik Harita Arşivi — Georeferans ve Mozaikleme Raporu

**Proje Kapsamı:** Bangka Adası 1930'lar Hollanda Koloniyel Topografik Harita Serisinin (`KK 083-04-01 / 085-04-10`) yapay zeka (ormansızlaşma ve arazi kullanımı tespiti) eğitim veri seti için hazırlanması
**Toplam Pafta Sayısı:** 176 adet
**Tarih:** Temmuz 2026

> **Not:** Bu rapordaki tüm sayısal değerler, diskteki dosyalar (`bangka_dataset_v2.csv`,
> `GEOREF_FINAL_STANDART_164/`, `GEOREF_FINAL_BIRLESIK_12/`, `kurtarilmis_haritalar/`)
> üzerinde yeniden ölçülerek doğrulanmıştır; önceki tahminlerden alınmamıştır.

---

## 1. Giriş ve Projenin Amacı

Bu çalışmanın amacı, 1930'lu yıllara ait 176 adet paftadan oluşan Bangka Adası
topografik harita serisini yüksek mekansal doğrulukla coğrafi koordinat sistemine
(WGS 84 / EPSG:4326) oturtmak ve derin öğrenme modellerinin işleyebileceği tutarlı bir
CBS altlığı haline getirmektir.

Arşiv iki tip paftadan oluşur:

- **164 tek-hücre pafta** — her biri tek bir 5′ × 5′ ızgara hücresi.
- **12 birleşik pafta** — iki komşu hücreye basılmış (9 dikey 5′ × 10′, 3 yatay 10′ × 5′);
  kıyı uçlarında hücrenin yarısının deniz olduğu durumlar için.

---

## 2. Kırpma (Cropping) ve Veri Seti Doğrulaması

Paftaların etrafındaki lejant ve beyaz çerçeve boşlukları (`margin`) kesilerek
`crop_*.jpg` dosyaları oluşturulmuştur.

1. **CSV senkronizasyonu:** Güncel `kurtarilmis_haritalar/` klasöründeki 176 crop
   dosyasının piksel boyutları (`crop_w` × `crop_h`), `bangka_dataset_v2.csv` tablosuyla
   birebir uyuşmaktadır.
2. **Yeniden kesim (Re-crop):** 8 dosya (`crop_012, 047, 056, 057, 145, 151, 170, 172`)
   orijinal taramalardan (`main maps`) yeniden kırpılmıştır. Bunların 7'si dikey birleşik
   paftadır; `crop_056` (`33-XXVI-d`) ise aslında **tek-hücre** bir paftadır (birleşik
   değil, yalnızca biraz uzun kırpılmıştı).
3. **Terminoloji düzeltmesi:** Arşivde **12 gerçek birleşik pafta** vardır (sub-kodda çift
   harf), 8 değil. Birleşik paftalar kıyı kenarındadır ve içeriklerinin bir hücrelik kısmı
   karadır; komşu hücre büyük ölçüde denizdir ve kırpma sırasında dışarıda kalmıştır. Bu,
   bir "veri kaybı" değil, paftanın fiziksel içeriğinin doğasıdır.

---

## 3. Sorun Teşhisi: Izgara Boşlukları ve Ölçek

Başlangıçtaki georeferans denemelerinde paftalar arasında boşluklar oluşuyordu. Diskteki
çıktılar üzerinde yapılan ölçümler iki hususu netleştirmiştir:

### A. Piksel Ölçeği
* Ölçülen ortalama piksel ölçeği: **`0.00001904` derece/piksel**.
* Nominal değer (0.083333° ÷ 4341 px): `0.00001920` derece/piksel.
* Sapma: **−0.85 %** (σ ≈ 0.007 %). Yani ölçek tutarlıdır; ciddi bir "büzüşme" yoktur.
  Önceki taslakta belirtilen `%15–30` büzüşme, nihai çıktılarda görülmemektedir.

### B. Pafta Tiplerinin Ayrışması
* **164 adet** standart tek-harfli pafta (`a`, `b`, ... `q`).
* **12 adet** birleşik pafta (`dh`, `ni`, `cd`, `on`, `fg` vb.). Nihai birleşik
  çıktılarda en-boy oranı ~1:1 korunmuştur; belirgin bir dikey/yatay sündürme
  tespit edilmemiştir.

---

## 4. Çözüm Metodolojisi ve Uygulanan Adımlar

### Adım 1: Sistematik Sapma (Offset) — Teorik Izgara → Gerçek Dünya

Teorik Hollanda pafta formülü (`base_lon = 105.0 + (col−32)·20′`), paftaların gerçek
coğrafi konumuyla çakışmaz. Manuel olarak (OSM/uydu üzerine) referanslanan paftalarla
karşılaştırma, her paftaya uygulanması gereken **tek ve son derece tutarlı** bir sapma
verir:

| Bileşen | Değer | Metrik |
|---|---|---|
| Boylam (Doğu) | **+0.14083° (+8.450′)** | ≈ +15.67 km |
| Enlem (Kuzey) | **+0.00012° (+0.007′)** | ≈ +13.4 m |
| Tutarlılık (σ) | **0.0000′** | — |

Buradaki büyük boylam terimi bir **hata değil**, pafta-indeksleme/datum referans farkıdır:
teorik ızgarayı paftaların gerçek konumuna oturtan sapmadır ve OSM üzerinde görsel olarak
doğrulanmıştır. Bunun üzerine, onlarca metre mertebesinde bir ince ayar (Batavia → WGS 84
datum + kağıt kayması) biner — önceki taslakta "ampirik GCP offset" (≈ −22.5 m boylam /
+17 m enlem) olarak raporlanan terim budur.

*(Önceki taslak yalnızca bu küçük ince-ayar terimini raporlamış, asıl +8.45′'lik büyük
sapmayı atlamıştı; bu yüzden belirtilen boylam kayması iki kat mertebede küçük görünüyordu.)*

### Adım 2: Standart 164 Paftanın Mozaiklenmesi (`GEOREF_FINAL_STANDART_164`)

164 standart paftanın Kuzey-Batı köşesi *teorik ızgara + sistematik sapma* değerine
demirlenmiş ve 5′ ölçeğe getirilmiştir. 164 pafta tek ve kusursuz bir ızgara kökeni
paylaştığından (**σ = 0.0000′**), sonuç tek-hücre paftalar arasında **boşluksuz, tam
bitişik bir döşeme**dir — bu iddia ölçülerek doğrulanmıştır.

### Adım 3: 12 Birleşik Paftanın Normalizasyonu (`GEOREF_FINAL_BIRLESIK_12`)

Her birleşik pafta iki hücre kaplar ama kıyı paftası olduğu için karayı yalnızca
**birinde** içerir; diğeri açık denizdir ve büyük ölçüde kırpılmıştır. Doğrulama, tutarlı
bir kural ortaya koymuş ve 12 paftanın tamamında geçerli olduğunu göstermiştir:

- **Sub-kodun ilk harfi kara hücresini belirtir** ve her pafta tam o hücreye demirlenmiştir
  (12/12 eşleşme). Kodlar sıraya duyarlıdır: `ni` → kara *alt* hücrede, `in` → kara *üst*
  hücrede.
- **Sıfır çakışma:** hiçbir hücre iki kez doldurulmamıştır.
- **12 boş eş-hücrenin tamamı denizdir** — kıyı çizgisinin gerektirdiği gibi kasıtlı boştur.

Dolayısıyla birleşik paftalar **doğru konumdadır**; QGIS'te bazı paftaların "yukarıda/aşağıda
asılı" görünmesi bir koordinat hatası değil, bu boş deniz hücrelerinden kaynaklanır.

---

## 5. Doğrulama Özeti

| Kriter | Sonuç |
|---|---|
| CSV ↔ disk crop boyutları (176) | Senkron |
| Tek-hücre ızgara kökeni dağılımı (164) | **σ = 0.0000′** (kusursuz döşeme) |
| Piksel ölçeği (nominale göre) | −0.85 % (σ ≈ 0.007 %) |
| Sistematik sapma | +8.450′ D / +0.007′ K, σ = 0.0000′ |
| Birleşik "ilk harf = kara hücresi" kuralı | **12 / 12** |
| Birleşik hücre çakışması | **0** |
| Birleşik eş-hücreler = deniz | **12 / 12** |

---

## 6. Sonuç ve Değerlendirme

Teorik koloniyel ızgara, OSM ile doğrulanmış sistematik sapma ve tutarlı bir birleşik-pafta
demirleme kuralı birleştirilerek, 176 paftalık arşiv mekansal olarak tutarlı bir WGS 84 veri
setine dönüştürülmüştür. 164 tek-hücre pafta kusursuz döşenir (σ = 0.0′); 12 kıyı birleşik
paftası doğru kara hücrelerine demirlenmiştir ve deniz tarafındaki hücreleri kasıtlı boştur.
Veri seti (`GEOREF_FINAL_STANDART_164` + `GEOREF_FINAL_BIRLESIK_12`), tarihsel kartografya ve
yapay zeka görüntü işleme modelleri için uygun bir altlıktır.

**Önerilen ek doğrulama:** "Kesintisiz" iddiasının sayısal bir toleransla ifade edilebilmesi
için, 12 birleşik paftanın bağımsız bir doğruluk ölçümü (OSM overlay veya basılı neatline'ın
tam arc-dakikaya göre RMS artığı) önerilir. Otomatik neatline tespiti denenmiş ancak bu
taramalarda çerçeve çizgileri güvenilir ölçüm için fazla soluk çıkmıştır; örneklem üzerinde
QGIS tabanlı bir overlay bu boşluğu kapatacaktır.
