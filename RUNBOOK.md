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
- 5–8 sahne, toplam 25–40 sn. İlk sahne "Bilirdinizmi? ..." gibi bir kanca; son sahne her zaman:
  `{"text": "Daha çox maraqlı fakt üçün Maraqloidə abunə olun!", "emoji": ["🔔","⭐","👍"], "big": "ABUNƏ OL!", "palette": [[90,20,60],[200,60,60]]}`
- Dil: Azerbaycan Türkçesi (Latin alfabesi), doğru dilbilgisi. Sayıları seslendirme metninde yazıyla yaz ("iki yüz qırx üç"); `big` alanında rakam kullanılabilir.
- `big` en fazla ~16 karakter, BÜYÜK HARF (Azerbaycanca İ/I kurallarıyla).
- `emoji`: ilk emoji büyük ana görsel, diğerleri etrafında döner. Üzerinde yazı olan emojileri kullanma (📅 "July 17" gösterir, 🆒 🆕 gibi İngilizce yazılılar da olmaz).
- Konular dönüşümlü: bilim, tarih, teknoloji, doğa/hayvanlar, uzay, insan vücudu, coğrafya.
- Doğruluk şart: yalnızca iyi bilinen, doğrulanabilir bilgiler. Emin değilsen web'de doğrula; şüpheli "internet efsanelerini" kullanma.

## Üretim
```bash
pip install --break-system-packages -q espeakng-loader numpy pillow
MQ_ELEVEN_KEY=<anahtar> MQ_ELEVEN_VOICE=BQgh92MxG7QAtCA8wY7O \
  python3 engine/engine.py specs/<dosya>.json /tmp/render/<dosya>.mp4
```
Çıktı JSON'unda `"tts": ["elevenlabs"]` olmalı. `espeak` çıktıysa (robotik ses) YAYINLAMA; kullanıcıya bildir.
Render ~4 dk sürer; arka planda çalıştırıp bitmesini bekle.

## Yayın (Buffer)
- Organizasyon: "My organization" `6af8c4c7bfa2116d7effa63d`
- YouTube kanalı: `6af8cd6f62b70b94b03324c1` — metadata.youtube: title (≤100 karakter, sonunda `#shorts`), categoryId "27", privacy "public", madeForKids false
- Instagram: `6af8d23a62b70b94b0336e70` — metadata.instagram: type "reel", shouldShareToFeed true
- schedulingType "automatic", mode "customScheduled", dueAt `YYYY-MM-DDT12:00:00+04:00` (Bakü)
- Video URL: `https://raw.githubusercontent.com/maraqloid/videos/main/videos/<dosya>.mp4`
- Açıklamalarda "her gün 12:00" gibi saat/periyot ifadesi KULLANMA.
- Açıklama sonu: YouTube → "Daha çox maraqlı fakt üçün abunə olun! 🔔", Instagram → "Daha çox maraqlı fakt üçün izlə: @maraqloid". 4–5 hashtag (#maraqlıfaktlar #bilirdinizmi + konuya özel; YouTube'da #shorts).
