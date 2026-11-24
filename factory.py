import os, json, re, random, subprocess, asyncio, html
from pathlib import Path
import requests

OUT=Path('output'); WORK=Path('work'); OUT.mkdir(exist_ok=True); WORK.mkdir(exist_ok=True)
GEM=os.environ.get('GEMINI_API_KEY')
if not GEM: raise SystemExit('Missing GEMINI_API_KEY GitHub secret')
MODEL=os.getenv('GEMINI_MODEL','gemini-3.5-flash-lite')
PROMPT='''Create one accurate, engaging automotive engineering video for Indian Hinglish viewers. Pick a fresh specific topic (car, motorcycle, engine, tyres, braking, aerodynamics, safety tech, manufacturing). Return ONLY valid JSON with keys: topic,title,narration,image_searches,caption,hashtags,fact_notes. narration: 105-125 spoken words, natural conversational Hinglish, written in Devanagari with common English technical terms where natural; avoid awkward pure Hindi. Start with a strong curiosity hook, explain one mechanism clearly, finish with a satisfying reveal. image_searches: exactly 8 distinct short English Wikimedia Commons searches, each describing a different scene/object relevant to the narration. Avoid unsupported statistics, invented facts, unsafe advice. fact_notes: 2-4 notes with credible source names or URLs; clearly qualify uncertainty.'''

def gemini():
    url=f'https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={GEM}'
    r=requests.post(url,json={'contents':[{'parts':[{'text':PROMPT}]}],'generationConfig':{'temperature':0.65,'responseMimeType':'application/json'}},timeout=90)
    if r.status_code==404:
        raise RuntimeError(f'Gemini model {MODEL} returned 404. Set GEMINI_MODEL to a model enabled for your API project; check Google AI Studio model list.')
    r.raise_for_status()
    raw=r.json()['candidates'][0]['content']['parts'][0]['text'].strip()
    raw=re.sub(r'^```(?:json)?\s*|\s*```$','',raw)
    data=json.loads(raw)
    for key in ['topic','title','narration','image_searches','caption','hashtags','fact_notes']:
        if key not in data: raise ValueError(f'Gemini response missing {key}')
    return data

def commons_image(query,index):
    params={'action':'query','format':'json','generator':'search','gsrsearch':f'filetype:bitmap {query}','gsrnamespace':6,'gsrlimit':12,'prop':'imageinfo','iiprop':'url|extmetadata','iiurlwidth':1600}
    r=requests.get('https://commons.wikimedia.org/w/api.php',params=params,headers={'User-Agent':'TorquenautVideoFactory/2.0 (educational video)'},timeout=45); r.raise_for_status()
    pages=r.json().get('query',{}).get('pages',{}); choices=[]
    for page in pages.values():
        info=(page.get('imageinfo') or [{}])[0]; url=info.get('thumburl') or info.get('url')
        if url and re.search(r'\.(jpg|jpeg|png|webp)(\?|$)',url,re.I): choices.append((page,info,url))
    if not choices:return None
    page,info,url=random.choice(choices); p=WORK/f'image_{index:02}.jpg'
    rr=requests.get(url,headers={'User-Agent':'TorquenautVideoFactory/2.0'},timeout=60); rr.raise_for_status(); p.write_bytes(rr.content)
    meta=info.get('extmetadata',{})
    def clean(k): return re.sub('<[^>]+>','',html.unescape(meta.get(k,{}).get('value',''))).strip()
    return {'path':p,'title':page.get('title',''),'url':info.get('descriptionurl',''),'artist':clean('Artist'),'license':clean('LicenseShortName'),'license_url':clean('LicenseUrl')}

def run(cmd): subprocess.run(cmd,check=True)
def duration(path): return float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(path)]).decode().strip())
def stamp(t):
    ms=int(max(0,t)*1000); return f'{ms//3600000:02}:{(ms%3600000)//60000:02}:{(ms%60000)//1000:02},{ms%1000:03}'

def make_srt(text,audio_len,path):
    words=text.split(); groups=[]
    # 4-6 words per subtitle card for easier phone readability
    for i in range(0,len(words),5): groups.append(' '.join(words[i:i+5]))
    lines=[]
    for i,phrase in enumerate(groups):
        start=audio_len*i/len(groups); end=audio_len*(i+1)/len(groups)
        lines += [str(i+1),f'{stamp(start)} --> {stamp(end)}',phrase,'']
    path.write_text('\n'.join(lines),encoding='utf-8')

