"""Durable S5/S6 numerical and PNG receipts, including failed attempts.
Only a NEW evidence branch is written; main and PR refs are never moved here.
No user review database or credentials enter the bounded archive allowlist.
"""
from __future__ import annotations
import base64,hashlib,json,math,os,re,sys,time,urllib.request
from pathlib import Path
from model import ROOT,CACHE,canonical
from surface_registry import S5,S6,cases,case,case_specs,sample_id,source_digest

UI_CASES={'S5':'head-a-neutral','S6':'novel-a-smile'}
UI_STEPS={'generation','independent verification','view controls','material and hair parameters','offline export','history','mobile layout','zero fabricated reviews'}


def read(path):return json.loads(path.read_text(encoding='utf8'))
def encoded(value):return (json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
def digest(data):return hashlib.sha256(data).hexdigest()
def require(ok,message):
    if not ok:raise ValueError(message)
def write(path,data):path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
def finite(value):return type(value) in (float,int) and math.isfinite(value)


def context():
    run=os.environ.get('GITHUB_RUN_ID','');head=os.environ.get('SOURCE_HEAD_SHA','')
    require(bool(re.fullmatch(r'\d+',run)) and bool(re.fullmatch(r'[a-f0-9]{40}',head)),'Missing exact CI provenance')
    return run,head


def image_check(name,data):
    require(data.startswith(b'\x89PNG\r\n\x1a\n') and len(data)>24,'Invalid PNG '+name)
    width=int.from_bytes(data[16:20],'big');height=int.from_bytes(data[20:24],'big')
    require(0<width<=4096 and 0<height<=8192,'PNG dimension budget '+name)
    if not name.startswith(('workbench-','mobile-')):require((width,height)==(320,320),'Unexpected measurement frame '+name)


def pack(case_id):
    c=case(case_id);run,head=context();folder=CACHE/'surface/evidence'/case_id;target=CACHE/'surface/receipts'/case_id
    files={}
    if folder.exists():
        for path in sorted(folder.iterdir()):
            if path.is_file() and path.suffix in ('.json','.png'):
                data=path.read_bytes();require(len(data)<=8_000_000,'File size budget')
                if path.suffix=='.png':image_check(path.name,data)
                files[path.name]=data
    if 'report.json' not in files:
        files['failure.json']=encoded({'caseId':case_id,'stage':c['stage'],'status':'INCOMPLETE','ciRun':run,'sourceHeadCommit':head,
            'reason':'Compiler or reference failed before measurement; inspect original job log','humanObservers':0,'artStatus':'ART_UNVERIFIED'})
    require(sum(map(len,files.values()))<15_000_000,'Case archive size budget')
    for name,data in files.items():write(target/name,data)
    write(target/'manifest.json',encoded({'caseId':case_id,'stage':c['stage'],'run':run,'head':head,'files':{n:digest(v) for n,v in files.items()}}))
    print('SURFACE_RECEIPT_PACK',case_id,len(files),flush=True)


def check_report(report,case_id,files):
    c=case(case_id);run,head=context();stage=c['stage'];settings=S5['thresholds'];t=S6['thresholds']
    require(report['caseId']==case_id and report['stage']==stage,'Wrong case')
    require(report['ciRun']==run and report['sourceHeadCommit']==head,'Mixed source/run')
    require(report['sourceDigest']==source_digest(stage),'Stale surface implementation')
    require(report['status']=='PASS' and not report['errors'] and not report['externalRequests'],'Failed browser case')
    require(report['humanObservers']==0 and report['artStatus']=='ART_UNVERIFIED','Fabricated art evidence')
    require(re.fullmatch(r'[a-f0-9]{40}',report['ciCommit']) is not None,'Missing actual CI commit')
    require(len(report['calibrationMAE'])==3 and all(finite(x) and 0<=x<2 for x in report['calibrationMAE']),'Calibration failed')
    rows=report['metrics'];require([r['id'] for r in rows]==[sample_id(s) for s in case_specs(case_id)],'Incomplete/reordered lights')
    for row in rows:
        require(row['status']=='PASS' and row['failures']==[],'Failed scene')
        require(row['sourceDigest']==source_digest(stage) and row['stage']==stage,'Wrong scene source')
        require(row['humanObservers']==0 and row['artStatus']=='ART_UNVERIFIED','Not human ratings')
        for metric,limit in [('fullMAE','referenceFullMAE'),('interiorMAE','referenceInteriorMAE'),('featureMAE','referenceFeatureMAE')]:
            require(finite(row['metrics'][metric]) and 0<=row['metrics'][metric]<t[limit],'Base-form fidelity failed')
        require(t['referenceSilhouetteIoU']<=row['metrics']['silhouetteIoU']<=1,'Base silhouette failed')
        require(0<=row['outsideMaskMaxDelta']<=settings['maxOutsideMaskDelta'],'Surface locality failed')
        require(0<=row['protectedMaxDelta']<=settings['maxProtectedDelta'],'Protected feature failed')
        require(0<=row['changedFaceFraction']<=settings['maxChangedFaceFraction'],'Surface coverage failed')
        require(finite(row['surfaceAddedSkinMAE']) and row['surfaceAddedSkinMAE']<=settings['maxAddedSkinError'],'Surface error failed')
        require(row['changedPixels']>=settings['minChangedPixels'],'No-op surface')
        require(row['layerCount']==5 and 0<row['surfaceContourPoints']<=settings['maxAddedContourPoints'],'Surface complexity failed')
        require(row['nonAffineRMS']>t['minimumIdentityNonAffineRMS'],'Identity template collapse')
        require(0<=row['maxExpressionDisplacementSpan']<=t['maxExpressionDisplacementSpan'],'Expression displacement failed')
        require(row['expression']=='neutral' or row['expressionRMS']>=t['minimumExpressionRMS'],'No expression effect')
        require(len(row['imageHashes'])>=10,'Missing measured ablations')
        for name,expected in row['imageHashes'].items():
            require(Path(name).name==name and name.endswith('.png'),'Unsafe image reference')
            require(name in files and digest(files[name])==expected,'Missing/damaged measured image '+name)
        ident=row['renderId'];ref=read_bytes(files[ident+'-reference.json'])
        require(ref['imageHash']==digest(files[ident+'-reference.png']) and ref['geometryHash']==row['geometryHash'],'Wrong independent reference')
        require(ref['surfaceSourceDigest']==source_digest(stage) and ref['identityHash']==row['identityHash'],'Wrong reference provenance')
    if UI_CASES[stage]==case_id:
        ui=read_bytes(files['UI-result.json'])
        require(ui['status']=='PASS' and ui['stage']==stage and ui['sourceHead']==head and ui['ciRun']==run,'Missing real UI receipt')
        require(ui['humanObservers']==0 and ui['reviewData']=='no reviews created; temporary database','UI fabricated reviews')
        require(UI_STEPS<=set(ui['steps']),'Incomplete UI lifecycle')
        for prefix in ('workbench-','mobile-'):require(prefix+stage+'.png' in files,'Missing UI capture')
    return rows


def read_bytes(data):return json.loads(data)


def collect():
    run,head=context();base=f'research/sketch/evidence/raw-surface/{run}';files={};reports={};failures=[];stage_rows={'S5':[],'S6':[]}
    for c in cases('S5')+cases('S6'):
        case_id=c['id'];folder=CACHE/'surface/receipts'/case_id
        if not (folder/'manifest.json').exists():failures.append({'caseId':case_id,'reason':'No receipt; required case did not finish'});continue
        try:
            manifest=read(folder/'manifest.json');require(manifest['run']==run and manifest['head']==head and manifest['caseId']==case_id,'Mixed receipt')
            own={}
            for name,expected in manifest['files'].items():
                require(Path(name).name==name and Path(name).suffix in ('.json','.png'),'Unsafe archive filename')
                data=(folder/name).read_bytes();require(digest(data)==expected and len(data)<=8_000_000,'Damaged receipt')
                if name.endswith('.png'):image_check(name,data)
                own[name]=data;files[f'{base}/{case_id}/{name}']=data
            report=read_bytes(own['report.json']);rows=check_report(report,case_id,own)
            reports[case_id]=report;stage_rows[c['stage']].extend(rows)
        except (ValueError,KeyError,OSError,TypeError) as exc:
            failures.append({'caseId':case_id,'reason':type(exc).__name__+': '+str(exc)})
    # Group invariants use numerical identities, never names inferred from faces.
    try:
        for stage,expected_count in [('S5',18),('S6',45)]:
            rows=stage_rows[stage];require(len(rows)==expected_count,'Incomplete '+stage+' matrix')
            require(len({r['id'] for r in rows})==expected_count,'Duplicate scenes')
            identity_hashes={}
            for row in rows:
                identity_hashes.setdefault(row['identity'],set()).add(row['identityHash'])
            require(all(len(v)==1 for v in identity_hashes.values()),'Identity changed across expression/light')
            require(len({next(iter(v)) for v in identity_hashes.values()})==len(identity_hashes),'Distinct identities collapsed')
            for ident in identity_hashes:
                expressions={r['expression'] for r in rows if r['identity']==ident};pose_hashes=[]
                for expression in expressions:
                    values={r['geometryHash'] for r in rows if r['identity']==ident and r['expression']==expression}
                    require(len(values)==1,'Geometry changed with light');pose_hashes.extend(values)
                require(len(set(pose_hashes))==len(expressions),'Expression geometry collapsed')
        require(len({r['ciCommit'] for r in reports.values()})==1,'Mixed tested commits')
    except ValueError as exc:failures.append({'caseId':'aggregate','reason':str(exc)})
    status='FAIL' if failures else 'PASS'
    receipt={'schemaVersion':1,'status':status,'run':run,'sourceHead':head,'counts':{k:len(v) for k,v in stage_rows.items()},
             'failures':failures,'humanObservers':0,'humanReview':'DEFERRED_BY_OWNER','artStatus':'ART_UNVERIFIED'}
    files[base+'/result.json']=encoded(receipt)
    if status=='PASS':
        for stage,rows in stage_rows.items():
            entry={'schemaVersion':1,'stage':stage,'status':'TECHNICAL_STUDY_COMPLETE','ciRun':run,'sourceHeadCommit':head,
                   'ciCommit':next(iter(reports.values()))['ciCommit'],'sourceDigest':source_digest(stage),'metrics':rows,
                   'counts':{'identities':6 if stage=='S5' else 3,'scenes':len(rows),'expressions':1 if stage=='S5' else 5},
                   'rawReports':[f'{base}/{c["id"]}/report.json' for c in cases(stage)],'uiEvidence':f'{base}/{UI_CASES[stage]}/UI-result.json',
                   'humanObservers':0,'humanReview':'DEFERRED_BY_OWNER','artStatus':'ART_UNVERIFIED','imageArchiveAvailable':True,
                   'scope':'Native CSS material and shared-topology new-mode/expression transfer; not unseen real-person or independent artistic validation',
                   'limitations':['Procedural scalp ribbons, not full 3D hair scattering','Graphite granulation, not skin pores','Same ICT topology; new PCA modes are not individuals','Human artistic review deferred; no default promotion']}
            files[f'research/sketch/evidence/{stage}.json']=encoded(entry)
    files[base+'/manifest.json']=encoded({'run':run,'sourceHead':head,'files':{p:{'sha256':digest(b),'bytes':len(b)} for p,b in sorted(files.items())}})
    require(sum(map(len,files.values()))<100_000_000,'Full evidence archive size budget')
    return files,receipt


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):raise RuntimeError('Unexpected Git API redirect')


