"""Maraqloid video engine: JSON spec -> 1080x1920 30fps mp4 with Azerbaijani voice + captions.
Usage: python3 engine.py spec.json out.mp4
spec = {"title": "...", "palette": [[r,g,b],[r,g,b]],
        "scenes": [{"text": "Sentence spoken + captioned", "emoji": ["🐙","❤️"], "big": "3 ÜRƏK",
                    "palette": optional override}], "outro": "Abunə ol!"}
"""
import json, sys, os, math, random, subprocess, wave, re
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1080, 1920, 30
F_BOLD = "/usr/share/fonts/opentype/inter/InterDisplay-Black.otf"
F_SEMI = "/usr/share/fonts/opentype/inter/InterDisplay-Bold.otf"
F_EMOJI = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"
for f in ["/usr/share/fonts/opentype/inter/InterDisplay-Black.otf"]:
    if not os.path.exists(f):
        F_BOLD = F_SEMI = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
SR = 24000
_font_cache = {}

def font(path, size):
    k = (path, size)
    if k not in _font_cache:
        _font_cache[k] = ImageFont.truetype(path, size)
    return _font_cache[k]

_emoji_cache = {}
def emoji_img(ch, size):
    k = (ch, size)
    if k in _emoji_cache:
        return _emoji_cache[k]
    f = ImageFont.truetype(F_EMOJI, 109)  # only bitmap size available
    im = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((80, 80), ch, font=f, embedded_color=True, anchor="mm")
    bb = im.getbbox() or (0, 0, 160, 160)
    im = im.crop(bb)
    s = size / max(im.size)
    im = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.LANCZOS)
    _emoji_cache[k] = im
    return im

# ---------------- TTS ----------------
def tts(text):
    """Return float32 mono audio at SR. Tries ElevenLabs (if MQ_ELEVEN_KEY set), edge-tts, then espeak-ng."""
    key = os.environ.get("MQ_ELEVEN_KEY")
    if key:
        try:
            import urllib.request
            vid = os.environ.get("MQ_ELEVEN_VOICE", "JBFqnCBsd6RMkjVDRZzb")
            req = urllib.request.Request(f"https://api.elevenlabs.io/v1/text-to-speech/{vid}?output_format=mp3_44100_128",
                data=json.dumps({"text": text, "model_id": os.environ.get("MQ_ELEVEN_MODEL", "eleven_v3"), "language_code": "az"}).encode(),
                headers={"xi-api-key": key, "Content-Type": "application/json"})
            mp3 = urllib.request.urlopen(req, timeout=60).read()
            p = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", "pipe:0", "-f", "f32le", "-ac", "1", "-ar", str(SR), "pipe:1"],
                               input=mp3, capture_output=True, check=True)
            return np.frombuffer(p.stdout, np.float32).copy(), "elevenlabs"
        except Exception as e:
            print("elevenlabs failed:", e, file=sys.stderr)
    try:
        import asyncio, edge_tts, io
        async def go():
            c = edge_tts.Communicate(text, os.environ.get("MQ_VOICE", "az-AZ-BabekNeural"), rate="+5%")
            buf = b""
            async for ch in c.stream():
                if ch["type"] == "audio":
                    buf += ch["data"]
            return buf
        mp3 = asyncio.run(asyncio.wait_for(go(), 20))
        if mp3:
            p = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", "pipe:0", "-f", "f32le", "-ac", "1", "-ar", str(SR), "pipe:1"],
                               input=mp3, capture_output=True, check=True)
            return np.frombuffer(p.stdout, np.float32).copy(), "edge"
    except Exception:
        pass
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from tts_espeak import synth
    sr, a = synth(text, rate=148, pitch=42)
    a = a.astype(np.float32) / 32768
    p = subprocess.run(["ffmpeg", "-loglevel", "error", "-f", "f32le", "-ar", str(sr), "-ac", "1", "-i", "pipe:0",
                        "-af", "highpass=f=80,lowpass=f=7000,aecho=0.8:0.5:30:0.12,loudnorm=I=-16",
                        "-f", "f32le", "-ar", str(SR), "pipe:1"], input=a.tobytes(), capture_output=True, check=True)
    return np.frombuffer(p.stdout, np.float32).copy(), "espeak"

