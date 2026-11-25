import os, json, re, random, subprocess, textwrap, urllib.parse, urllib.request, urllib.error
from pathlib import Path
from PIL import Image, ImageOps, ImageEnhance
import google.generativeai as genai
import edge_tts

OUT = Path("output")
OUT.mkdir(exist_ok=True)
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

# Stable fallback photo URLs from Unsplash (automotive-themed). Used only if all
# searchable providers fail; image fetch failures are skipped and retried.
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
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

def gemini_json(prompt):
    if not GEMINI_KEY:
        raise RuntimeError("GEMINI_API_KEY secret is missing.")
    genai.configure(api_key=GEMINI_KEY)
    model = genai.GenerativeModel(MODEL)
    response = model.generate_content(prompt)
    raw = response.text.strip()
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.I)
    return json.loads(raw)

def create_story():
    prompt = """Create a factual, engaging 45-55 second Hinglish automotive short for Indian viewers.
Choose a fresh interesting topic from car/bike engineering, technology, myths, history or unusual facts.
Avoid made-up claims. If a fact is uncertain, phrase it cautiously. Output ONLY valid JSON:
{
 "title":"short catchy title",
 "topic":"subject",
 "narration":"natural spoken Hinglish, 110-135 words, no headings, pronounceable, one strong opening hook and ending question",
 "searches":["8 short broad image search terms, 2-5 words each, automotive visuals"]
}
Make searches visually varied and suitable for relevant documentary photos."""
    try:
        d = gemini_json(prompt)
        if not isinstance(d.get("searches"), list):
            d["searches"] = [d.get("topic","car technology"), "automotive engine", "car interior", "motorcycle"]
        return d
    except Exception as e:
        print("Script generation fallback:", repr(e))
        return {
            "title":"Machine Ka Raaz: Engine Kaise Kaam Karta Hai?",
            "topic":"How a combustion engine works",
            "narration":"Kabhi socha hai, ek chhota sa spark poori gaadi ko kaise chala deta hai? Engine ke andar piston hawa aur fuel ke mixture ko compress karta hai. Phir spark plug ignition karta hai, aur combustion se pressure banta hai. Ye pressure piston ko neeche dhakelta hai. Connecting rod isi movement ko crankshaft ke rotation mein badalti hai. Aur wahi rotation transmission ke through wheels tak pahunchta hai. Har second engine ke andar ye cycle kai baar repeat hoti hai. Isi liye engine ki timing, cooling aur lubrication itni important hoti hai. Machine ka raaz ye hai—power ek explosion se nahi, controlled cycles se milti hai. Tum next kis machine ka raaz jaan-na chahoge?",
            "searches":["car engine","piston crankshaft","spark plug","engine assembly","car dashboard","automotive workshop","engine block","motorcycle engine"]
        }

def commons_search(query, limit=12):
    api = "https://commons.wikimedia.org/w/api.php"
    params = {
        "action":"query", "format":"json", "generator":"search",
        "gsrsearch":"filetype:bitmap " + query, "gsrnamespace":6,
        "gsrlimit":limit, "prop":"imageinfo", "iiprop":"url|extmetadata",
        "iiurlwidth":1280
    }
    url = api + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent":"TorqueNautFactory/1.0 (automated video creator)"})
    with urllib.request.urlopen(req, timeout=20) as r:
        data = json.load(r)
    pages = data.get("query", {}).get("pages", {})
    out=[]
    for p in pages.values():
        info=(p.get("imageinfo") or [{}])[0]
        url=info.get("thumburl") or info.get("url")
        if url:
            meta=info.get("extmetadata",{})
            artist=meta.get("Artist",{}).get("value","")
            out.append((url, artist, p.get("title","")))
    return out

def download_image(url, path):
    req=urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0 TORQUENAUT video generator"})
    with urllib.request.urlopen(req, timeout=25) as r:
        data=r.read()
    path.write_bytes(data)
    im=Image.open(path)
    im.verify()
    im=Image.open(path).convert("RGB")
    im=ImageOps.fit(im, (1080,1920), method=Image.Resampling.LANCZOS)
    im=ImageEnhance.Contrast(im).enhance(1.12)
    im=ImageEnhance.Color(im).enhance(1.08)
    im.save(path, "JPEG", quality=90)
    return True

def fetch_images(searches, count=8):
    candidates=[]
    # Search multiple variations; one failed Commons search should never end the run.
    for query in searches:
        try:
            results=commons_search(query, 10)
            random.shuffle(results)
            candidates.extend(results)
            print(f"Commons '{query}': {len(results)} results")
        except Exception as e:
            print(f"Commons query failed ({query}): {e}")
    # Deduplicate source URLs
    seen=set()
    usable=[]
    for url,artist,title in candidates:
        if url in seen: continue
        seen.add(url)
        dest=OUT / f"image_{len(usable)+1:02d}.jpg"
        try:
            download_image(url,dest)
            usable.append((dest,artist,title))
            if len(usable)>=count: break
        except Exception as e:
            dest.unlink(missing_ok=True)
            print("Skip unusable Commons image:", str(e)[:180])
    # Backup photo provider, no key needed; if Commons has too few images.
    if len(usable)<4:
        fallback=FALLBACK_PHOTOS[:]
        random.shuffle(fallback)
        for url in fallback:
            if len(usable)>=count: break
            dest=OUT / f"fallback_{len(usable)+1:02d}.jpg"
            try:
                download_image(url,dest)
                usable.append((dest,"Unsplash photo","Unsplash fallback photo"))
            except Exception as e:
                dest.unlink(missing_ok=True)
                print("Fallback image failed:",str(e)[:150])
    if len(usable)<4:
        raise RuntimeError(f"Only {len(usable)} images downloaded after Commons and fallback attempts.")
    return usable

