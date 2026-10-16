"""Read-only edge locality ablations. These are NOT stage completion receipts.
Uses the already-compiled, hash-verified head-c geometry; no compiler tuning.
"""
import copy,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'workbench'))
import numpy as np
from shapely import union_all,contains_xy
from shapely.geometry import Point
from playwright.sync_api import sync_playwright
from model import CACHE
from study_light import source_digest as s3_digest,content_hash
from study_edges import source_digest as s4_digest
from validate_studies import capture,rgb,ref_rgb,contour_geometry

SHAPE_JS='''(nodes,regions)=>nodes.forEach((node,i)=>{
 const paths=regions[i].rings.filter(r=>r.length>=3);
 if(!paths.length){node.style.clipPath='polygon(0 0,0 0,0 0)';return;}
 const commands=[];
 paths.forEach((path,j)=>{
  commands.push((j?'move to ':'from ')+path[0].map(v=>v.toFixed(5)+'%').join(' '));
  path.slice(1).forEach(p=>commands.push('line to '+p.map(v=>v.toFixed(5)+'%').join(' ')));
  commands.push('close');
 });
 const value='shape(evenodd '+commands.join(',')+')';
 if(!CSS.supports('clip-path',value))throw Error('CSS shape unsupported in diagnostic browser');
 node.style.clipPath=value;
})'''


def main():
 out=CACHE/'studies/diagnostic';out.mkdir(parents=True,exist_ok=True)
 yy,xx=np.mgrid[:320,:320]
 with sync_playwright() as p:
  browser=p.chromium.launch(headless=True,args=['--no-sandbox']);page=browser.new_page(viewport={'width':640,'height':480})
  for light in ['left','front','right']:
   ident='head-c-'+light
   d3=json.loads((CACHE/'studies/S3'/ident/'tone.json').read_text());d4=json.loads((CACHE/'studies/S4'/ident/'tone.json').read_text())
   assert d3['sourceDigest']==s3_digest() and d4['sourceDigest']==s4_digest()
   assert d3['contentHash']==content_hash(d3) and d4['contentHash']==content_hash(d4)
   capture(page,d3,out/(ident+'-base.png'));base=rgb(out/(ident+'-base.png'))
   _,mask=ref_rgb(CACHE/'studies/reference'/(ident+'-shadow.png'))
   for arm in ['selected','hard-only','soft-only']:
    d=copy.deepcopy(d4)
    if arm=='hard-only':d['edgeRegions'][1]['rings']=[]
    if arm=='soft-only':d['edgeRegions'][0]['rings']=[]
    d['diagnosticArm']=arm;d['contentHash']=content_hash(d)
    zones=union_all([contour_geometry(r['rings']).buffer((3*r['blurPixels']+1)/3.2) for r in d['edgeRegions']])
    raw=union_all([contour_geometry(r['rings']) for r in d['edgeRegions']])
    allowed=contains_xy(zones,(xx+.5)/3.2,(yy+.5)/3.2)
    for painter in ['polygon','shape']:
     path=out/(ident+'-'+arm+'-'+painter+'.png');capture(page,d,path)
     if painter=='shape':
      page.locator('#portrait .edge-ribbon i').evaluate_all(SHAPE_JS,d['edgeRegions'])
      page.locator('#portrait').screenshot(path=str(path))
     image=rgb(path);delta=np.abs(image-base).mean(-1);bad=(delta>1)&~allowed
     coords=np.argwhere(bad);coords=sorted(coords,key=lambda q:delta[tuple(q)],reverse=True)[:6]
     data={'id':ident,'arm':arm,'painter':painter,'sourceDigest':s4_digest(),'diagnosticOnly':True,
       'badPixels':int(bad.sum()),'maxOutside':float(delta[~allowed].max()),'inkFraction':float(np.count_nonzero((delta>1)&mask)/mask.sum()),
       'examples':[{'x':int(x),'y':int(y),'before':float(base[y,x,0]),'after':float(image[y,x,0]),'distancePixels':float(raw.distance(Point((x+.5)/3.2,(y+.5)/3.2))*3.2)} for y,x in coords]}
     print('LOCALITY_ABLATION '+json.dumps(data,sort_keys=True),flush=True)
  browser.close()
if __name__=='__main__':main()
