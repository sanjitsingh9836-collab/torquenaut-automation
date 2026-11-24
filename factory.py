import os, json, re, random, subprocess, textwrap, requests, asyncio
from pathlib import Path

OUT=Path('output'); WORK=Path('work'); OUT.mkdir(exist_ok=True); WORK.mkdir(exist_ok=True)
GEM=os.environ.get('GEMINI_API_KEY')
if not GEM: raise SystemExit('Missing GEMINI_API_KEY GitHub secret')

PROMPT='''Create a fresh automotive engineering / car / motorcycle fact video for Indian Hinglish viewers. Choose a non-obvious topic and avoid generic clickbait. Return ONLY valid JSON with keys: topic, title, narration, image_searches (4 short English Wikimedia Commons search terms), caption, hashtags (array of 5), and fact_notes (array of 2-4 concise notes explaining factual claims and suggested source names/URLs if known). Narration should be 100-130 words in natural Hinglish/Hindi, Devanagari where practical. Include a strong hook in first sentence and a satisfying reveal. Avoid invented statistics, unsupported precise claims, unsafe driving advice, or presenting guesses as facts. If unsure, qualify the claim. The video may use still photos with motion graphics, so suggest visuals that match the topic.'''

def gemini():
    url=f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEM}'
    r=requests.post(url,json={'contents':[{'parts':[{'text':PROMPT}]}],'generationConfig':{'temperature':0.75}},timeout=90); r.raise_for_status()
    text=r.json()['candidates'][0]['content']['parts'][0]['text'].strip()
    text=re.sub(r'^```(?:json)?\s*|\s*```$','',text)
    return json.loads(text)

# Wikimedia Commons API: no API key required. Download images and retain attribution/license metadata.
def commons_image(query, index):
    params={'action':'query','format':'json','generator':'search','gsrsearch':f'filetype:bitmap {query}','gsrnamespace':6,'gsrlimit':8,'prop':'imageinfo','iiprop':'url|extmetadata','iiurlwidth':1200}
    r=requests.get('https://commons.wikimedia.org/w/api.php',params=params,headers={'User-Agent':'TorquenautVideoFactory/1.0 (automated educational video)'},timeout=40); r.raise_for_status()
    pages=r.json().get('query',{}).get('pages',{})
    choices=[]
    for page in pages.values():
        info=(page.get('imageinfo') or [{}])[0]
        url=info.get('thumburl') or info.get('url')
        if url and re.search(r'\.(jpg|jpeg|png|webp)(\?|$)',url,re.I): choices.append((page,info,url))
    if not choices: return None
    page,info,url=random.choice(choices)
    p=WORK/f'image_{index}.jpg'
    rr=requests.get(url,headers={'User-Agent':'TorquenautVideoFactory/1.0'},timeout=60); rr.raise_for_status(); p.write_bytes(rr.content)
    meta=info.get('extmetadata',{})
    def clean(k): return re.sub('<[^>]+>','',meta.get(k,{}).get('value','')).strip()
    return {'path':p,'title':page.get('title',''),'url':info.get('descriptionurl',''),'artist':clean('Artist'),'license':clean('LicenseShortName'),'license_url':clean('LicenseUrl')}

def run(cmd): subprocess.run(cmd,check=True)
def probe_duration(path):
    return float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(path)]).decode().strip())
def stamp(t):
    ms=int(max(0,t)*1000); h=ms//3600000; m=(ms%3600000)//60000; s=(ms%60000)//1000; ms%=1000
    return f'{h:02}:{m:02}:{s:02},{ms:03}'

def main():
    data=gemini(); (OUT/'content.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    voice=OUT/'voice.mp3'
    import edge_tts
    async def speak(): await edge_tts.Communicate(data['narration'],voice='hi-IN-SwaraNeural',rate='+8%').save(str(voice))
    asyncio.run(speak())
    searches=data.get('image_searches',[])[:4] or [data['topic']]
    images=[]; credits=[]
    for i,term in enumerate(searches):
        try:
            item=commons_image(term,i)
            if item: images.append(item); credits.append({k:v for k,v in item.items() if k!='path'})
        except Exception as e: print('Image search failed:',term,str(e)[:160])
    if not images: raise RuntimeError('No Wikimedia Commons images could be retrieved. Try manual workflow run later.')
    audio_len=probe_duration(voice); per=audio_len/len(images); clips=[]
    for i,item in enumerate(images):
        clip=WORK/f'visual_{i}.mp4'; image=item['path']
        # Slow Ken Burns motion on still images; scale/crop to portrait then animate zoom.
        frames=max(1,int(per*30)); vf=f"scale=1200:2134:force_original_aspect_ratio=increase,crop=1080:1920,zoompan=z='min(zoom+0.0005,1.08)':d={frames}:s=1080x1920:fps=30,format=yuv420p"
        run(['ffmpeg','-y','-loop','1','-i',str(image),'-t',str(per),'-vf',vf,'-an','-c:v','libx264','-preset','veryfast','-crf','25',str(clip)])
        clips.append(clip)
    concat=WORK/'clips.txt'; concat.write_text(''.join(f"file '{p.resolve()}'\n" for p in clips))
    visual=WORK/'visuals.mp4'; run(['ffmpeg','-y','-f','concat','-safe','0','-i',str(concat),'-c','copy',str(visual)])
    words=data['narration'].split(); n=max(1,len(words)); chunk=7; lines=[]
    for idx in range(0,n,chunk):
        start=audio_len*idx/n; end=audio_len*min(idx+chunk,n)/n
        phrase=' '.join(words[idx:idx+chunk])
        lines += [str(idx//chunk+1),f'{stamp(start)} --> {stamp(end)}',phrase,'']
    srt=OUT/'captions.srt'; srt.write_text('\n'.join(lines),encoding='utf-8')
    final=OUT/'torquenaut_draft.mp4'; sub=str(srt.resolve()).replace(':','\\:')
    run(['ffmpeg','-y','-stream_loop','-1','-i',str(visual),'-i',str(voice),'-t',str(audio_len),'-vf',f"subtitles={sub}:force_style='FontSize=18,Outline=2,Alignment=2,MarginV=150'",'-map','0:v:0','-map','1:a:0','-c:v','libx264','-preset','veryfast','-crf','25','-c:a','aac','-b:a','128k','-shortest',str(final)])
    (OUT/'image_credits.json').write_text(json.dumps(credits,ensure_ascii=False,indent=2),encoding='utf-8')
    txt=f"TITLE: {data.get('title','')}\nTOPIC: {data.get('topic','')}\nCAPTION: {data.get('caption','')}\nHASHTAGS: {' '.join(data.get('hashtags',[]))}\nFACT NOTES: {json.dumps(data.get('fact_notes',[]),ensure_ascii=False)}\n"
    (OUT/'posting.txt').write_text(txt,encoding='utf-8')
    print('Draft complete:',final)
if __name__=='__main__': main()
