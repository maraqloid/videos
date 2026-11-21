# Maraqloid — günlük video üretim talimatı

Bu depo @maraqloid (YouTube Shorts + Instagram Reels) için günlük videoları ve onları üreten kodu tutar.

## Klasörler
- `engine/engine.py` — JSON senaryo → 1080x1920, 30 fps MP4 (Azerbaycanca seslendirme + altyazı + müzik).
- `engine/tts_espeak.py` — yedek (robotik) ses; ElevenLabs çalışmazsa kullanılır.
- `specs/YYYY-MM-DD-konu.json` — her videonun senaryosu.
- `videos/YYYY-MM-DD-konu.mp4` — yayınlanan videolar (Buffer buradan indirir).
- `topics.md` — işlenmiş konular. Aynı konuyu tekrar kullanma.

## Senaryo formatı
```json
{"title": "...", "palette": [[r,g,b],[r,g,b]],
 "scenes": [{"text": "Seslendirilen ve altyazı olan cümle.", "emoji": ["🐙","❤️"], "big": "3 ÜRƏK",
             "palette": [[r,g,b],[r,g,b]]}]}
```

## Gerçek görüntüler (Pexels / Pixabay)
Her sahneye `"query"` alanı ekle: o sahnede anlatılanı birebir gösteren, İngilizce, somut ve görsel bir arama ifadesi (2–4 kelime).
- Sorgunun **ilk kelimesi ana konu** olmalı (motor, etiketlerinde bu kelime geçmeyen görüntüleri eler). Yeşil perde, animasyon ve yapay zekâ ile üretilmiş klipler otomatik elenir.
- İyi: `"mud volcano eruption"`, `"octopus swimming"`, `"venus planet"`, `"baku old city"`. Kötü: `"interesting fact"`, `"history"`, `"amazing"`.
- Belirli, önizlenip seçilmiş bir Pixabay klibi için sahneye `"pixabay_id": <id>` ve isteğe bağlı `"offset": <sn>` ekle (ör. şimşek gibi anlık olaylarda parlak anı yakalamak için). `query` yedek olarak kalır.
- Varsayılan dikey **video klip** aranır; bulunamazsa fotoğraf (yavaş yakınlaşma efektiyle) kullanılır. Sadece fotoğraf istersen `"media": "photo"` ekle (ör. tarihi kişi, harita, belirli bir yapı).
- `query` verilmeyen ya da hiçbir görüntü bulunamayan sahne eski emoji tarzına döner. Yorum sorusu sahnesi için de bir `query` ver (ör. konuyla ilgili genel bir çekim).
- `emoji` alanını yine de doldur (yedek olarak kullanılır).
- Render çıktısındaki `"real_media_scenes"` değeri en az sahnelerin çoğunluğu olmalı. Log'da `WARNING: pexels lookup failed` görürsen sorgu kelimelerini değiştirip yeniden dene.
- **Görüntü doğruluğu:** Render sonrası her sahneden bir kare çıkarıp bak. Görüntü anlatılanla örtüşmüyorsa (ör. palçıq vulkanı yerine lav püskürten volkan, Venera yerine Ay) sorguyu değiştir ve yeniden render et. Yanlış ya da yanıltıcı görüntü kullanma; tanınabilir kişileri, anlatılan olayla ilgisiz bir bağlamda gösterme.

## Kısaltmalar ve yabancı adlar (seslendirme / altyazı)
Seslendirmenin yanlış okuyabileceği kısaltma ve yabancı adları `text` içinde okunuşuyla, tek parça (tireyle) yaz ve spec'in en üstüne `display_map` ekle; altyazıda doğru yazım görünür:
```json
"display_map": {"Ci-Ti-Ey-altı": "GTA 6", "Vays-Siti": "VICE CITY", "Nasa": "NASA"}
```
Değerleri BÜYÜK HARFLE yaz (Latin I/İ karışmasın). Telif hakkıyla korunan oyun/film görüntüsü, logo veya fragman kullanma; Pixabay'den konuyu çağrıştıran genel görüntüler kullan.

## Kullanıcının verdiği görseller
Bir sahneye kullanıcının yüklediği bir görseli koymak için `"image": "/yerel/yol.jpg"` kullan (Pixabay araması yapılmaz). `"focus_x"` (0–1) dikey kırpmanın yatay merkezini, `"big_y"` (piksel, varsayılan 340) büyük başlığın yüksekliğini ayarlar. Yüzler üstteyse başlığı `"big_y": 1110` ile altyazının üstüne indir. Telifli görselleri herkese açık depoya koyma; yalnızca bitmiş video yüklenir.

## Erişim ve etkileşim kuralları (her videoda uygula)
Shorts/Reels algoritması önce "izlendi mi, geçildi mi"ye, sonra izlenme oranına bakar. Her şey buna göre:

