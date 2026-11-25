import os, json, re, random, subprocess, urllib.parse, urllib.request, asyncio, shutil
from pathlib import Path
from PIL import Image, ImageOps, ImageEnhance
from edge_tts import Communicate

OUT = Path("output")
OUT.mkdir(exist_ok=True)

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

FALLBACK_PHOTOS = [
    "https://images.unsplash.com/photo-1503376780353-7e6692767b70?auto=format&fit=crop&w=1280&q=85",
    "https://images.unsplash.com/photo-1492144534655-ae79c964c9d7?auto=format&fit=crop&w=1280&q=85",
    "https://images.unsplash.com/photo-1503736334956-4c8f8e92946d?auto=format&fit=crop&w=1280&q=85",
    "https://images.unsplash.com/photo-1511919884226-fd3cad34687c?auto=format&fit=crop&w=1280&q=85",
    "https://images.unsplash.com/photo-1504215680853-026ed2a45def?auto=format&fit=crop&w=1280&q=85",
    "https://images.unsplash.com/photo-1517524206127-48bbd363f3d7?auto=format&fit=crop&w=1280&q=85",
    "https://images.unsplash.com/photo-1552519507-da3b142c6e3d?auto=format&fit=crop&w=1280&q=85",
    "https://images.unsplash.com/photo-1549317661-bd32c8ce0db2?auto=format&fit=crop&w=1280&q=85",
]


def run(cmd):
    p = subprocess.run(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True
    )

    if p.returncode:
        raise RuntimeError(
            "Command failed: "
            + " ".join(cmd)
            + "\n"
            + p.stderr[-2500:]
        )


def gemini_json(prompt):
    if not GEMINI_KEY:
        raise RuntimeError("GEMINI_API_KEY secret is missing.")

    from google import genai

    client = genai.Client(api_key=GEMINI_KEY)

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt
    )

    raw = (response.text or "").strip()

    raw = re.sub(
        r"^```(?:json)?\s*|\s*```$",
        "",
        raw,
        flags=re.I
    )

    return json.loads(raw)


def create_story():

    prompt = """
Create one factual, engaging 45-55 second Hinglish automotive short
for Indian viewers.

Choose a fresh topic about:
cars, bikes, engineering, technology, myths, history,
mechanics, unusual facts or automotive secrets.

The content should be interesting and easy to understand.

Do not invent facts.

The opening must have a powerful hook.

The ending should make viewers comment.

Output ONLY valid JSON:

{
"title":"short catchy title",
"topic":"subject",
"narration":"natural spoken Hinglish, about 105-125 words, strong hook, ending question",
"searches":["8 image search phrases, 2-5 words each"]
}
"""

    try:

        d = gemini_json(prompt)

        if not isinstance(d.get("searches"), list):
            d["searches"] = [
                d.get("topic", "automotive"),
                "car engine",
                "motorcycle"
            ]

        if not d.get("narration") or not d.get("title"):
            raise ValueError("Incomplete script response")

        return d

    except Exception as e:

        print("Script generation fallback:", repr(e))

        return {
            "title": "Machine Ka Raaz: Engine Kaise Kaam Karta Hai?",
            "topic": "Combustion engine basics",

            "narration": """
Kabhi socha hai, ek chhota sa spark poori gaadi
ko kaise chala deta hai?

Engine ke andar piston hawa aur fuel ke mixture
ko compress karta hai.

Phir spark plug ignition karta hai aur combustion
se pressure banta hai.

Ye pressure piston ko neeche dhakelta hai.

Connecting rod is movement ko crankshaft ke
rotation mein badalti hai.

Aur wahi rotation transmission ke through
wheels tak pahunchta hai.

Engine ke andar ye cycle baar baar repeat hoti hai.

Isi liye timing, cooling aur lubrication
bahut important hain.

Machine ka raaz ye hai:
power sirf ek blast se nahi,
controlled cycles se milti hai.

Tum next kis machine ka raaz jaan-na chahoge?
""".strip(),

            "searches": [
                "car engine",
                "piston crankshaft",
                "spark plug",
                "engine assembly",
                "car dashboard",
                "automotive workshop",
                "engine block",
                "motorcycle engine"
            ]
        }


