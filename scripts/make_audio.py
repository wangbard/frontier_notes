#!/usr/bin/env python3
"""Make the MP3 for one issue and write segment timings back into the page.

Usage: python3 scripts/make_audio.py issues/YYYY-MM-DD.html

Reads the audio script from the page (#scriptText, one <div data-seg> per story),
speaks it with the Piper voice, saves audio/YYYY-MM-DD.mp3, and fills the
<script id="audio-meta"> block with {"starts": [...], "dur": seconds}.
"""
import html, io, json, os, re, shutil, subprocess, sys, tarfile, urllib.request, wave

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOICE_DIR = os.path.join(ROOT, "voices")
VOICE = os.path.join(VOICE_DIR, "en-us-lessac-medium.onnx")
VOICE_URL = "https://github.com/rhasspy/piper/releases/download/v0.0.2/voice-en-us-lessac-medium.tar.gz"
PARA_GAP, SEG_GAP = 0.45, 0.5


def ensure_piper():
    try:
        import piper  # noqa: F401
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "piper-tts"])


def ensure_voice():
    if os.path.exists(VOICE) and os.path.exists(VOICE + ".json"):
        return
    os.makedirs(VOICE_DIR, exist_ok=True)
    tmp = os.path.join(VOICE_DIR, "voice.tgz")
    urllib.request.urlretrieve(VOICE_URL, tmp)
    with tarfile.open(tmp) as t:
        for m in t.getmembers():
            if m.name.endswith((".onnx", ".onnx.json")):
                m.name = os.path.basename(m.name)
                t.extract(m, VOICE_DIR)
    os.remove(tmp)


def ffmpeg_bin():
    found = shutil.which("ffmpeg")
    if found:
        return found
    try:
        import imageio_ffmpeg
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "imageio-ffmpeg"])
        import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def speakable(fragment):
    text = html.unescape(re.sub(r"<[^>]+>", "", fragment))
    text = re.sub(r"\s+", " ", text).strip()
    return text.replace("\u2019", "'").replace("\u2013", "-").replace("\u2014", ", ")


def main(page_path):
    page = open(page_path, encoding="utf-8").read()
    date = re.search(r'<meta name="fn-date" content="(\d{4}-\d{2}-\d{2})">', page).group(1)
    block = re.search(r'id="scriptText">(.*?)</div>\s*</details>', page, re.S).group(1)
    segs = re.findall(r'<div data-seg="\d+"[^>]*>(.*?)</div>', block, re.S)
    if not segs:
        sys.exit("No audio script segments found in the page")

    ensure_piper()
    ensure_voice()
    from piper import PiperVoice
    voice = PiperVoice.load(VOICE)
    rate = voice.config.sample_rate
    silence = lambda s: b"\x00\x00" * int(rate * s)

    pcm, starts = bytearray(), []
    for seg in segs:
        starts.append(round(len(pcm) / 2 / rate, 2))
        for para in re.findall(r"<p>(.*?)</p>", seg, re.S):
            buf = io.BytesIO()
            with wave.open(buf, "wb") as w:
                voice.synthesize_wav(speakable(para), w)
            buf.seek(0)
            with wave.open(buf) as r:
                pcm += r.readframes(r.getnframes())
            pcm += silence(PARA_GAP)
        pcm += silence(SEG_GAP)
    dur = round(len(pcm) / 2 / rate, 1)

    os.makedirs(os.path.join(ROOT, "audio"), exist_ok=True)
    wav_path = os.path.join(ROOT, "audio", date + ".wav")
    mp3_path = os.path.join(ROOT, "audio", date + ".mp3")
    with wave.open(wav_path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate); w.writeframes(bytes(pcm))
    subprocess.check_call([ffmpeg_bin(), "-y", "-loglevel", "error", "-i", wav_path,
                           "-ac", "1", "-b:a", "48k", mp3_path])
    os.remove(wav_path)

    meta = json.dumps({"starts": starts, "dur": dur})
    page = re.sub(r'(<script type="application/json" id="audio-meta">).*?(</script>)',
                  lambda m: m.group(1) + meta + m.group(2), page, flags=re.S)
    page = re.sub(r'<audio id="aud"[^>]*></audio>',
                  '<audio id="aud" preload="metadata" src="../audio/%s.mp3"></audio>' % date, page)
    open(page_path, "w", encoding="utf-8").write(page)
    print("Audio: %s, %.0f s, %d segments" % (mp3_path, dur, len(starts)))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
