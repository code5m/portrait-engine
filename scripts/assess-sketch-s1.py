"""Evaluate all scenes before deciding. Technical completion is not ART_PASS."""
import base64,hashlib,io,json,os,sys
import numpy as np
from PIL import Image,ImageDraw
from sketch_s1_model import CONFIG,ROOT,all_cases,field,image_metrics,overlap,unit,shadow_mask
from sketch_s1_provenance import source_digest
OUT=ROOT/'test-results/sketch-s1';P=CONFIG['protocol']

def image(name):return np.asarray(Image.open(OUT/name).convert('RGB'),dtype=float).mean(-1)
def mean(rows,key):return round(float(np.mean([r[key] for r in rows])),5)

def main():
    debug='--debug' in sys.argv
    browser=json.loads((OUT/'browser.json').read_text());frames=browser['frames'];failures=[];metrics=[]
    def check(condition,label):
        if not condition:failures.append(label)
    check(not browser['browserErrors'] and not browser['externalRequests'],'browser errors/requests')
    check(browser['sourceDigest']==source_digest(),'stale browser capture')
    check(browser['offlinePageSha256']==hashlib.sha256((OUT/'lab.html').read_bytes()).hexdigest(),'offline page changed after capture')
    check(len(frames)==138,'missing CSS frames')
    expected_keys=set()
    for case in all_cases():
        variants=['flat16','gradient16','flat32'] if case['shape']['kind']=='ellipsoid' else ['flat32']
        modes=[(v,False,'form') for v in variants]+[('flat32',True,'form'),('flat32',False,'shadow'),('flat32',True,'composite')]
        expected_keys.update((case['id'],v,b,l) for v,b,l in modes)
    actual_keys=[(f['scene'],f['variant'],f['bounce'],f['layer']) for f in frames]
    check(len(set(actual_keys))==len(actual_keys) and set(actual_keys)==expected_keys,'missing or duplicate scene/variant coverage')
    if not debug:check(browser['transport']=='file','inline debugging cannot complete S1')
    summary=[]
    for split in ['baseline','holdout']:
        for variant in ['flat16','gradient16','flat32']:
            rows=[r for r in frames if r['split']==split and r['variant']==variant and r['kind']=='ellipsoid' and r['layer']=='form' and not r['bounce']]
            summary.append({'split':split,'variant':variant,**{k:mean(rows,k) for k in ['interiorMAE','fullMAE','edgeMAE','gradientError']}})
    def arm(split,variant):return next(r for r in summary if r['split']==split and r['variant']==variant)
    gradient=True;flat32=True
    for split in ['baseline','holdout']:
        a,b,c=[arm(split,v) for v in ['flat16','gradient16','flat32']]
        gradient &= b['interiorMAE']<=P['gradientAdoptionRatio']*a['interiorMAE'] and b['fullMAE']<=P['gradientAdoptionRatio']*a['fullMAE'] and b['edgeMAE']<=a['edgeMAE']+P['gradientEdgeAllowance'] and b['gradientError']<=P['gradientAdoptionRatio']*a['gradientError']
        flat32 &= c['interiorMAE']<=P['flat32AdoptionRatio']*a['interiorMAE'] and c['fullMAE']<=a['fullMAE']
    check(flat32,'C32 did not meet registered cross-split adoption criteria')
    reference=json.loads((OUT/'reference.json').read_text()) if (OUT/'reference.json').exists() else None
    if not debug:check(reference is not None,'missing Blender reference manifest')
    for case in all_cases():
        ident,s,l=case['id'],case['shape'],case['light']
        row={'scene':ident,'kind':s['kind'],'split':s['split']};selected=[];ref_errors=[];pair_errors=[]
        for bounce in [False,True]:
            f=next(r for r in frames if r['scene']==ident and r['variant']=='flat32' and r['layer']=='form' and r['bounce']==bounce);selected.append(f)
            check(f['patchCount']<=32,ident+' region budget')
            for key,limit in [('interiorMAE',P['selectedInteriorMAE']),('fullMAE',P['selectedFullMAE']),('edgeMAE',P['selectedEdgeMAE'])]:check(f[key]<limit,f'{ident} bounce={bounce} {key}={f[key]} >= {limit}')
            expected,mask,_=field(s,l,bounce)
            if reference:
                ref=image(f'reference-{ident}-{int(bounce)}.png');refm=image_metrics(ref,expected,mask);pair=image_metrics(image(f['file']),ref,mask)
                ref_errors.append(refm['interiorMAE']);pair_errors.append(pair['interiorMAE'])
                check(refm['interiorMAE']<P['referenceInteriorMAE'],f'{ident} reference normal calibration {refm}')
                check(pair['interiorMAE']<P['selectedInteriorMAE'],f'{ident} CSS/Blender mismatch {pair}')
        row.update(cssVsAnalyticMAE=max(r['interiorMAE'] for r in selected),fullMAE=max(r['fullMAE'] for r in selected),edgeMAE=max(r['edgeMAE'] for r in selected))
        if reference:row.update(referenceVsAnalyticMAE=max(ref_errors),cssVsBlenderMAE=max(pair_errors))
        shadow=next(r for r in frames if r['scene']==ident and r['layer']=='shadow')
        check(shadow['iou']>=P['shadowIoU'],ident+' analytic shadow overlap');check(shadow['centroidPixels']<P['shadowCentroidPixels'],ident+' analytic shadow centroid')
        row['analyticShadowIoU']=shadow['iou']
        composite=next(r for r in frames if r['scene']==ident and r['layer']=='composite')
        form,mask,_=field(s,l,True);g=unit(CONFIG['groundNormal']);direction=unit(l['direction'])
        ground_value=CONFIG['receiverAlbedo']*(CONFIG['ambient']+CONFIG['direct']*max(0,float(g@direction)))
        shadow_value=CONFIG['receiverAlbedo']*CONFIG['ambient']
        shade=shadow_mask(s,l,shadow['ground']['offset'])
        ground=np.where(shade,shadow_value,ground_value)
        ground=255*np.where(ground<=.0031308,12.92*ground,1.055*ground**(1/2.4)-.055)
        row['compositeMAE']=round(float(np.abs(image(composite['file'])-np.where(mask,form,ground)).mean()),5)
        check(row['compositeMAE']<P['selectedFullMAE'],ident+' composite plane/shadow/form alignment')
        if reference:
            ref=image('shadow-reference-'+ident+'.png')
            check(ref.max()>50 and ref.min()<5,ident+' physical shadow pass is empty or unlit')
            measured=overlap(image(shadow['file'])<128,ref<ref.max()*.5)
            check(measured['iou']>=P['shadowIoU'],f'{ident} Cycles shadow IoU {measured}')
            check(measured['centroidPixels']<P['shadowCentroidPixels'],ident+' Cycles shadow centroid')
            row['shadowIoU']=measured['iou'];row['shadowCentroidPixels']=measured['centroidPixels']
        _,mask,n=field(s,l,True)
        delta=image(selected[1]['file'])-image(selected[0]['file']);row['bounceMeanDelta']=round(float(delta[mask].mean()),5)
        check(row['bounceMeanDelta']>.5,ident+' reflected light did not visibly affect surface')
        metrics.append(row)
    if reference:
        check(reference['sourceDigest']==source_digest(),'stale Blender reference')
        expected_refs={f'reference-{c["id"]}-{int(b)}.png' for c in all_cases() for b in [False,True]}|{'shadow-reference-'+c['id']+'.png' for c in all_cases()}
        check(len(reference['outputs'])==81 and {r['file'] for r in reference['outputs']}==expected_refs,'missing or duplicate reference frames')
        for record in reference['outputs']:check(hashlib.sha256((OUT/record['file']).read_bytes()).hexdigest()==record['sha256'],'reference image hash drift')
    for f in frames:check(hashlib.sha256((OUT/f['file']).read_bytes()).hexdigest()==f['sha256'],'CSS image hash drift')
    report={'schemaVersion':1,'stage':'S1','status':'LOCAL_ONLY' if debug else ('FAILED' if failures else 'FORM_STUDY_COMPLETE'),'artStatus':'ART_UNVERIFIED','humanObservers':0,'transport':browser['transport'],'ciRun':os.getenv('GITHUB_RUN_ID'),'ciCommit':os.getenv('GITHUB_SHA'),'sourceHeadCommit':os.getenv('SOURCE_HEAD_SHA'),'sourceDigest':source_digest(),'counts':{'cases':27,'cssFrames':len(frames),'referenceFrames':len(reference['outputs']) if reference else 0,'baselineCases':15,'holdoutCases':12},'selectedRepresentation':'flat32' if flat32 else None,'gradientCandidate':'ACCEPTABLE_TECHNICALLY' if gradient else 'REJECTED_NUMERIC','comparisons':summary,'metrics':metrics,'failures':failures,'browserVersion':browser['browser'],'blenderVersion':reference['blenderVersion'] if reference else None,'performance':{'maxPatches':max(r['patchCount'] for r in frames),'maxSceneDom':max(r['nodeCount'] for r in frames),'generateMsMedian':round(float(np.median([r['generateMs'] for r in frames])),3),'generateMsP95':round(float(np.percentile([r['generateMs'] for r in frames],95)),3),'scope':'single browser process observations; not a speedup claim'},'offlinePageSha256':hashlib.sha256((OUT/'lab.html').read_bytes()).hexdigest(),'limitations':['Finite tonal bands remain; no global blur is used','Only convex analytic primitives and fixed orthographic camera','Hard directional shadows; grazing/back-side lights explicitly rejected','Hemisphere bounce assumes an infinite uniformly lit diffuse receiver; no bounce occlusion or multiple scattering','No transfer to head anatomy and no independent portrait realism evidence'],'artifactStorage':'Full files generated in CI; artifact upload may fail due to account quota. Labeled compact previews and exact completion JSON are also logged.'}
    report['imageHashes']={'comparison.png':hashlib.sha256((OUT/'comparison.png').read_bytes()).hexdigest(),'workbench.png':hashlib.sha256((OUT/'workbench.png').read_bytes()).hexdigest()}
    (OUT/'assessment.json').write_text(json.dumps(report,indent=2))
    if failures:
        print('S1_FAILED',json.dumps(failures));raise SystemExit(1)
    if not debug:
        check(bool(report['ciRun']) and bool(report['ciCommit']),'completion requires real CI provenance')
        if failures:raise SystemExit(failures)
        (OUT/'completion.json').write_text(json.dumps(report,indent=2))
        print('S1_COMPLETION_JSON '+json.dumps(report,separators=(',',':')))
        contact=Image.new('RGB',(4*256,4*280),'white');draw=ImageDraw.Draw(contact)
        for i,ident in enumerate(['sphere-left','wide-left','cylinder-left','wedge-left']):
            for j,(name,label) in enumerate([(f'reference-{ident}-1.png','Blender / hemisphere model'),(f'{ident}--flat32--1--form.png','CSS / same model'),(f'shadow-reference-{ident}.png','Cycles / physical shadow'),(f'{ident}--flat32--0--shadow.png','CSS / geometry shadow')]):
                contact.paste(Image.open(OUT/name).convert('RGB'),(j*256,i*280+24));draw.text((j*256+4,i*280+5),label,fill='black')
        contact.save(OUT/'reference-contact.png')
        for name in ['comparison.png','reference-contact.png']:
            im=Image.open(OUT/name).convert('RGB');im.thumbnail((768,850));buf=io.BytesIO();im.save(buf,format='JPEG',quality=70,optimize=True)
            print('S1_PREVIEW_JPEG '+name+' '+base64.b64encode(buf.getvalue()).decode())
    else:print('S1_DEBUG_SUMMARY',json.dumps({'comparisons':summary,'failures':failures,'performance':report['performance']}))

if __name__=='__main__':main()
