import os, json, re, random, subprocess, urllib.parse, urllib.request, asyncio, shutil
from pathlib import Path
from PIL import Image, ImageOps, ImageEnhance
from edge_tts import Communicate

OUT=Path("output"); OUT.mkdir(exist_ok=True)
IMAGE_SOURCES=[]
KEY=os.getenv("GEMINI_API_KEY")
MODEL=os.getenv("GEMINI_MODEL","gemini-3.8-flash")
W,H=1080,1920
FALLBACK=[
 "https://images.unsplash.com/photo-1503376780353-7e6692767b70?auto=format&fit=crop&w=1280&q=85",
 "https://images.unsplash.com/photo-1492144534655-ae79c964c9d7?auto=format&fit=crop&w=1280&q=85",
 "https://images.unsplash.com/photo-1503736334956-4c8f8e92946d?auto=format&fit=crop&w=1280&q=85",
 "https://images.unsplash.com/photo-1511919884226-fd3cad34687c?auto=format&fit=crop&w=1280&q=85",
 "https://images.unsplash.com/photo-1504215680853-026ed2a45def?auto=format&fit=crop&w=1280&q=85",
 "https://images.unsplash.com/photo-1552519507-da3b142c6e3d?auto=format&fit=crop&w=1280&q=85",
 "https://images.unsplash.com/photo-1549317661-bd32c8ce0db2?auto=format&fit=crop&w=1280&q=85",
 "https://images.unsplash.com/photo-1517524206127-48bbd363f3d7?auto=format&fit=crop&w=1280&q=85"]
def run(cmd):
 p=subprocess.run(cmd,capture_output=True,text=True)
 if p.returncode: raise RuntimeError("Command failed: "+ " ".join(cmd)+"\n"+p.stderr[-2500:])
def get_json(prompt):
 if not KEY: raise RuntimeError("GEMINI_API_KEY secret is missing")
 from google import genai
 c=genai.Client(api_key=KEY)
 res=c.models.generate_content(model=MODEL,contents=prompt)
 text=(res.text or "").strip()
 text=re.sub(r"^\s*```(?:json)?|\s*```\s*$","",text,flags=re.I)
 return json.loads(text)
def story():
 prompt="""Create a fresh, factual 45-55 second automotive short for Indian Hinglish viewers, series MACHINE KA RAAZ. Topic: cars, bikes, engineering, mechanisms, myths or history. Do not invent numbers or claims. Script should sound natural, energetic, conversational, concise. Hook in first 2 seconds, escalating curiosity, simple explanation, final comment question. Return JSON only: {title,topic,narration,searches:[8 visual search phrases]}. Narration in spoken Hinglish. Searches must be specific to this story, not generic car photos."""
 try:
  s=get_json(prompt)
  assert s.get("title") and s.get("narration")
  if not isinstance(s.get("searches"),list): s["searches"]=[]
  print("Topic:",s.get("topic"),"Title:",s["title"])
  return s
 except Exception as e:
  print("Script API failed, using fallback:",repr(e))
  return {"title":"Machine Ka Raaz: Turbo Kaise Power Badhata Hai?","topic":"Turbocharger","narration":"Socho, ek chhota sa device engine ki power ko kaafi badha sakta hai—bina engine ka size badhaye. Iska naam hai turbocharger. Engine se nikalne wali exhaust gas ek turbine ko ghumati hai. Ye turbine doosri side compressor ko chalata hai, jo engine mein zyada hawa push karta hai. Zyada hawa ka matlab fuel ko efficiently burn karne ka mauka, aur engine se extra power. Lekin turbo bahut garam hota hai, isliye cooling aur lubrication bahut important hai. Turbo ka raaz exhaust gas ko dobara kaam mein lagana hai. Tum naturally aspirated engine pasand karte ho ya turbo?","searches":["turbocharger cutaway","turbo turbine compressor","engine exhaust turbo","turbo boost pressure","car engine bay turbo","intercooler","turbocharger parts","sports car"]}
def commons(q):
 params={"action":"query","format":"json","generator":"search","gsrsearch":"filetype:bitmap "+q,"gsrnamespace":6,"gsrlimit":12,"prop":"imageinfo","iiprop":"url","iiurlwidth":1400}
 url="https://commons.wikimedia.org/w/api.php?"+urllib.parse.urlencode(params)
 req=urllib.request.Request(url,headers={"User-Agent":"TorqueNautFactory/4.0 (video automation)"})
 with urllib.request.urlopen(req,timeout=25) as f: data=json.load(f)
 pages=data.get("query",{}).get("pages",{}).values()
 return [((p.get("imageinfo") or [{}])[0].get("thumburl") or (p.get("imageinfo") or [{}])[0].get("url")) for p in pages]