def trim(a, thr=0.01):
    idx = np.where(np.abs(a) > thr)[0]
    return a[max(0, idx[0] - 600): idx[-1] + 1200] if len(idx) else a

def chunks_of(sentence, maxw=4):
    words = sentence.split()
    out, cur = [], []
    for w in words:
        cur.append(w)
        if len(cur) >= maxw or re.search(r"[,.!?:;—]$", w):
            out.append(" ".join(cur)); cur = []
    if cur:
        out.append(" ".join(cur))
    return out

def tts_aligned(text):
    """ElevenLabs with-timestamps: returns (audio float32 @SR, [(char,start,end)])."""
    import urllib.request, base64
    key = os.environ["MQ_ELEVEN_KEY"]
    vid = os.environ.get("MQ_ELEVEN_VOICE", "BQgh92MxG7QAtCA8wY7O")
    body = {"text": text, "model_id": os.environ.get("MQ_ELEVEN_MODEL", "eleven_v3"), "language_code": "az"}
    last = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(f"https://api.elevenlabs.io/v1/text-to-speech/{vid}/with-timestamps?output_format=mp3_44100_128",
                data=json.dumps(body).encode(), headers={"xi-api-key": key, "Content-Type": "application/json"})
            d = json.loads(urllib.request.urlopen(req, timeout=120).read())
            break
        except Exception as e:
            last = e
    else:
        raise RuntimeError(f"ElevenLabs failed: {last}")
    mp3 = base64.b64decode(d["audio_base64"])
    p = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", "pipe:0", "-f", "f32le", "-ac", "1", "-ar", str(SR), "pipe:1"],
                       input=mp3, capture_output=True, check=True)
    al = d["alignment"]
    chars = list(zip(al["characters"], al["character_start_times_seconds"], al["character_end_times_seconds"]))
    return np.frombuffer(p.stdout, np.float32).copy(), chars

def chunk_times(text, chars, maxw=4):
    """Map caption chunks onto character alignment."""
    joined = "".join(c for c, _, _ in chars)
    out, pos = [], 0
    for ch in chunks_of(text, maxw):
        i = joined.find(ch, pos)
        if i < 0:
            i = pos
        j = min(len(chars) - 1, i + len(ch) - 1)
        out.append({"text": ch, "s": chars[min(i, len(chars)-1)][1], "e": chars[j][2]})
        pos = i + len(ch)
    return out

