import os
import json
import re
import random
import subprocess
import urllib.parse
import urllib.request
import asyncio
import shutil
from pathlib import Path

from PIL import Image, ImageOps, ImageEnhance
from edge_tts import Communicate


# ============================================================
# TORQUENAUT AUTOMATIC VIDEO FACTORY
# ============================================================

OUT = Path("output")
OUT.mkdir(exist_ok=True)

MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.5-flash-lite"
)

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


# ============================================================
# UTILITIES
# ============================================================

def run(cmd):

    p = subprocess.run(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True
    )

    if p.returncode != 0:

        raise RuntimeError(
            "Command failed:\n"
            + " ".join(cmd)
            + "\n\n"
            + p.stderr[-3000:]
        )


def clean_output():

    for p in OUT.iterdir():

        if p.is_file():
            p.unlink()

        elif p.is_dir():
            shutil.rmtree(p)


# ============================================================
# AI SCRIPT GENERATION
# ============================================================

def gemini_json(prompt):

    if not GEMINI_KEY:

        raise RuntimeError(
            "GEMINI_API_KEY secret is missing."
        )

    from google import genai

    client = genai.Client(
        api_key=GEMINI_KEY
    )

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt
    )

    raw = (
        response.text or ""
    ).strip()

    raw = re.sub(
        r"^```(?:json)?\s*|\s*```$",
        "",
        raw,
        flags=re.I
    )

    return json.loads(raw)


def create_story():

    prompt = """
You are a professional automotive content creator.

Create one fascinating, factual, high-retention
short video for an Indian audience.

CONTENT:
Cars, motorcycles, automotive engineering,
technology, history, myths, mechanics,
unusual facts and hidden machine secrets.

SERIES:
MACHINE KA RAAZ

BRAND:
TORQUENAUT

AUDIENCE:
Indian viewers who understand Hindi and Hinglish.

VIDEO:
45-60 seconds.

SCRIPT REQUIREMENTS:

1. Start with a powerful curiosity hook.
2. Use natural spoken Hinglish.
3. Avoid robotic textbook language.
4. Explain the science simply.
5. Include surprising information.
6. Keep sentences short.
7. Make the narration exciting.
8. Do not invent statistics.
9. End with a question encouraging comments.
10. Do not repeat recently overused topics if possible.

Return ONLY valid JSON:

{
"title":"Catchy video title",
"topic":"Topic name",
"narration":"Complete spoken Hinglish narration",
"searches":[
"image search phrase 1",
"image search phrase 2",
"image search phrase 3",
"image search phrase 4",
"image search phrase 5",
"image search phrase 6",
"image search phrase 7",
"image search phrase 8"
]
}
"""

    try:

        story = gemini_json(prompt)

        if not story.get("title"):
            raise ValueError("Missing title")

        if not story.get("narration"):
            raise ValueError("Missing narration")

        if not isinstance(
            story.get("searches"),
            list
        ):

            story["searches"] = [
                story.get("topic", "automotive"),
                "car engine",
                "motorcycle engineering"
            ]

        print("AI topic:", story.get("topic"))

        print("AI title:", story.get("title"))

        return story

    except Exception as e:

        print(
            "AI script fallback:",
            repr(e)
        )

        return {

            "title":
            "Machine Ka Raaz: Engine Ki Power",

            "topic":
            "How engines work",

            "narration": """
Kabhi socha hai, engine ke andar
itni power aati kahan se hai?

Jab tum gaadi start karte ho,
engine ke cylinders ke andar
hawa aur fuel mix hote hain.

Piston is mixture ko compress karta hai.

Phir spark plug ignition karta hai,
aur pressure piston ko neeche dhakelta hai.

Connecting rod is movement ko
crankshaft ki rotation mein badal deti hai.

Aur isi rotation se wheels ko power milti hai.

Lekin engine ka asli raaz sirf power nahi hai.

Perfect timing, lubrication aur cooling
ke bina engine kuch hi der mein damage ho sakta hai.

Isi liye ek engine ke andar
hazaaron parts ek saath perfectly kaam karte hain.

Machine Ka Raaz.

Agli baar kis machine ka secret jaan-na hai?
""".strip(),

            "searches": [
                "automotive engine",
                "engine piston",
                "spark plug",
                "crankshaft",
                "car engine parts",
                "mechanic workshop",
                "motorcycle engine",
                "sports car"
            ]
        }