def commons_search(query, limit=10):

    params = {
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrsearch": "filetype:bitmap " + query,
        "gsrnamespace": 6,
        "gsrlimit": limit,
        "prop": "imageinfo",
        "iiprop": "url|extmetadata",
        "iiurlwidth": 1280
    }

    url = (
        "https://commons.wikimedia.org/w/api.php?"
        + urllib.parse.urlencode(params)
    )

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent":
            "TorqueNautFactory/2.0 (automated creator)"
        }
    )

    with urllib.request.urlopen(req, timeout=25) as r:
        data = json.load(r)

    out = []

    for p in data.get("query", {}).get("pages", {}).values():

        info = (p.get("imageinfo") or [{}])[0]

        u = info.get("thumburl") or info.get("url")

        if u:

            meta = info.get("extmetadata", {})

            out.append(
                (
                    u,
                    meta.get("Artist", {}).get("value", ""),
                    p.get("title", "")
                )
            )

    return out


def download_image(url, path):

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent":
            "Mozilla/5.0 TORQUENAUT creator"
        }
    )

    with urllib.request.urlopen(req, timeout=30) as r:
        path.write_bytes(r.read())

    with Image.open(path) as im:

        im = im.convert("RGB")

        im = ImageOps.fit(
            im,
            (1080, 1920),
            method=Image.Resampling.LANCZOS
        )

        im = ImageEnhance.Contrast(im).enhance(1.08)

        im = ImageEnhance.Color(im).enhance(1.05)

        im.save(
            path,
            "JPEG",
            quality=90,
            optimize=True
        )


def fetch_images(searches, count=8):

    candidates = []

    for q in searches:

        try:

            found = commons_search(q, 10)

            random.shuffle(found)

            candidates.extend(found)

            print(
                f"Commons '{q}': "
                f"{len(found)} results"
            )

        except Exception as e:

            print(
                "Commons search skipped:",
                q,
                str(e)[:160]
            )

    seen = set()

    usable = []

    for u, artist, title in candidates:

        if u in seen:
            continue

        seen.add(u)

        dest = OUT / f"image_{len(usable)+1:02d}.jpg"

        try:

            download_image(u, dest)

            usable.append(
                (dest, artist, title)
            )

            if len(usable) >= count:
                break

        except Exception as e:

            dest.unlink(missing_ok=True)

            print(
                "Image skipped:",
                str(e)[:160]
            )

    if len(usable) < count:

        fallback = FALLBACK_PHOTOS[:]

        random.shuffle(fallback)

        for u in fallback:

            if len(usable) >= count:
                break

            dest = OUT / f"fallback_{len(usable)+1:02d}.jpg"

            try:

                download_image(u, dest)

                usable.append(
                    (
                        dest,
                        "Unsplash",
                        "Fallback photo"
                    )
                )

            except Exception as e:

                dest.unlink(missing_ok=True)

                print(
                    "Fallback skipped:",
                    str(e)[:100]
                )

    if len(usable) < 4:

        raise RuntimeError(
            f"Not enough usable images ({len(usable)}); need at least 4."
        )

    return usable


async def make_voice(text, mp3):

    voices = [
        "hi-IN-MadhurNeural",
        "hi-IN-SwaraNeural",
        "hi-IN-NeerjaNeural",
        "hi-IN-PrabhatNeural"
    ]

    for voice in voices:

        try:

            await Communicate(
                text,
                voice,
                rate="-2%",
                pitch="+0Hz"
            ).save(str(mp3))

            if mp3.exists() and mp3.stat().st_size > 1000:

                print("Voice selected:", voice)

                return

        except Exception as e:

            mp3.unlink(missing_ok=True)

            print(
                "Voice failed:",
                voice,
                repr(e)
            )

    # Backup voice service

    try:

        from gtts import gTTS

        gTTS(
            text=text,
            lang="hi",
            slow=False
        ).save(str(mp3))

        if mp3.exists() and mp3.stat().st_size > 1000:

            print(
                "Voice selected: gTTS Hindi fallback"
            )

            return

    except Exception as e:

        print(
            "gTTS fallback failed:",
            repr(e)
        )

    raise RuntimeError(
        "All voice services failed. Retry workflow later."
    )