def main():
    data=gemini(); (OUT/'content.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    voice=OUT/'voice.mp3'
    import edge_tts
    # More natural Indian Hindi male neural voice; slightly slower for documentary delivery.
    async def speak(): await edge_tts.Communicate(data['narration'],voice='hi-IN-MadhurNeural',rate='-5%',pitch='-2Hz',volume='+0%').save(str(voice))
    asyncio.run(speak())
    terms=list(dict.fromkeys(data.get('image_searches',[])[:10]))
    if len(terms)<6: terms += [data['topic']+' automobile',data['topic']+' mechanical parts']
    images=[]; credits=[]
    for i,term in enumerate(terms[:10]):
        try:
            item=commons_image(term,i)
            if item: images.append(item); credits.append({k:v for k,v in item.items() if k!='path'})
        except Exception as e: print('Image search failed:',term,str(e)[:180])
    if len(images)<4: raise RuntimeError(f'Only {len(images)} usable Commons images found; need at least 4. Try another topic later.')
    audio_len=duration(voice); per=audio_len/len(images); clips=[]
    for i,item in enumerate(images):
        clip=WORK/f'scene_{i:02}.mp4'; frames=max(1,int(per*30)); mode=i%4
        if mode==0: zoom="min(zoom+0.00065,1.12)"; x="iw/2-(iw/zoom/2)"; y="ih/2-(ih/zoom/2)"
        elif mode==1: zoom="if(eq(on,0),1.12,max(zoom-0.00065,1.0))"; x="iw/2-(iw/zoom/2)"; y="ih/2-(ih/zoom/2)"
        elif mode==2: zoom="1.08"; x="(iw-iw/zoom)*on/"+str(max(frames-1,1)); y="ih/2-(ih/zoom/2)"
        else: zoom="1.08"; x="(iw-iw/zoom)*(1-on/"+str(max(frames-1,1))+')'; y="ih/2-(ih/zoom/2)"
        vf=f"scale=1400:2488:force_original_aspect_ratio=increase,crop=1200:2134,zoompan=z='{zoom}':x='{x}':y='{y}':d={frames}:s=1080x1920:fps=30,eq=contrast=1.06:saturation=1.12:brightness=0.01,format=yuv420p"
        run(['ffmpeg','-y','-loop','1','-i',str(item['path']),'-t',str(per),'-vf',vf,'-an','-c:v','libx264','-preset','veryfast','-crf','22',str(clip)])
        clips.append(clip)
    concat=WORK/'clips.txt'; concat.write_text(''.join(f"file '{p.resolve()}'\n" for p in clips))
    visual=WORK/'visuals.mp4'; run(['ffmpeg','-y','-f','concat','-safe','0','-i',str(concat),'-c','copy',str(visual)])
    srt=OUT/'captions.srt'; make_srt(data['narration'],audio_len,srt)
    final=OUT/'torquenaut_draft.mp4'; sub=str(srt.resolve()).replace(':','\\:').replace("'", "\\'")
    style="FontName=DejaVu Sans,FontSize=22,Bold=1,PrimaryColour=&H0000D7FF,OutlineColour=&H00101010,BorderStyle=1,Outline=3,Shadow=1,Alignment=2,MarginL=70,MarginR=70,MarginV=170"
    run(['ffmpeg','-y','-stream_loop','-1','-i',str(visual),'-i',str(voice),'-t',str(audio_len),'-vf',f"subtitles={sub}:force_style='{style}'",'-map','0:v:0','-map','1:a:0','-c:v','libx264','-preset','veryfast','-crf','22','-c:a','aac','-b:a','160k','-shortest',str(final)])
    (OUT/'image_credits.json').write_text(json.dumps(credits,ensure_ascii=False,indent=2),encoding='utf-8')
    txt=f"TITLE: {data['title']}\nTOPIC: {data['topic']}\nCAPTION: {data['caption']}\nHASHTAGS: {' '.join(data['hashtags'])}\nFACT NOTES: {json.dumps(data['fact_notes'],ensure_ascii=False)}\n"
    (OUT/'posting.txt').write_text(txt,encoding='utf-8')
    print(f'Draft complete: {final}; scenes={len(images)}; voice=hi-IN-MadhurNeural')
if __name__=='__main__': main()