def publish():
    files,receipt=collect();run,head=context();attempt=os.environ.get('GITHUB_RUN_ATTEMPT','')
    require(bool(re.fullmatch(r'\d+',attempt)),'Missing attempt');repo=os.environ.get('GITHUB_REPOSITORY','')
    require(bool(re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repo)),'Invalid repository')
    token=os.environ.get('GITHUB_TOKEN','');require(bool(token),'Archive needs contents:write')
    opener=urllib.request.build_opener(NoRedirect());base='https://api.github.com/repos/'+repo
    def api(path,payload=None):
        req=urllib.request.Request(base+path,data=encoded(payload) if payload is not None else None,
            headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json','Content-Type':'application/json','User-Agent':'portrait-surface-evidence'})
        with opener.open(req,timeout=90) as response:return json.load(response)
    parent=api('/git/commits/'+head);tree_base=parent['tree']['sha'];entries=[];blobs={}
    # Existing content-addressed PNG blobs need not be re-uploaded on a repeat
    # verification. Only hash identity is reused, never an old measured PASS.
    existing=api('/git/trees/'+tree_base+'?recursive=1');known={r['sha'] for r in existing.get('tree',[]) if r['type']=='blob'}
    for path,data in sorted(files.items()):
        entry={'path':path,'mode':'100644','type':'blob'}
        if path.endswith('.png'):
            blob=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
            if blob not in known and blob not in blobs:
                observed=api('/git/blobs',{'content':base64.b64encode(data).decode(),'encoding':'base64'})['sha']
                require(observed==blob,'Blob transport hash mismatch');blobs[blob]=True;time.sleep(1.0)
            entry['sha']=blob
        else:entry['content']=data.decode('utf8')
        entries.append(entry)
    tree=api('/git/trees',{'base_tree':tree_base,'tree':entries})['sha']
    commit=api('/git/commits',{'message':f'archive(sketch): S5/S6 run {run} {receipt["status"]}, real PNGs and zero fabricated reviews','tree':tree,'parents':[head]})['sha']
    branch=f'evidence/sketch-s5-s6-{run}-{attempt}';api('/git/refs',{'ref':'refs/heads/'+branch,'sha':commit})
    receipt.update(branch=branch,commit=commit,files=len(files),bytes=sum(map(len,files.values())))
    print('DURABLE_SURFACE_ARCHIVE '+json.dumps(receipt,sort_keys=True),flush=True)
    if os.getenv('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'],'a') as out:out.write('S5/S6 durable evidence: `'+branch+'`\n\n'+json.dumps(receipt)+'\n')
    if receipt['status']!='PASS':raise SystemExit(1)
if __name__=='__main__':
    if len(sys.argv)==3 and sys.argv[1]=='pack':pack(sys.argv[2])
    elif sys.argv[1:]==['publish']:publish()
    else:raise SystemExit('Usage: archive_surface.py pack CASE | publish')