def make_subtitles(text, duration, srt):

    words = text.split()

    chunks = [
        " ".join(words[i:i+6])
        for i in range(0, len(words), 6)
    ]

    total = sum(
        len(c.split())
        for c in chunks
    ) or 1

    t = 0

    entries = []

    for c in chunks:

        span = (
            duration
            * len(c.split())
            / total
        )

        entries.append(
            (
                t,
                min(duration, t + span),
                c
            )
        )

        t += span

    def stamp(sec):

        ms = max(0, int(sec * 1000))

        h = ms // 3600000

        ms %= 3600000

        m = ms // 60000

        ms %= 60000

        s = ms // 1000

        ms %= 1000

        return (
            f"{h:02}:{m:02}:{s:02},{ms:03}"
        )

    with open(
        srt,
        "w",
        encoding="utf-8"
    ) as f:

        for i, (a, b, txt) in enumerate(
            entries,
            1
        ):

            f.write(
                f"{i}\n"
                f"{stamp(a)} --> {stamp(b)}\n"
                f"{txt}\n\n"
            )


def assemble(images, voice, duration, output):

    # Reliable rendering without zoompan.

    segdur = duration / len(images)

    segments = []

    for i, (path, artist, title) in enumerate(images):

        seg = OUT / f"segment_{i:02d}.mp4"

        run([
            "ffmpeg",
            "-y",
            "-loop", "1",
            "-framerate", "30",
            "-i", str(path),
            "-t", f"{segdur:.4f}",
            "-vf",
            (
                "scale=1080:1920:"
                "force_original_aspect_ratio=increase,"
                "crop=1080:1920,"
                "fps=30,"
                "setsar=1"
            ),
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-pix_fmt", "yuv420p",
            "-an",
            str(seg)
        ])

        segments.append(seg)

    concat = OUT / "concat.txt"

    concat.write_text(
        "".join(
            "file '"
            + p.resolve().as_posix()
            + "'\n"
            for p in segments
        ),
        encoding="utf-8"
    )

    silent = OUT / "silent.mp4"

    run([
        "ffmpeg",
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat),
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-pix_fmt", "yuv420p",
        "-an",
        str(silent)
    ])

    srt = OUT / "captions.srt"

    make_subtitles(
        narration,
        duration,
        srt
    )

    srt_path = (
        srt.resolve()
        .as_posix()
        .replace(":", "\\:")
    )

    style = (
        "FontName=DejaVu Sans,"
        "FontSize=20,"
        "Bold=1,"
        "PrimaryColour=&H0000FFFF,"
        "OutlineColour=&H00000000,"
        "BorderStyle=1,"
        "Outline=3,"
        "Shadow=1,"
        "Alignment=2,"
        "MarginV=170"
    )

    vf = (
        f"subtitles='{srt_path}':"
        f"force_style='{style}'"
    )

    run([
        "ffmpeg",
        "-y",
        "-i", str(silent),
        "-i", str(voice),
        "-vf", vf,
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "160k",
        "-shortest",
        str(output)
    ])


def main():

    # Remove old output files

    for p in OUT.iterdir():

        if p.is_file():
            p.unlink()

    story = create_story()

    print(
        "Topic:",
        story.get("topic")
    )

    print(
        "Title:",
        story.get("title")
    )

    images = fetch_images(
        story.get("searches", []),
        8
    )

    voice = OUT / "voice.mp3"

    asyncio.run(
        make_voice(
            story["narration"],
            voice
        )
    )

    probe = subprocess.run(
        [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(voice)
        ],
        capture_output=True,
        text=True,
        check=True
    )

    duration = float(
        probe.stdout.strip()
    )

    output = OUT / "torquenaut_reel.mp4"

    assemble(
        images,
        voice,
        duration,
        output
    )

    copy = (
        f"TITLE: {story.get('title', 'Machine Ka Raaz')}\n\n"
        f"CAPTION:\n{story['narration']}\n\n"
        "HASHTAGS:\n"
        "#MachineKaRaaz #TorqueNaut #Cars #Bikes "
        "#Automotive #Engineering #HindiFacts "
        "#Reels #Shorts"
    )

    (
        OUT / "posting_copy.txt"
    ).write_text(
        copy,
        encoding="utf-8"
    )

    (
        OUT / "image_sources.txt"
    ).write_text(
        "\n".join(
            f"{title} | creator: {artist} | file: {path.name}"
            for path, artist, title in images
        ),
        encoding="utf-8"
    )

    print(
        "SUCCESS - Video created:",
        output
    )


if __name__ == "__main__":
    main()