async def make_voice(text, mp3):
    # Use a stable Hindi voice; if this voice endpoint fails, retry with another.
    for voice in ["hi-IN-MadhurNeural","hi-IN-SwaraNeural"]:
        try:
            communicate=edge_tts.Communicate(text, voice, rate="-3%", pitch="-1Hz")
            await communicate.save(str(mp3))
            return
        except Exception as e:
            print("TTS voice failed:",voice,repr(e))
    raise RuntimeError("Both Hindi TTS voices failed.")

def make_subtitles(narration, duration, srt):
    # Approximate subtitle timing by spoken word count, break into readable 5-7 word lines.
    words=narration.split()
    chunks=[]
    for i in range(0,len(words),6):
        chunks.append(" ".join(words[i:i+6]))
    total=sum(max(1,len(c.split())) for c in chunks)
    t=0.0
    lines=[]
    for i,c in enumerate(chunks):
        span=duration*len(c.split())/total
        start=t
        end=min(duration,t+span)
        lines.append((start,end,c))
        t=end
    def stamp(sec):
        ms=int(sec*1000); h=ms//3600000; ms%=3600000; m=ms//60000; ms%=60000; s=ms//1000; ms%=1000
        return f"{h:02}:{m:02}:{s:02},{ms:03}"
    with open(srt,"w",encoding="utf-8") as f:
        for idx,(a,b,txt) in enumerate(lines,1):
            f.write(f"{idx}\\n{stamp(a)} --> {stamp(b)}\\n{txt}\\n\\n")

def assemble(images, voice, duration, output):
    # Split video into image segments, varied motion, documentary-style grading.
    segdur=duration/len(images)
    segments=[]
    for idx,(path,artist,title) in enumerate(images):
        seg=OUT/f"segment_{idx:02d}.mp4"
        # Motion variation; subtle slow pan/zoom.
        zoom_modes=[
            "zoompan=z='min(1+0.00013*on,1.12)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=900:fps=30",
            "zoompan=z='max(1.0,1.12-0.00013*on)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=900:fps=30",
            "zoompan=z='1.10':x='(iw-iw/zoom)*on/(d-1)':y='ih/2-(ih/zoom/2)':d=900:fps=30",
            "zoompan=z='1.10':x='(iw-iw/zoom)*(1-on/(d-1))':y='ih/2-(ih/zoom/2)':d=900:fps=30",
        ]
        filt=zoom_modes[idx%len(zoom_modes)]
        run(["ffmpeg","-y","-loop","1","-i",str(path),"-t",str(segdur),
             "-vf",f"{filt},fps=30,scale=1080:1920,setsar=1",
             "-c:v","libx264","-preset","ultrafast","-pix_fmt","yuv420p","-an",str(seg)])
        segments.append(seg)
    concat=OUT/"concat.txt"
    concat.write_text("".join(f"file '{p.resolve()}'\\n" for p in segments),encoding="utf-8")
    silent=OUT/"silent.mp4"
    run(["ffmpeg","-y","-f","concat","-safe","0","-i",str(concat),"-c","copy",str(silent)])
    # Bold styled subtitles: yellow text, black outline, semi-transparent shadow.
    srt=OUT/"captions.srt"
    make_subtitles(narration,duration,srt)
    escaped=str(srt.resolve()).replace("\\\\","/").replace(":","\\\\:")
    vf=f"subtitles='{escaped}':force_style='FontName=DejaVu Sans,FontSize=19,Bold=1,PrimaryColour=&H0000FFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=4,Shadow=2,Alignment=2,MarginV=190'"
    run(["ffmpeg","-y","-i",str(silent),"-i",str(voice),"-vf",vf,"-c:v","libx264","-preset","veryfast","-pix_fmt","yuv420p","-c:a","aac","-b:a","160k","-shortest",str(output)])

def main():
    story=create_story()
    print("Topic:",story.get("topic"))
    print("Title:",story.get("title"))
    images=fetch_images(story.get("searches",[]),8)
    import asyncio
    voice=OUT/"voice.mp3"
    asyncio.run(make_voice(story["narration"],voice))
    probe=subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1",str(voice)],capture_output=True,text=True,check=True)
    duration=float(probe.stdout.strip())
    output=OUT/"torquenaut_reel.mp4"
    assemble(images,voice,duration,output)
    # Metadata/post copy
    copy=f"""TITLE: {story.get('title','Machine Ka Raaz')}\\n\\nCAPTION:\\n{story['narration']}\\n\\nHASHTAGS:\\n#MachineKaRaaz #TorqueNaut #Cars #Bikes #Automotive #Engineering #HindiFacts #Reels #Shorts"""
    (OUT/"posting_copy.txt").write_text(copy,encoding="utf-8")
    (OUT/"image_sources.txt").write_text("\\n".join(f"{title} | creator: {artist} | {path.name}" for path,artist,title in images),encoding="utf-8")
    print("Created:",output)

if __name__=="__main__":
    main()