# ============================================================
# IMAGE SEARCH
# ============================================================

def commons_search(query, limit=10):

    params = {

        "action": "query",

        "format": "json",

        "generator": "search",

        "gsrsearch":
        "filetype:bitmap " + query,

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
            "TorqueNautFactory/3.0"
        }
    )

    with urllib.request.urlopen(
        req,
        timeout=30
    ) as r:

        data = json.load(r)

    results = []

    pages = (
        data.get("query", {})
        .get("pages", {})
        .values()
    )

    for page in pages:

        info = (
            page.get("imageinfo")
            or [{}]
        )[0]

        url = (
            info.get("thumburl")
            or info.get("url")
        )

        if not url:
            continue

        metadata = (
            info.get("extmetadata")
            or {}
        )

        artist = (
            metadata.get("Artist", {})
            .get("value", "")
        )

        results.append(
            (
                url,
                artist,
                page.get("title", "")
            )
        )

    return results


# ============================================================
# IMAGE DOWNLOAD AND PROCESSING
# ============================================================

def download_image(url, path):

    req = urllib.request.Request(

        url,

        headers={
            "User-Agent":
            "Mozilla/5.0 TORQUENAUT"
        }
    )

    with urllib.request.urlopen(
        req,
        timeout=35
    ) as r:

        path.write_bytes(
            r.read()
        )

    with Image.open(path) as image:

        image = image.convert("RGB")

        image = ImageOps.fit(

            image,

            (1080, 1920),

            method=Image.Resampling.LANCZOS
        )

        image = ImageEnhance.Contrast(
            image
        ).enhance(1.07)

        image = ImageEnhance.Color(
            image
        ).enhance(1.06)

        image = ImageEnhance.Sharpness(
            image
        ).enhance(1.12)

        image.save(

            path,

            "JPEG",

            quality=91,

            optimize=True
        )


def fetch_images(searches, count=8):

    candidates = []

    for query in searches:

        try:

            found = commons_search(
                query,
                limit=10
            )

            random.shuffle(found)

            candidates.extend(found)

            print(
                f"Image search '{query}': "
                f"{len(found)} results"
            )

        except Exception as e:

            print(
                "Search failed:",
                query,
                str(e)[:150]
            )

    usable = []

    seen = set()

    for url, artist, title in candidates:

        if url in seen:
            continue

        seen.add(url)

        path = OUT / (
            f"image_{len(usable)+1:02d}.jpg"
        )

        try:

            download_image(
                url,
                path
            )

            usable.append(
                (
                    path,
                    artist,
                    title
                )
            )

            print(
                "Image downloaded:",
                path.name
            )

            if len(usable) >= count:
                break

        except Exception as e:

            path.unlink(
                missing_ok=True
            )

            print(
                "Image failed:",
                str(e)[:150]
            )

    # Backup image sources

    if len(usable) < count:

        backups = FALLBACK_PHOTOS[:]

        random.shuffle(backups)

        for url in backups:

            if len(usable) >= count:
                break

            path = OUT / (
                f"backup_{len(usable)+1:02d}.jpg"
            )

            try:

                download_image(
                    url,
                    path
                )

                usable.append(
                    (
                        path,
                        "Unsplash",
                        "Backup image"
                    )
                )

                print(
                    "Backup image:",
                    path.name
                )

            except Exception as e:

                path.unlink(
                    missing_ok=True
                )

                print(
                    "Backup failed:",
                    str(e)[:100]
                )

    if len(usable) < 4:

        raise RuntimeError(
            "Could not download enough images."
        )

    return usable


