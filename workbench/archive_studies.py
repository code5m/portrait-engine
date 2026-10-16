"""Archive measured study receipts and their actual PNGs, never human ratings.

Each successful shard packs a bounded allowlist into an Actions cache. The
all-scenes job verifies all packs, then creates a NEW evidence-only branch.
It never moves main or the PR ref. Git storage is independent of artifact ZIP
quota. No user uploads, credentials, arbitrary paths or renderer inputs enter
this archive. PNGs remain research evidence only.
"""
from __future__ import annotations
import base64,hashlib,json,math,os,re,sys,time,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PACKS=ROOT/'data/workbench/receipts'
LABELS=('control','S3','masses','structure','all-edges','S4')
STEPS=('S3 generation','S4 generation','independent verify','three-tone view','structure view','edge control','stage-bound isolated reviews','HTML exports','mobile layout')


def read(path):return json.loads(path.read_text(encoding='utf8'))
def encoded(value):return (json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
def digest(data):return hashlib.sha256(data).hexdigest()
def write(path,data):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
def require(condition,message):
    if not condition:raise ValueError(message)
def finite(value):return type(value) in (float,int) and math.isfinite(value) and value>=0

def context():
    run=os.environ.get('GITHUB_RUN_ID','');head=os.environ.get('SOURCE_HEAD_SHA','')
    require(bool(re.fullmatch(r'[0-9]+',run)) and bool(re.fullmatch(r'[a-f0-9]{40}',head)),'Missing exact CI provenance')
    return run,head

def source_digest(stage):
    h=hashlib.sha256()
    for name in sorted(read(ROOT/f'research/sketch/{stage.lower()}-sources.json')):
        h.update(name.encode()+b'\0'+(ROOT/name).read_bytes()+b'\0')
    return h.hexdigest()

def check_report(report,stage,identity,config):
    run,head=context();p3=read(ROOT/'research/sketch/s3-protocol.json');p4=read(ROOT/'research/sketch/s4-protocol.json')
    require(report['ciRun']==run and report['sourceHeadCommit']==head,'Mixed source head or run')
    require(report['stage']==stage and report['status']=='PASS','Non-passing study')
    require(report['sourceDigest']==source_digest(stage),'Stale study source')
    require(report['humanObservers']==0 and report['artStatus']=='ART_UNVERIFIED','Not a human evidence archive')
    require(report['split']==identity['split'] and report['transport']=='file','Wrong cohort or browser transport')
    require(report['counts']=={'identities':1,'scenes':3,'cssFrames':12 if stage=='S3' else 6},'Wrong shard counts')
    require([r['id'] for r in report['metrics']]==[identity['id']+'-'+l['id'] for l in config['lights']],'Missing or reordered scenes')
    require(len(report['calibrationMAE'])==3 and all(finite(x) and x<p3['radiometryCalibrationMAE'] for x in report['calibrationMAE']),'Radiometry failed')
    for row in report['metrics']:
        require(row['status']=='PASS' and row['failures']==[],'Failed scene')
        m=row['metrics'];require(all(finite(x) for x in m.values()),'Invalid measurement')
        require(.975<=m['silhouetteIoU']<=1,'Silhouette failed')
        if stage=='S3':
            require(all(m[k]<p3['thresholds'][k] for k in ('fullMAE','interiorMAE','featureMAE')),'S3 fidelity failed')
            require(row['toneRegions']==p3['levels'] and 0<row['contourPoints']<=p3['thresholds']['maxContourPoints'],'S3 complexity failed')
            require(row['unshadowedFidelity']['interiorMAE']<p3['thresholds']['interiorMAE'],'Unshadowed control failed')
            if row['shadowPixels']>=20:
                require(row['shadowError']<=p3['shadowErrorRatio']*row['controlShadowError']+1e-5,'Shadow improvement failed')
        else:
            require(0<=row['inkFraction']<=p4['maxInkFraction'],'S4 ink failed')
            require(0<=row['outsideAllowedChange']<=p4['outsideEdgePixelTolerance'],'S4 locality failed')
            require(m['interiorMAE']<=row['parentInteriorMAE']+p4['maxAddedInteriorError'],'S4 error failed')
            require(0<=row['edgePoints']<=p4['maxEdgePoints'] and row['classification']['lost']>0,'S4 complexity or omission failed')

def pack(identity_id):
    config=read(ROOT/'research/sketch/s2-protocol.json')
    identities=[i for i in config['identities'] if i['id']==identity_id]
    require(len(identities)==1,'Unregistered identity');identity=identities[0]
    source=ROOT/'data/workbench/studies';target=PACKS/identity_id
    files={};reports={}
    for stage in ('S3','S4'):
        path=source/f'{stage}-{identity["split"]}-result.json';report=read(path)
        check_report(report,stage,identity,config);reports[stage]=report
        files[f'{stage}-{identity_id}.json']=path.read_bytes()
    for light in config['lights']:
        scene=identity_id+'-'+light['id']
        for label in LABELS:files[f'images/{scene}-{label}.png']=(source/'captures'/f'{scene}-{label}.png').read_bytes()
        for arm in ('shadow','unshadowed'):
            for extension in ('png','json'):
                name=f'{scene}-{arm}.{extension}';files['reference/'+name]=(source/'reference'/name).read_bytes()
    for cosine in (.25,.65,1.0):
        name=f'calibration-{cosine}.png';files['reference/'+name]=(source/'reference'/name).read_bytes()
    files[f'comparison-{identity_id}.png']=(source/f'comparison-{identity["split"]}.png').read_bytes()
    if identity_id==config['identities'][0]['id']:
        receipt=read(source/'UI-result.json');check_ui(receipt)
        files['UI-result.json']=(source/'UI-result.json').read_bytes()
        for stage in ('S3','S4'):files[f'workbench-{stage}.png']=(source/f'workbench-{stage}.png').read_bytes()
    verify_image_hashes(reports,files)
    require(sum(map(len,files.values()))<15_000_000,'Unexpected shard size')
    for name,data in files.items():write(target/name,data)
    run,head=context();write(target/'manifest.json',encoded({'run':run,'head':head,'identity':identity_id,'files':{n:digest(d) for n,d in files.items()}}))
    print('MEASURED_EVIDENCE_PACK',identity_id,len(files),'files',flush=True)

def check_ui(receipt):
    run,head=context()
    require(receipt['status']=='PASS' and receipt['ciRun']==run and receipt['sourceHead']==head,'UI provenance failed')
    require(receipt['humanObservers']==0 and receipt['reviewData']=='temporary AUTOMATED_TEST database only','UI is not human evidence')
    require(set(STEPS)<=set(receipt['steps']),'Incomplete UI validation')

def verify_image_hashes(reports,files):
    for name,data in files.items():
        if name.endswith('.png'):
            require(data.startswith(b'\x89PNG\r\n\x1a\n') and len(data)>24,'Not a PNG capture')
            width=int.from_bytes(data[16:20],'big');height=int.from_bytes(data[20:24],'big')
            require(0<width<=4096 and 0<height<=8192,'Unexpected PNG dimensions')
            if name.startswith(('images/','reference/')):require((width,height)==(320,320),'Changed measured image size')
    for r in reports['S3']['metrics']:
        require(digest(files[f'images/{r["id"]}-S3.png'])==r['captureHash'],'Wrong S3 capture')
        require(digest(files[f'reference/{r["id"]}-shadow.png'])==r['referenceHash'],'Wrong independent reference')
    for r in reports['S4']['metrics']:
        require(digest(files[f'images/{r["id"]}-S4.png'])==r['captureHash'],'Wrong S4 capture')
        require(digest(files[f'images/{r["id"]}-all-edges.png'])==r['controlHash'],'Wrong S4 control')

def collect():
    run,head=context();config=read(ROOT/'research/sketch/s2-protocol.json')
    require(len(config['identities'])==6 and len(config['lights'])==3,'Cohort changed')
    base=f'research/sketch/evidence/raw/{run}';files={};raw={s:[] for s in ('S3','S4')};rows={s:[] for s in raw};ui=None
    for identity in config['identities']:
        ident=identity['id'];folder=PACKS/ident;manifest=read(folder/'manifest.json')
        require(manifest['run']==run and manifest['head']==head and manifest['identity']==ident,'Mixed cache pack')
        own={}
        for name,checksum in manifest['files'].items():
            require(not Path(name).is_absolute() and '..' not in Path(name).parts and Path(name).suffix in ('.json','.png'),'Unsafe archive path')
            data=(folder/name).read_bytes();require(digest(data)==checksum,'Damaged pack')
            require(len(data)<=8_000_000,'Unexpected file size');own[name]=data
            destination=f'{base}/{name}' if '/' not in name and name.endswith('.json') else f'{base}/assets/{ident}/{name}'
            files[destination]=data
        reports={}
        for stage in raw:
            report=json.loads(own[f'{stage}-{ident}.json']);check_report(report,stage,identity,config);reports[stage]=report
            raw[stage].append(f'{base}/{stage}-{ident}.json');rows[stage].extend(report['metrics'])
        verify_image_hashes(reports,own)
        if ident==config['identities'][0]['id']:
            ui=json.loads(own['UI-result.json']);check_ui(ui)
    require(ui is not None and all(len(v)==18 for v in rows.values()),'Incomplete cohort')
    require(sum(r['shadowPixels']>=20 for r in rows['S3'])>=6,'No meaningful shadow cohort')
    for a,b in zip(rows['S3'],rows['S4']):
        require(a['id']==b['id'] and a['geometryHash']==b['geometryHash'] and a['metrics']['interiorMAE']==b['parentInteriorMAE'],'S4 parent mismatch')
    for stage in raw:
        first=json.loads(files[raw[stage][0]])
        require(all(json.loads(files[p])['ciCommit']==first['ciCommit'] for p in raw[stage]),'Mixed CI merge commits')
        record={'schemaVersion':1,'stage':stage,'status':'TECHNICAL_STUDY_COMPLETE','ciRun':run,'ciCommit':first['ciCommit'],
                'sourceHeadCommit':head,'sourceDigest':first['sourceDigest'],'artStatus':'ART_UNVERIFIED','humanObservers':0,
                'counts':{'identities':6,'scenes':18,'cssFrames':72 if stage=='S3' else 36},'rawReports':raw[stage],
                'uiEvidence':base+'/UI-result.json','metrics':rows[stage],
                'imageArchiveAvailable':True,'archiveTransport':'Git repository full-resolution PNG evidence; not an Actions ZIP',
                'limits':['Fixed frontal neutral surface and three lights only','Reserved coefficient combinations exposed during debugging; not blind generalization','No skin, hair or independent human artistic evaluation']}
        if stage=='S4':record['parentSourceDigest']=source_digest('S3')
        files[f'research/sketch/evidence/{stage}.json']=encoded(record)
    require(sum(map(len,files.values()))<40_000_000,'Unexpected full archive size')
    files[base+'/manifest.json']=encoded({'run':run,'sourceHead':head,'humanObservers':0,'artStatus':'ART_UNVERIFIED',
        'files':{name:{'sha256':digest(data),'bytes':len(data)} for name,data in sorted(files.items())}})
    return files

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):raise RuntimeError('Unexpected Git API redirect')

