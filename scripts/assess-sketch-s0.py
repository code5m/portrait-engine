"""Assess calibration and retain provenance; never certifies drawing realism."""
import base64,hashlib,io,json,os,textwrap
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageChops
from importlib.util import spec_from_file_location,module_from_spec
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'test-results/sketch-s0'
spec=spec_from_file_location('capture',ROOT/'scripts/capture-sketch-s0.py');mod=module_from_spec(spec);spec.loader.exec_module(mod)
config=json.loads((ROOT/'research/sketch/s0-scenes.json').read_text())
SOURCE_FILES=['research/sketch/s0-scenes.json','research/sketch/sources.lock.json','study/sketch-s0.mjs','study/sketch-s0.template.html','scripts/build-sketch-s0.py','scripts/capture-sketch-s0.py','scripts/prepare-sketch-s0.py','scripts/reference-sketch-s0.py','scripts/assess-sketch-s0.py']
def digest():
    h=hashlib.sha256()
    for name in sorted(SOURCE_FILES):h.update(name.encode()+b'\0'+(ROOT/name).read_bytes()+b'\0')
    return h.hexdigest()
css=json.loads((OUT/'css-metrics.json').read_text());ref=json.loads((OUT/'reference-manifest.json').read_text());source=json.loads((OUT/'source-verification.json').read_text())
assert css['transport']=='file','Only real file navigation can complete S0'
assert not css['browserErrors'] and not css['externalRequests']
rows=[]
for profile in config['profiles']:
    for light in config['lights']:
        scene=profile['id']+'-'+light['id'];expected,mask=mod.expected(profile,light)
        b=np.asarray(Image.open(OUT/('reference-'+scene+'.png')).convert('RGB')).mean(-1)
        c=np.asarray(Image.open(OUT/('css-'+scene+'.png')).convert('RGB')).mean(-1)
        row={'scene':scene,'referenceVsAnalyticMAE':round(float(np.abs(b-expected)[mask].mean()),4),'cssVsAnalyticMAE':round(float(np.abs(c-expected)[mask].mean()),4),'cssVsBlenderMAE':round(float(np.abs(c-b)[mask].mean()),4)}
        assert row['referenceVsAnalyticMAE']<4,('Reference camera/color/normal mismatch',row)
        assert row['cssVsAnalyticMAE']<6 and row['cssVsBlenderMAE']<6,('CSS transfer calibration failed',row)
        rows.append(row)
line=Image.open(OUT/'ict-neutral-freestyle.png').convert('RGB');shade=Image.open(OUT/'ict-neutral-reference.png').convert('RGB')
lineDelta=float(np.asarray(ImageChops.difference(line,shade)).mean());assert lineDelta>.01,'Freestyle had no actual line effect'
baseline=ROOT/'test-results/face-engine-v1/manifest.json'; baselineRows=json.loads(baseline.read_text());assert len(baselineRows)==9
assert len(source['files'])==2 and ref['ictVertices']==26719 and ref['ictFaces']==26384
report={'schemaVersion':1,'stage':'S0','status':'CALIBRATION_COMPLETE','artStatus':'ART_UNVERIFIED','humanObservers':0,'sourceDigest':digest(),'ciRun':os.getenv('GITHUB_RUN_ID'),'ciCommit':os.getenv('GITHUB_SHA'),'upstream':source,'blenderVersion':ref['blenderVersion'],'colorManagement':{'view':ref['viewTransform'],'look':ref['look']},'counts':{'baselinePortraits':9,'blenderPrimitives':9,'cssPrimitives':9,'cssThreeTone':3,'referenceHeadFrames':2},'metrics':rows,'freestylePixelDelta':round(lineDelta,5),'limitations':['No cast shadows or physical bounced light','Visible finite-tone banding','Single orthographic view; ellipsoids are NOT human identities','ICT mesh is an import probe only, not yet transferred to CSS','No evidence of improved human-portrait realism']}
report['imageHashes']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(OUT.glob('*.png'))}
(OUT/'completion.json').write_text(json.dumps(report,indent=2))
print('S0_COMPLETION_JSON '+json.dumps(report,separators=(',',':')))
sheet=Image.new('RGB',(768,3*284),'white');draw=ImageDraw.Draw(sheet)
for i,profile in enumerate(config['profiles']):
    light=config['lights'][0];name=profile['id']+'-'+light['id']
    for j,prefix in enumerate(['reference','css']):
        pic=Image.open(OUT/(prefix+'-'+name+'.png')).convert('RGB');sheet.paste(pic,(j*256,i*284+28));draw.text((j*256+8,i*284+8),('B Blender' if j==0 else 'C CSS 16 patches')+' / '+profile['id'],fill='black')
    pic=Image.open(OUT/('css3-'+name+'.png')).convert('RGB')
    sheet.paste(pic,(512,i*284+28));draw.text((520,i*284+8),'C CSS: 3 tones / same geometry',fill='black')
sheet.save(OUT/'comparison-contact.jpg',quality=85)
# Log a small reference-only contact when Actions artifact quota is full.
if os.getenv('S0_LOG_PREVIEW')=='1':
    for name in ['comparison-contact.jpg','ict-neutral-freestyle.png']:
        thumb=Image.open(OUT/name).convert('RGB');thumb.thumbnail((480,560))
        buffer=io.BytesIO();thumb.save(buffer,format='JPEG',quality=65,optimize=True)
        print('S0_PREVIEW_BEGIN '+name)
        for line in textwrap.wrap(base64.b64encode(buffer.getvalue()).decode(),180):print(line)
        print('S0_PREVIEW_END '+name)
