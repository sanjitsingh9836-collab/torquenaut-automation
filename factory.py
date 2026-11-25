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

        if
