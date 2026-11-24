import os, json, re, random, subprocess, textwrap, requests
from pathlib import Path

OUT=Path('output'); WORK=Path('work'); OUT.mkdir(exist_ok=True); WORK.mkdir(exist_ok=True)
GEM=os.environ['GEMINI_API_KEY']; PEX=os.environ['PEXELS_API_KEY']

prompt='''Create one fresh automotive engineering / car / motorcycle fact video for Indian Hinglish viewers. Pick a non-obvious topic and avoid generic clickbait. Return ONLY valid JSON with keys: topic, title, narration (Hindi/Hinglish in Devanagari where practical, 100-140 words, factual and cautious), search_terms (3 short English stock-video searches), caption (short), hashtags (array of 5). No invented statistics or unsafe driving advice. Explain why the machine works / a design secret. Include a strong hook in first sentence and a satisfying reveal.'''

def gemini():
    url=f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEM}'
    r=requests.post(url,json={'contents':[{'parts':[{'text':prompt}]}],'generationConfig':{'temperature':0.8}},timeout=90); r.raise_for_status()
    text=r.json()['candidates'][0]['content']['parts'][0]['text']
    text=re.sub(r'^```(?:json)?\s*|\s*```$','',text.strip())
    return json.loads(text)

def get_video(search):
    r=requests.get('https://api.pexels.com/videos/search',headers={'Authorization':PEX},params={'query':search,'orientation':'portrait','per_page':8},timeout=45); r.raise_for_status()
    items=r.json().get('videos',[])
    if not items: return None
    v=random.choice(items)
    files=sorted([f for f in v.get('video_files',[]) if f.get('file_type')=='video/mp4'],key=lambda x:(x.get('width',0)*x.get('height',0)))
    if not files: return None
    chosen=files[-1]
    p=WORK/f'clip_{random.randrange(999999)}.mp4'
    with requests.get(chosen['link'],stream=True,timeout=90) as rr:
        rr.raise_for_status()
        with open(p,'wb') as fh:
            for chunk in rr.iter_content(1024*1024):
                if chunk: fh.write(chunk)
    return p

def run(cmd): subprocess.run(cmd,check=True)

def main():
    data=gemini(); (OUT/'content.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    voice=OUT/'voice.mp3'
    import asyncio, edge_tts
    async def speak():
        await edge_tts.Communicate(data['narration'],voice='hi-IN-SwaraNeural',rate='+8%').save(str(voice))
    asyncio.run(speak())
    # Download footage from multiple searches, then create short portrait clips.
    raw=[]
    for term in data.get('search_terms',[])[:3]:
        p=get_video(term)
        if p: raw.append(p)
    if not raw: raise RuntimeError('Pexels returned no usable videos. Try another run.')
    audlen=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(voice)]).decode().strip())
    per=max(4,audlen/len(raw)); parts=[]
    for i,p in enumerate(raw):
        part=WORK/f'part{i}.mp4'
        run(['ffmpeg','-y','-i',str(p),'-t',str(per),'-vf',"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30,format=yuv420p",'-an','-c:v','libx264','-preset','veryfast','-crf','24',str(part)])
        parts.append(part)
    # concat clips; loop footage if narration longer than source clips
    concat=WORK/'clips.txt'; concat.write_text(''.join(f"file '{p.resolve()}'\n" for p in parts))
    merged=WORK/'visual.mp4'; run(['ffmpeg','-y','-f','concat','-safe','0','-i',str(concat),'-c','copy',str(merged)])
    # Subtitle file: simple phrase-level timing distributed across narration words.
    words=data['narration'].split(); n=max(1,len(words)); chunk=7; duration=audlen
    def stamp(t):
        ms=int(max(0,t)*1000); h=ms//3600000; m=(ms%3600000)//60000; s=(ms%60000)//1000; ms%=1000
        return f'{h:02}:{m:02}:{s:02},{ms:03}'
    lines=[]
    for idx in range(0,n,chunk):
        start=duration*idx/n; end=duration*min(idx+chunk,n)/n
        phrase=' '.join(words[idx:idx+chunk]).replace('--','—')
        lines.extend([str(idx//chunk+1),f'{stamp(start)} --> {stamp(end)}',phrase,''])
    srt=OUT/'captions.srt'; srt.write_text('\n'.join(lines),encoding='utf-8')
    # Keep visuals long enough by looping if needed; burn captions and mix narration.
    final=OUT/'torquenaut_draft.mp4'
    subtitle_path=str(srt.resolve()).replace(':','\\:')
    run(['ffmpeg','-y','-stream_loop','-1','-i',str(merged),'-i',str(voice),'-t',str(audlen),'-vf',f"subtitles={subtitle_path}:force_style='FontSize=18,Outline=2,Alignment=2,MarginV=150'",'-map','0:v:0','-map','1:a:0','-c:v','libx264','-preset','veryfast','-crf','24','-c:a','aac','-b:a','128k','-shortest',str(final)])
    # Save publishing copy text
    txt=f"TITLE: {data['title']}\\nCAPTION: {data.get('caption','')}\\nHASHTAGS: {' '.join(data.get('hashtags',[]))}\\nTOPIC: {data['topic']}\\n"
    (OUT/'posting.txt').write_text(txt,encoding='utf-8')
    print('Draft complete:',final)
if __name__=='__main__': main()