def dl(url,path):
 req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 TorqueNaut"})
 with urllib.request.urlopen(req,timeout=35) as f: path.write_bytes(f.read())
 with Image.open(path) as im:
  im=ImageOps.fit(im.convert("RGB"),(W,H),method=Image.Resampling.LANCZOS)
  im=ImageEnhance.Contrast(im).enhance(1.08); im=ImageEnhance.Color(im).enhance(1.08)
  im.save(path,"JPEG",quality=90,optimize=True)
def images(queries):
 found=[]
 for q in queries:
  try:
   urls=commons(q)
   print("Commons search",q,"found",len(urls))
   for u in urls[:2]:
    if u and u not in found: found.append(u)
  except Exception as e: print("Commons error",str(e)[:160])
 paths=[]
 for u in found:
  p=OUT/f"scene_{len(paths)+1:02d}.jpg"
  try: dl(u,p); paths.append(p); IMAGE_SOURCES.append(u); print("Downloaded",p)
  except Exception as e: p.unlink(missing_ok=True); print("Image skipped",str(e)[:100])
  if len(paths)>=8: break
 for u in FALLBACK:
  if len(paths)>=8: break
  p=OUT/f"fallback_{len(paths)+1:02d}.jpg"
  try: dl(u,p); paths.append(p); IMAGE_SOURCES.append(u); print("Fallback image",p)
  except Exception as e: p.unlink(missing_ok=True); print("Fallback failed",str(e)[:100])
 if len(paths)<4: raise RuntimeError("Not enough usable photos")
 return paths
async def voice(text,path):
 for v in ["hi-IN-SwaraNeural","hi-IN-NeerjaNeural","hi-IN-MadhurNeural","hi-IN-PrabhatNeural"]:
  try:
   await Communicate(text=text,voice=v,rate="+0%",pitch="+0Hz").save(str(path))
   if path.exists() and path.stat().st_size>1000: print("TTS voice",v); return
  except Exception as e: path.unlink(missing_ok=True); print("Edge voice error",v,str(e)[:120])
 try:
  from gtts import gTTS
  gTTS(text=text,lang="hi").save(str(path)); print("gTTS backup used")
  if path.exists() and path.stat().st_size>1000:return
 except Exception as e: print("gTTS error",repr(e))
 raise RuntimeError("All speech providers failed")