# ---------------- music ----------------
def music(dur):
    t = np.arange(int(dur * SR)) / SR
    chords = [[220, 277.18, 329.63], [196, 246.94, 293.66], [174.61, 220, 261.63], [196, 246.94, 329.63]]
    out = np.zeros_like(t)
    seg = 4.0
    for i, ch in enumerate(chords * int(dur // (seg * 4) + 2)):
        s, e = int(i * seg * SR), int((i + 1) * seg * SR + SR)
        if s >= len(t): break
        tt = t[s:min(e, len(t))] - i * seg
        env = np.clip(tt / 1.2, 0, 1) * np.clip((seg + 1 - tt) / 1.5, 0, 1)
        for f in ch:
            out[s:s + len(tt)] += env * (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(2 * np.pi * f * 2.002 * tt)) * 0.05
    # soft pulse
    beat = (np.sin(2 * np.pi * 55 * t) * np.exp(-((t % 0.5) * 18))) * 0.12
    out += beat
    out *= np.clip(t / 1.5, 0, 1) * np.clip((dur - t) / 1.5, 0, 1)
    return out.astype(np.float32)

# ---------------- drawing ----------------
def az_upper(s):
    return s.replace("i", "İ").replace("ı", "I").upper()

def lerp(a, b, t): return a + (b - a) * t
def ease_out_back(x):
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2
def clamp(x, a=0, b=1): return max(a, min(b, x))

def gradient(c1, c2, t):
    y = np.linspace(0, 1, H)[:, None]
    x = np.linspace(0, 1, W)[None, :]
    k = clamp(0.5 + 0.5 * math.sin(t * 0.4))
    m = np.clip(y * 0.85 + x * 0.15 * k + 0.05 * np.sin(x * 6 + t), 0, 1)[..., None]
    img = (np.array(c1)[None, None, :] * (1 - m) + np.array(c2)[None, None, :] * m)
    # radial glow
    r = np.sqrt((x - 0.5) ** 2 + ((y - 0.4) * 1.6) ** 2)[..., None]
    img = img + np.clip(0.35 - r, 0, 1) * 120
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB")

class Particles:
    def __init__(self, n=40, seed=1):
        r = random.Random(seed)
        self.p = [(r.random() * W, r.random() * H, r.uniform(4, 16), r.uniform(20, 70), r.random() * 6) for _ in range(n)]
    def draw(self, d, t):
        for x, y, s, v, ph in self.p:
            yy = (y - v * t) % (H + 40) - 20
            xx = x + 18 * math.sin(t * 0.8 + ph)
            a = int(60 + 50 * math.sin(t * 2 + ph))
            d.ellipse([xx - s, yy - s, xx + s, yy + s], outline=(255, 255, 255, a), width=2)

def draw_text_outlined(d, xy, text, f, fill, anchor="mm", stroke=10, stroke_fill=(0, 0, 0, 255)):
    d.text(xy, text, font=f, fill=fill, anchor=anchor, stroke_width=stroke, stroke_fill=stroke_fill)

def wrap(text, f, maxw, d):
    words, lines, cur = text.split(), [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if d.textlength(test, font=f) <= maxw: cur = test
        else:
            if cur: lines.append(cur)
            cur = w
    if cur: lines.append(cur)
    return lines

def render_scene(sc, idx, total_scenes, t0_global, dur_total, out_path, pal, part):
    dur = sc["dur"]
    c1, c2 = sc.get("palette", pal)
    n = int(round(dur * FPS))
    tmp = out_path + ".tmp.mp4"
    p = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                          "-i", "pipe:0", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", tmp],
                         stdin=subprocess.PIPE)
    emojis = sc.get("emoji", [])
    big = sc.get("big", "")
    for i in range(n):
        t = i / FPS
        tg = t0_global + t
        bg = gradient(c1, c2, tg).convert("RGBA")
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        part.draw(d, tg)
        bg = Image.alpha_composite(bg, ov)
        # main emoji
        if emojis:
            e_in = 1.0 if sc.get("_first") else clamp(t / 0.45)
            sc_ = ease_out_back(e_in) if e_in < 1 else 1 + 0.04 * math.sin(t * 3)
            size = int(520 * max(0.01, sc_))
            em = emoji_img(emojis[0], size).rotate(6 * math.sin(t * 1.5), resample=Image.BICUBIC, expand=True)
            cx, cy = W // 2, int(760 + 22 * math.sin(t * 2))
            # glow
            glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            gd = ImageDraw.Draw(glow)
            gr = int(330 * min(1, e_in * 1.2))
            gd.ellipse([cx - gr, cy - gr, cx + gr, cy + gr], fill=(255, 255, 255, 50))
            bg = Image.alpha_composite(bg, glow.filter(ImageFilter.GaussianBlur(60)))
            bg.alpha_composite(em, (cx - em.width // 2, cy - em.height // 2))
            # orbiting secondary emojis
            for k, ch in enumerate(emojis[1:]):
                a_in = 1.0 if sc.get("_first") else clamp((t - 0.35 - 0.15 * k) / 0.4)
                if a_in <= 0: continue
                ang = tg * 0.9 + k * (2 * math.pi / max(1, len(emojis) - 1))
                rx, ry = 390, 230
                ex, ey = cx + rx * math.cos(ang), cy + ry * math.sin(ang)
                es = int(190 * ease_out_back(a_in))
                if es > 4:
                    im2 = emoji_img(ch, es)
                    bg.alpha_composite(im2, (int(ex - im2.width / 2), int(ey - im2.height / 2)))
        d = ImageDraw.Draw(bg)
        # big keyword
        if big:
            b_in = 1.0 if sc.get("_first") else clamp((t - 0.15) / 0.4)
            if b_in > 0:
                fb = font(F_BOLD, 150)
                lines = wrap(big, fb, W - 120, d)
                fsz = 150 if len(lines) == 1 else 120
                fb = font(F_BOLD, fsz)
                lines = wrap(big, fb, W - 120, d)
                yb = 340 - (len(lines) - 1) * fsz // 2
                off = (1 - ease_out_back(b_in)) * 120
                for li, ln in enumerate(lines):
                    draw_text_outlined(d, (W // 2, yb + li * (fsz + 8) + off), ln, fb, (255, 222, 60, int(255 * b_in)), stroke=12,
                                       stroke_fill=(20, 10, 40, int(255 * b_in)))
        # captions: current chunk
        cur = None
        for ch in sc["chunks"]:
            if ch["s"] <= t < ch["e"] + 0.05: cur = ch
        if cur is None and sc["chunks"] and t >= sc["chunks"][-1]["s"]: cur = sc["chunks"][-1]
        if cur:
            fc = font(F_BOLD, 88)
            lines = wrap(az_upper(cur["text"]), fc, W - 140, d)
            pop = ease_out_back(clamp((t - cur["s"]) / 0.18))
            y0 = 1330 - (len(lines) - 1) * 52
            # backing pill
            maxw = max(d.textlength(l, font=fc) for l in lines)
            pad = 36
            d.rounded_rectangle([W / 2 - maxw / 2 - pad, y0 - 70, W / 2 + maxw / 2 + pad, y0 + (len(lines) - 1) * 104 + 70], radius=36,
                                fill=(10, 8, 30, 150))
            for li, ln in enumerate(lines):
                draw_text_outlined(d, (W // 2, y0 + li * 104 + (1 - pop) * 30), ln, fc, (255, 255, 255, 255), stroke=8)
        # brand (no progress bar: showing remaining length invites swipes)
        fbr = font(F_SEMI, 44)
        d.text((W // 2, 130), "MARAQLOID", font=fbr, fill=(255, 255, 255, 220), anchor="mm")
        # fade in/out at scene edges (soft flash)
        img = bg.convert("RGB")
        if t < 0.12 and idx > 0:
            img = Image.blend(Image.new("RGB", (W, H), (255, 255, 255)), img, clamp(t / 0.12) * 0.7 + 0.3)
        p.stdin.write(img.tobytes())
    p.stdin.close()
    if p.wait() != 0:
        raise RuntimeError("ffmpeg failed")
    os.replace(tmp, out_path)

def build(spec_path, out):
    spec = json.load(open(spec_path))
    pal = spec.get("palette", [[20, 30, 90], [120, 30, 140]])
    work = os.path.splitext(out)[0] + "_work"
    os.makedirs(work, exist_ok=True)
    scenes = spec["scenes"]
    voice_parts, engine_used = [], set()
    gap = np.zeros(int(0.12 * SR), np.float32)
    for si, sc in enumerate(scenes):
        sc["_first"] = si == 0
        lead = 0.0 if si == 0 else 0.1
        if os.environ.get("MQ_ELEVEN_KEY"):
            a, chars = tts_aligned(sc["text"]); engine_used.add("elevenlabs")
            sp = float(os.environ.get("MQ_SPEED", "1.3"))
            if abs(sp - 1) > 0.01:
                a = np.frombuffer(subprocess.run(["ffmpeg", "-loglevel", "error", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "pipe:0",
                    "-af", f"atempo={sp}", "-f", "f32le", "pipe:1"], input=a.tobytes(), capture_output=True, check=True).stdout, np.float32).copy()
                chars = [(c, s0 / sp, e0 / sp) for c, s0, e0 in chars]
            sc["chunks"] = [{"text": c["text"], "s": c["s"] + lead, "e": c["e"] + lead} for c in chunk_times(sc["text"], chars)]
            idx = np.where(np.abs(a) > 0.01)[0]
            if len(idx):
                st = max(0, idx[0] - 240)  # trim leading silence so speech starts at once
                a = a[st: idx[-1] + 2400]
                for c in sc["chunks"]:
                    c["s"] = max(lead, c["s"] - st / SR); c["e"] = max(c["s"] + 0.1, c["e"] - st / SR)
            audio = [np.zeros(int(lead * SR), np.float32), a]
        else:
            sc["chunks"] = []
            t = lead
            audio = [np.zeros(int(lead * SR), np.float32)]
            for ch in chunks_of(sc["text"]):
                a, eng = tts(ch); engine_used.add(eng)
                a = trim(a)
                sc["chunks"].append({"text": ch, "s": t, "e": t + len(a) / SR})
                audio += [a, gap]
                t += len(a) / SR + len(gap) / SR
        audio.append(np.zeros(int(0.15 * SR), np.float32))
        sc["audio"] = np.concatenate(audio)
        sc["dur"] = round(len(sc["audio"]) / SR * FPS) / FPS
        voice_parts.append(sc["audio"][: int(sc["dur"] * SR)])
    voice = np.concatenate(voice_parts)
    total = len(voice) / SR
    part = Particles()
    files, t0 = [], 0
    for i, sc in enumerate(scenes):
        f = os.path.join(work, f"s{i:02d}.mp4")
        render_scene(sc, i, len(scenes), t0, total, f, pal, part)
        files.append(f); t0 += sc["dur"]
    with open(os.path.join(work, "list.txt"), "w") as fh:
        fh.writelines(f"file '{os.path.abspath(f)}'\n" for f in files)
    mix = voice / (np.abs(voice).max() + 1e-6) * 0.9
    mus = music(total)[: len(mix)]
    mix = np.clip(mix + mus * 0.35, -1, 1)
    wavp = os.path.join(work, "mix.wav")
    with wave.open(wavp, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((mix * 32767).astype(np.int16).tobytes())
    tmp = out + ".tmp.mp4"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", os.path.join(work, "list.txt"), "-i", wavp,
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart",
                    "-shortest", tmp], check=True)
    os.replace(tmp, out)
    print(json.dumps({"out": out, "duration": round(total, 2), "tts": sorted(engine_used)}))

def still(spec_path, scene_idx, t, png):
    """Render a single frame for checking layout."""
    spec = json.load(open(spec_path)); sc = spec["scenes"][scene_idx]
    sc["chunks"] = [{"text": c, "s": i * 1.0, "e": i * 1.0 + 0.9} for i, c in enumerate(chunks_of(sc["text"]))]
    sc["dur"] = 1 / FPS
    global FPS_
    tmpd = "/tmp/_still"; os.makedirs(tmpd, exist_ok=True)
    # quick path: reuse render loop by rendering one frame at t
    pal = spec.get("palette", [[20, 30, 90], [120, 30, 140]])
    import types
    sc2 = dict(sc); sc2["dur"] = t + 1 / FPS
    render_scene(sc2, scene_idx, 1, 0, 40, tmpd + "/x.mp4", pal, Particles())
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-sseof", "-0.05", "-i", tmpd + "/x.mp4", "-frames:v", "1", png], check=True)

if __name__ == "__main__":
    if sys.argv[1] == "still":
        still(sys.argv[2], int(sys.argv[3]), float(sys.argv[4]), sys.argv[5])
    else:
        build(sys.argv[1], sys.argv[2])