1. **İlk saniye kanca:** 1. sahnenin cümlesi doğrudan en şaşırtıcı bilgiyle başlar (en fazla ~8 kelime). "Bilirdinizmi?", "Salam", "Bu gün" gibi dolgu girişler YASAK. 1. sahnenin `big` metni kancayı 2–3 kelimeyle özetler (ilk karede ekranda olur, sessiz izleyen de anlar).
2. **Kısa ve tek fikir:** 4–6 sahne, toplam 15–30 sn. Tek bir konu; her sahne bir öncekinden daha şaşırtıcı ya da somut olsun. Gereksiz tekrar cümlesi yok.
3. **Merak boşluğu:** Mümkünse 1. ya da 2. sahnede açık bir soru bırak, cevabı sonda ver ("Ama asıl ilginci başka..." gibi). Vaat ettiğini mutlaka ver, yanıltıcı kanca yok.
4. **Ayrı "abunə ol" sahnesi YOK:** İnsanlar orada geçiyor. Son sahne = son şaşırtıcı bilgi + yorumu tetikleyen kısa soru, ör. "Sən bunu bilirdin? Şərhdə yaz!" / "Sənin fikrin nədir: ... yoxsa ...?". `big`: kısa soru (ör. "SƏN BİLİRDİN?"), emoji: 💬/🤔 benzeri.
5. **Senkron:** Senaryoda üç nokta (...) ve uzun dramatik duraklamalar kullanma; motor uzun sessizlikleri zaten kısaltır.
6. **Döngü (loop):** Son cümle doğal olarak ilk cümleye bağlanacak şekilde yaz, böylece video başa döndüğünde akış kopmaz (tekrar izlenme sayısını artırır). AMA son cümle kendi başına **tam ve anlamlı** olmalı: "Amma unutma:", "Axı...", "Çünki" gibi yarım kalan, devamı gelmeyen bir ifadeyle BİTİRME (izleyici videoyu eksik sanıyor). Son seslendirilen kelime soru ya da çağrı olsun (ör. "Şərhdə yaz!"). Render sonrası timing.json'daki son chunk'ı okuyup cümlenin tamamlandığını kontrol et.
7. **Konu seçimi:** Geniş kitlenin "vay!" diyeceği, gündelik hayata dokunan konular. Haftada 1–2 kez Azerbaycan'a özgü bir konu (tarih, coğrafya, doğa, bilim insanları, rekorlar). Yerel açı hem yeni bilgi sunar hem de yerel kitlenin paylaşımını artırır.
8. Dil: Azerbaycan Türkçesi (Latin alfabesi), doğru dilbilgisi, konuşma dili gibi akıcı. Sayıları seslendirme metninde yazıyla yaz ("iki yüz qırx üç"); `big` alanında rakam kullanılabilir.
9. `big` en fazla ~16 karakter, BÜYÜK HARF (Azerbaycanca İ/I kurallarıyla).
10. `emoji`: ilk emoji büyük ana görsel, diğerleri etrafında döner. Üzerinde yazı olan emojileri kullanma (📅 "July 17" gösterir; 🆒 🆕 gibi İngilizce yazılılar da olmaz).
11. Doğruluk şart: yalnızca iyi bilinen, doğrulanabilir bilgiler. Emin değilsen web'de doğrula; şüpheli "internet efsanelerini" kullanma.

## Üretim
```bash
pip install --break-system-packages -q espeakng-loader numpy pillow cairosvg
MQ_ELEVEN_KEY=<anahtar> MQ_ELEVEN_VOICE=BQgh92MxG7QAtCA8wY7O MQ_PIXABAY_KEY=<anahtar> \
  python3 engine/engine.py specs/<dosya>.json /tmp/render/<dosya>.mp4
```
Çıktı JSON'unda `"tts": ["elevenlabs"]` olmalı. `espeak` çıktıysa (robotik ses) YAYINLAMA; kullanıcıya bildir.
Render ~4 dk sürer; arka planda çalıştırıp bitmesini bekle.
Emojiler vektör Noto setinden (npm @svgmoji/noto, ilk çalıştırmada indirilir) keskin çizilir. Log'da `WARNING: no vector emoji` görürsen o emojiyi başka bir emojiyle değiştirip yeniden render et (düşük çözünürlüklü görünür).

## Yayın (Buffer)
- Organizasyon: "My organization" `6af8c4c7bfa2116d7effa63d`
- YouTube kanalı: `6af8cd6f62b70b94b03324c1` — metadata.youtube: title (≤100 karakter, sonunda `#shorts`), categoryId "27", privacy "public", madeForKids false
- Instagram: `6af8d23a62b70b94b0336e70` — metadata.instagram: type "reel", shouldShareToFeed true
- schedulingType "automatic", mode "customScheduled", dueAt `YYYY-MM-DDT12:00:00+04:00` (Bakü)
- Video URL: `https://raw.githubusercontent.com/maraqloid/videos/main/videos/<dosya>.mp4`
- Açıklamalarda "her gün 12:00" gibi saat/periyot ifadesi KULLANMA.

## Başlık ve açıklama (arama + etkileşim)
- **YouTube başlığı:** ≤60 karakter, insanların arayacağı anahtar kelime başta (konu adı), merak uyandıran iddia ya da soru, sonda 1 emoji + `#shorts`. Örn: "Venerada gün ildən uzundur?! 🪐 #shorts"
- **YouTube açıklaması:** 1. cümle anahtar kelimeleri içeren özet; 2. cümle yorum sorusu ("Sən bunu bilirdin? Şərhdə yaz 👇"); sonra "Daha çox maraqlı fakt üçün abunə olun! 🔔"; sonra 3–4 hashtag (#maraqlıfaktlar #bilirdinizmi + konu + #shorts).
- **Instagram açıklaması:** 1. satır kanca (videodaki iddia, anahtar kelimeli); 1–2 cümle ek bilgi; yorum sorusu; paylaşım çağrısı "Bunu bilməyən dostuna göndər 📩"; "Daha çox maraqlı fakt üçün izlə: @maraqloid"; 3–5 hashtag (#maraqlıfaktlar #bilirdinizmi #azərbaycan + konu).
- Haftalık öğrenimler varsa (`insights.md`), konu ve kanca seçiminde onları uygula.