# ============================================================
# AI VOICE GENERATION
# ============================================================

async def generate_voice(
    narration,
    output
):

    voices = [

        "hi-IN-SwaraNeural",

        "hi-IN-NeerjaNeural",

        "hi-IN-MadhurNeural",

        "hi-IN-PrabhatNeural"
    ]

    for voice in voices:

        try:

            output.unlink(
                missing_ok=True
            )

            await Communicate(

                text=narration,

                voice=voice,

                rate="-3%",

                pitch="+0Hz",

                volume="+0%"
            ).save(
                str(output)
            )

            if (

                output.exists()

                and output.stat().st_size > 1000

            ):

                print(
                    "Voice successful:",
                    voice
                )

                return

        except Exception as e:

            output.unlink(
                missing_ok=True
            )

            print(
                "Voice failed:",
                voice,
                repr(e)
            )

    # Google TTS backup

    try:

        from gtts import gTTS

        output.unlink(
            missing_ok=True
        )

        gTTS(

            text=narration,

            lang="hi",

            slow=False

        ).save(
            str(output)
        )

        if (

            output.exists()

            and output.stat().st_size > 1000

        ):

            print(
                "Using Google TTS fallback"
            )

            return

    except Exception as e:

        print(
            "Google TTS failed:",
            repr(e)
        )

    raise RuntimeError(
        "All voice services failed."
    )


# ============================================================
# AUDIO DURATION
# ============================================================

def get_audio_duration(audio):

    result = subprocess.run(

        [

            "ffprobe",

            "-v",
            "error",

            "-show_entries",
            "format=duration",

            "-of",

            "default=noprint_wrappers=1:nokey=1",

            str(audio)

        ],

        capture_output=True,

        text=True,

        check=True
    )

    return float(
        result.stdout.strip()
    )


# ============================================================
# SUBTITLES
# ============================================================

def make_subtitles(
    narration,
    duration,
    srt
):

    words = narration.split()

    if not words:
        raise RuntimeError(
            "Narration is empty."
        )

    # Short subtitle phrases

    chunks = [

        " ".join(
            words[i:i+5]
        )

        for i in range(
            0,
            len(words),
            5
        )
    ]

    total_words = sum(
        len(chunk.split())
        for chunk in chunks
    )

    current_time = 0

    entries = []

    for chunk in chunks:

        chunk_words = len(
            chunk.split()
        )

        span = (
            duration
            * chunk_words
            / total_words
        )

        start = current_time

        end = min(
            duration,
            current_time + span
        )

        entries.append(
            (
                start,
                end,
                chunk
            )
        )

        current_time += span

    def timestamp(seconds):

        milliseconds = int(
            seconds * 1000
        )

        hours = (
            milliseconds
            // 3600000
        )

        milliseconds %= 3600000

        minutes = (
            milliseconds
            // 60000
        )

        milliseconds %= 60000

        secs = (
            milliseconds
            // 1000
        )

        milliseconds %= 1000

        return (
            f"{hours:02}:"
            f"{minutes:02}:"
            f"{secs:02},"
            f"{milliseconds:03}"
        )

    with open(
        srt,
        "w",
        encoding="utf-8"
    ) as file:

        for number, entry in enumerate(
            entries,
            start=1
        ):

            start, end, text = entry

            file.write(

                f"{number}\n"

                f"{timestamp(start)} --> "
                f"{timestamp(end)}\n"

                f"{text}\n\n"
            )


# ============================================================
# VIDEO RENDERING
# ============================================================