def dur(path):
 return float(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1",str(path)],text=True).strip())
def subtitles(narration,duration,path):
 # Punchy 3-4 word captions with a highlighted keyword.
 words=narration.split(); chunks=[" ".join(words[i:i+4]) for i in range(0,len(words),4)]
 total=max(1,len(words)); t=0
 def stamp(sec):
  h=int(sec//3600); m=int((sec%3600)//60); s=sec%60
  return f"{h}:{m:02}:{s:05.2f}"
 stop={"hai","hain","ka","ki","ke","se","aur","ek","ye","is","to","mein","ko","par","the","a","an"}
 with open(path,"w",encoding="utf-8") as f:
  f.write("[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\nWrapStyle: 2\n\n[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\nStyle: Default,DejaVu Sans,66,&H00FFFFFF,&H0000FFFF,&H00151515,&H99000000,-1,0,0,0,100,100,0,0,1,5,2,2,90,90,250,1\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
  for chunk in chunks:
   n=len(chunk.split()); end=min(duration,t+duration*n/total)
   ws=chunk.split(); key=max((w for w in ws if w.lower().strip(".,!?") not in stop),key=len,default=ws[-1])
   marked=chunk.replace(key,"{\\c&H0000BFFF&}"+key+"{\\c&H00FFFFFF&}",1)
   animated="{\\\\fscx82\\\\fscy82\\\\t(0,130,\\\\fscx100\\\\fscy100)}"+marked
   f.write(f"Dialogue: 0,{stamp(t)},{stamp(end)},Default,,0,0,0,,{animated}\\n")
   t=end

def render(paths,audio,duration,narration,final,title):
 segs=[]
 per=duration/len(paths)
 for i,img in enumerate(paths):
  seg=OUT/f"part_{i:02d}.mp4"
  # Give EVERY still a distinct cinematic camera move (push, pull, or directional drift).
  frames=int(per*30)
  mode=i%6
  if mode==0:  # slow push in, slightly toward upper center
   z="min(1.0+on/1800,1.12)"; x="(iw-iw/zoom)/2"; y="(ih-ih/zoom)*0.38"
  elif mode==1:  # pull out
   z="max(1.12-on/1800,1.0)"; x="(iw-iw/zoom)/2"; y="(ih-ih/zoom)*0.52"
  elif mode==2:  # pan left to right
   z="1.08"; x="(iw-iw/zoom)*on/"+str(max(frames,1)); y="(ih-ih/zoom)/2"
  elif mode==3:  # pan right to left
   z="1.08"; x="(iw-iw/zoom)*(1-on/"+str(max(frames,1))+")"; y="(ih-ih/zoom)/2"
  elif mode==4:  # push toward lower-right
   z="min(1.0+on/1900,1.10)"; x="(iw-iw/zoom)*0.72"; y="(ih-ih/zoom)*0.72"
  else:  # gentle vertical drift
   z="1.07"; x="(iw-iw/zoom)/2"; y="(ih-ih/zoom)*on/"+str(max(frames,1))
  vf=f"zoompan=z='{z}':x='{x}':y='{y}':d={frames}:s=1080x1920:fps=30,fade=t=in:st=0:d=0.22,eq=contrast=1.07:saturation=1.14:brightness=0.01,unsharp=5:5:0.35:5:5:0,format=yuv420p"
  run(["ffmpeg","-y","-loop","1","-i",str(img),"-t",f"{per:.3f}","-vf",vf,"-r","30","-c:v","libx264","-preset","veryfast","-an",str(seg)])
  segs.append(seg)
 concat=OUT/"concat.txt"; concat.write_text("".join(f"file '{p.resolve().as_posix()}'\n" for p in segs),encoding="utf8")
 silent=OUT/"silent.mp4"
 run(["ffmpeg","-y","-f","concat","-safe","0","-i",str(concat),"-c","copy",str(silent)])
 ass=OUT/"captions.ass"; subtitles(narration,duration,ass)
 subpath=ass.resolve().as_posix().replace(":","\\:").replace("'","\\'")
 clean_title=re.sub(r"[^A-Za-z0-9 ,!?'-]","",title)[:42].replace("'","\\'")
 vf=f"subtitles='{subpath}',drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:text='{clean_title}':fontsize=54:fontcolor=white:box=1:boxcolor=black@0.72:boxborderw=24:x=(w-text_w)/2:y=210:enable='between(t,0,2.3)'"
 bed_duration=max(1,duration-0.8)
 # Low-volume generated ambient tones, no copyrighted track.
 fc=f"[2:a]volume=0.018,afade=t=in:st=0:d=1,afade=t=out:st={bed_duration:.2f}:d=0.8,lowpass=f=700[b1];[3:a]volume=0.009,lowpass=f=900[b2];[4:a]volume=0.006,lowpass=f=1200[b3];[b1][b2][b3]amix=inputs=3:normalize=0[bed];[1:a]volume=1.0[voice];[voice][bed]amix=inputs=2:duration=first:dropout_transition=1[a]"
 run(["ffmpeg","-y","-i",str(silent),"-i",str(audio),"-f","lavfi","-i",f"sine=frequency=110:duration={duration:.2f}","-f","lavfi","-i",f"sine=frequency=165:duration={duration:.2f}","-f","lavfi","-i",f"sine=frequency=220:duration={duration:.2f}","-filter_complex",fc,"-map","0:v","-map","[a]","-vf",vf,"-c:v","libx264","-preset","veryfast","-pix_fmt","yuv420p","-c:a","aac","-b:a","160k","-shortest","-movflags","+faststart",str(final)])
def posting(s):
 title=s["title"]; text=s["narration"]
 return f"{title}\n\n{text}\n\nHar machine ke andar chhupa hai ek raaz. Follow TORQUENAUT.\n\n#MachineKaRaaz #TorqueNaut #Cars #Bikes #Engineering #AutoFacts #HindiFacts #ReelsIndia #YouTubeShorts"
def main():
 for p in OUT.iterdir():
  if p.is_file(): p.unlink()
  elif p.is_dir(): shutil.rmtree(p)
 s=story(); narration=s["narration"]
 pics=images(s.get("searches",[]) or [s.get("topic","automotive")])
 audio=OUT/"voice.mp3"; asyncio.run(voice(narration,audio)); length=dur(audio)
 final=OUT/("TORQUENAUT_"+re.sub(r"[^A-Za-z0-9]+","_",s["title"]).strip("_")[:60]+".mp4")
 render(pics,audio,length,narration,final,s["title"])
 (OUT/"title.txt").write_text(s["title"],encoding="utf8")
 (OUT/"topic.txt").write_text(s.get("topic",""),encoding="utf8")
 (OUT/"narration.txt").write_text(narration,encoding="utf8")
 (OUT/"posting_copy.txt").write_text(posting(s),encoding="utf8")
 (OUT/"image_sources.txt").write_text("\n".join(f"{i+1}. {u}" for i,u in enumerate(IMAGE_SOURCES))+"\n",encoding="utf8")
 print("SUCCESS: Video:",final,"Duration:",round(length,2),"seconds")
if __name__=="__main__": main()
