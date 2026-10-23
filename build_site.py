"""Build a self-contained Pages site. No network or external Python packages."""
import json,re,shutil,sys
from pathlib import Path
from urllib.parse import quote

ALLOWED={'.mp3','.m4a','.wav','.ogg','.aac','.flac','.opus','.webm'}

def build(root,output):
    root=Path(root).resolve();output=Path(output).resolve()
    if output==root or root not in output.parents:raise ValueError('Output must be a subdirectory')
    settings=json.loads((root/'site.json').read_text())
    title=settings.get('title','あきらボタン')
    if not isinstance(title,str) or not title.strip() or len(title)>60:raise ValueError('Invalid title')
    minimum=settings.get('minimumSlots',300)
    if not isinstance(minimum,int) or not 300<=minimum<=10000:raise ValueError('minimumSlots must be 300..10000')
    records=[];ids=set();assets={};combined={}
    for r in json.loads((root/'seed.json').read_text())['records']:
        rid=r.get('id')
        if not isinstance(rid,str) or rid in combined:raise ValueError('Invalid seed record')
        combined[rid]=r
    for p in sorted((root/'library').glob('*.json')):
        r=json.loads(p.read_text())
        if r.get('id')!=p.stem:raise ValueError('Record filename must match ID: '+p.name)
        combined[p.stem]=r
    for rid,r in combined.items():
        if not isinstance(rid,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',rid) or rid in ids:raise ValueError('Invalid or duplicate record ID')
        ids.add(rid);name=rid+'.json'
        if r.get('deleted') is True:continue
        if not isinstance(r.get('label'),str) or not r['label'].strip() or len(r['label'])>80:raise ValueError('Invalid label: '+name)
        if not isinstance(r.get('category'),str) or not r['category'].strip() or len(r['category'])>80:raise ValueError('Invalid category: '+name)
        order=r.get('order',0)
        if isinstance(order,bool) or not isinstance(order,int) or not 0<=order<=2147483647:raise ValueError('Invalid order: '+name)
        c={k:r[k] for k in ('id','label','category')};c.update(order=order,favorite=False)
        if r.get('src'):
            src=r['src']
            if not isinstance(src,str) or not re.fullmatch(r'library/[A-Za-z0-9_-]+\.(mp3|m4a|wav|ogg|aac|flac|opus|webm)',src):raise ValueError('Invalid audio path: '+name)
            audio=root/src
            if audio.is_symlink() or not audio.is_file() or audio.stat().st_size==0 or audio.stat().st_size>25*1024*1024:raise ValueError('Missing or invalid audio: '+src)
            c['src']=src;c['filename']=str(r.get('filename',audio.name));assets[src]=audio
        records.append(c)
    occupied={r['order'] for r in records};i=0
    while len(records)<minimum:
        rid='slot-'+str(i+1).zfill(3)
        if i not in occupied and not any(r['id']==rid for r in records):
            records.append({'id':rid,'label':'ボイス '+str(i+1).zfill(2),'category':'未分類','order':i,'favorite':False})
        i+=1
    records.sort(key=lambda r:(r['order'],r['id']))
    total=sum(p.stat().st_size for p in assets.values())
    if total>900*1024*1024:raise ValueError('Audio exceeds 900 MiB. Reduce size before publishing.')
    if output.exists():shutil.rmtree(output)
    output.mkdir()
    for name in ('index.html','style.css','app.js'):
        if (root/name).is_symlink():raise ValueError('Symlinks not allowed')
        shutil.copyfile(root/name,output/name)
    for src,p in assets.items():
        dest=output/src;dest.parent.mkdir(exist_ok=True);shutil.copyfile(p,dest)
    (output/'.nojekyll').write_text('')
    manifest={'published':True,'storage':'github','title':title,'minimumSlots':minimum,'clips':records}
    (output/'voices.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(f'Built {len(records)} slots; {len(assets)} audio files; {total} audio bytes.')
    return manifest

if __name__=='__main__':build(Path(__file__).parent,Path(__file__).parent/'_site')