def assemble(
    images,
    voice,
    duration,
    output,
    narration
):

    print(
        "Starting video rendering..."
    )

    segment_duration = (
        duration
        / len(images)
    )

    segments = []

    # Render individual scenes

    for index, image_info in enumerate(
        images
    ):

        image_path = image_info[0]

        segment = OUT / (
            f"segment_{index:02d}.mp4"
        )

        print(
            "Rendering scene:",
            index + 1,
            "/",
            len(images)
        )

        run([

            "ffmpeg",

            "-y",

            "-loop",
            "1",

            "-framerate",
            "30",

            "-i",
            str(image_path),

            "-t",
            f"{segment_duration:.4f}",

            "-vf",

            (
                "scale=1080:1920:"
                "force_original_aspect_ratio=increase,"
                "crop=1080:1920,"
                "fps=30,"
                "setsar=1"
            ),

            "-c:v",
            "libx264",

            "-preset",
            "ultrafast",

            "-pix_fmt",
            "yuv420p",

            "-an",

            str(segment)

        ])

        segments.append(
            segment
        )

    # Join scenes

    concat_file = OUT / "concat.txt"

    concat_file.write_text(

        "".join(

            "file '"
            + segment.resolve().as_posix()
            + "'\n"

            for segment in segments

        ),

        encoding="utf-8"
    )

    silent_video = OUT / "silent.mp4"

    print(
        "Joining video scenes..."
    )

    run([

        "ffmpeg",

        "-y",

        "-f",
        "concat",

        "-safe",
        "0",

        "-i",
        str(concat_file),

        "-c:v",
        "libx264",

        "-preset",
        "ultrafast",

        "-pix_fmt",
        "yuv420p",

        "-an",

        str(silent_video)

    ])

    # Generate subtitles

    subtitle_file = OUT / "captions.srt"

    make_subtitles(

        narration,

        duration,

        subtitle_file

    )

    # Subtitle formatting

    subtitle_path = (
        subtitle_file
        .resolve()
        .as_posix()
    )

    subtitle_path = (
        subtitle_path
        .replace(":", "\\:")
        .replace("'", "\\'")
    )

    style = (

        "FontName=DejaVu Sans,"

        "FontSize=21,"

        "Bold=1,"

        "PrimaryColour=&H0000FFFF,"

        "OutlineColour=&H00000000,"

        "BorderStyle=1,"

        "Outline=3,"

        "Shadow=1,"

        "Alignment=2,"

        "MarginV=170"

    )

    subtitle_filter = (

        f"subtitles='{subtitle_path}':"

        f"force_style='{style}'"

    )

    print(
        "Adding subtitles and audio..."
    )

    # Final video

    run([

        "ffmpeg",

        "-y",

        "-i",
        str(silent_video),

        "-i",
        str(voice),

        "-vf",
        subtitle_filter,

        "-c:v",
        "libx264",

        "-preset",
        "veryfast",

        "-pix_fmt",
        "yuv420p",

        "-c:a",
        "aac",

        "-b:a",
        "192k",

        "-shortest",

        "-movflags",
        "+faststart",

        str(output)

    ])

    print(
        "Rendering finished successfully!"
    )


# ============================================================
# CAPTION AND POSTING INFORMATION
# ============================================================

def create_posting_copy(story):

    title = story.get(
        "title",
        "Machine Ka Raaz"
    )

    narration = story.get(
        "narration",
        ""
    )

    caption = f"""
{title}

{narration}

Har machine ke andar chhupa hai ek raaz.

Follow TORQUENAUT for more automotive secrets.

#MachineKaRaaz #TorqueNaut #Automotive
#Cars #Bikes #Engineering #AutoFacts
#HindiFacts #CarFacts #BikeFacts
#ReelsIndia #YouTubeShorts #Technology
""".strip()

    return caption


# ============================================================
# MAIN FACTORY
# ============================================================

def main():

    print("=" * 50)

    print(
        "TORQUENAUT VIDEO FACTORY STARTED"
    )

    print("=" * 50)

    # Clear previous output

    clean_output()

    # Generate script

    story = create_story()

    narration = story["narration"]

    # Download images

    images = fetch_images(

        story.get(
            "searches",
            []
        ),

        count=8

    )

    # Generate voice

    voic