def publish():
    files=collect();run,head=context();attempt=os.environ.get('GITHUB_RUN_ATTEMPT','')
    require(bool(re.fullmatch(r'[0-9]+',attempt)),'Missing run attempt')
    repo=os.environ.get('GITHUB_REPOSITORY','');require(bool(re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repo)),'Bad repository')
    token=os.environ.get('GITHUB_TOKEN','');require(bool(token),'Evidence publishing needs contents:write')
    base='https://api.github.com/repos/'+repo;opener=urllib.request.build_opener(NoRedirect())
    def api(path,payload=None):
        req=urllib.request.Request(base+path,data=encoded(payload) if payload is not None else None,
            headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json','Content-Type':'application/json','User-Agent':'portrait-evidence-archiver'})
        with opener.open(req,timeout=60) as response:return json.load(response)
    tree_base=api('/git/commits/'+head)['tree']['sha'];entries=[];blobs={}
    for name,data in sorted(files.items()):
        entry={'path':name,'mode':'100644','type':'blob'}
        if name.endswith('.png'):
            checksum=digest(data)
            if checksum not in blobs:
                blobs[checksum]=api('/git/blobs',{'content':base64.b64encode(data).decode(),'encoding':'base64'})['sha']
                time.sleep(.9)
            entry['sha']=blobs[checksum]
        else:entry['content']=data.decode('utf8')
        entries.append(entry)
    tree=api('/git/trees',{'base_tree':tree_base,'tree':entries})['sha']
    commit=api('/git/commits',{'message':f'archive(sketch): measured S3/S4 run {run}, full PNGs and isolated UI proof','tree':tree,'parents':[head]})['sha']
    branch=f'evidence/sketch-s3-s4-{run}-{attempt}'
    api('/git/refs',{'ref':'refs/heads/'+branch,'sha':commit})
    receipt={'branch':branch,'commit':commit,'sourceHead':head,'run':run,'files':len(files),'pngFiles':sum(p.endswith('.png') for p in files),'bytes':sum(map(len,files.values())),'artStatus':'ART_UNVERIFIED'}
    print('DURABLE_STUDY_ARCHIVE '+json.dumps(receipt,sort_keys=True),flush=True)
    summary=os.environ.get('GITHUB_STEP_SUMMARY')
    if summary:
        with open(summary,'a') as out:out.write('Durable full-resolution evidence branch: `'+branch+'`\n\n'+json.dumps(receipt)+'\n')

if __name__=='__main__':
    if len(sys.argv)==3 and sys.argv[1]=='pack':pack(sys.argv[2])
    elif sys.argv[1:]==['publish']:publish()
    else:raise SystemExit('Usage: archive_studies.py pack REGISTERED_IDENTITY | publish')
