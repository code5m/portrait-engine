"""Additional pinned numerical PCA/expression shapes; original S2 stays frozen.
PCA modes are NOT individual people. No downloaded code or raster is executed.
"""
from __future__ import annotations
import hashlib,json,time,urllib.request
from pathlib import Path
import numpy as np
from model import ROOT,CACHE,HeadModel,obj_file,unit,canonical,sha,save_json
from surface_registry import S6,geometry_source_digest

EXTRA=json.loads((ROOT/'workbench/surface-sources.lock.json').read_text())


def blob_hash(data):return hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()


def prepare_extra():
    folder=CACHE/'surface-vendor';folder.mkdir(parents=True,exist_ok=True);records=[]
    for path,expected in EXTRA['files']:
        dest=folder/Path(path).name
        if dest.exists():data=dest.read_bytes()
        else:
            url='https://raw.githubusercontent.com/'+EXTRA['repository']+'/'+EXTRA['commit']+'/'+path
            data=None;last=None
            for attempt in range(3):
                try:
                    with urllib.request.urlopen(url,timeout=60) as response:data=response.read(5_000_001)
                    break
                except OSError as exc:last=exc;time.sleep(attempt+1)
            if data is None:raise RuntimeError('Pinned numerical source unavailable: '+path) from last
        if len(data)>5_000_000 or blob_hash(data)!=expected:raise ValueError('Pinned additional source hash mismatch: '+path)
        tmp=dest.with_suffix('.tmp');tmp.write_bytes(data);tmp.replace(dest)
        records.append({'path':path,'blob':expected,'sha256':sha(data),'bytes':len(data)})
    save_json(CACHE/'surface-source-verification.json',{'repository':EXTRA['repository'],'commit':EXTRA['commit'],'files':records})
    return records


class PoseModel:
    def __init__(self,base_model,extra_weights,expression):
        if expression not in S6['expressions']:raise ValueError('Unregistered expression')
        a=np.asarray(extra_weights,dtype=float)
        if a.shape!=(3,) or not np.isfinite(a).all() or np.max(np.abs(a))>1.5:raise ValueError('Invalid additional coefficients')
        self.model=base_model;self.camera=base_model.camera;self.extra_weights=a;self.expression=expression
        self.extra_delta=np.zeros_like(base_model.base);self.expression_delta=np.zeros_like(base_model.base)
        active=[('identity%03d.obj'%(6+i),float(w),False) for i,w in enumerate(a) if w]
        active += [(name,float(w),True) for name,w in S6['expressions'][expression].items()]
        if active:
            prepare_extra()
            _,topology,_=obj_file(CACHE/'vendor/generic_neutral_mesh.obj')
            expected={Path(p).name:h for p,h in EXTRA['files']}
            for name,weight,is_expression in active:
                path=CACHE/'surface-vendor'/name;raw=path.read_bytes()
                if blob_hash(raw)!=expected[name]:raise ValueError('Additional model cache changed')
                v,f,_=obj_file(path)
                if not np.array_equal(f,topology):raise ValueError('Additional shape topology mismatch')
                delta=(v-base_model.base)*weight
                if is_expression:self.expression_delta+=delta
                else:self.extra_delta+=delta

    def neutral_vertices(self,weights):return self.model.mesh(weights)[0]+self.extra_delta

    def mesh(self,weights):
        _,f,_,regions=self.model.mesh(weights)
        v=self.neutral_vertices(weights)+self.expression_delta
        tri=v[f];cross=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0])
        if not np.isfinite(v).all() or np.count_nonzero(np.linalg.norm(cross,axis=1)<1e-10)>len(f)*.001:
            raise ValueError('Degenerate expression geometry')
        n=np.zeros_like(v)
        for i in range(3):np.add.at(n,f[:,i],cross)
        return v,f,unit(n),regions

    def signature(self,weights):
        neutral=self.neutral_vertices(weights);v=neutral+self.expression_delta
        base=self.model.base[:9409];target=neutral[:9409]
        design=np.c_[base,np.ones(len(base))];fit=np.linalg.lstsq(design,target,rcond=None)[0]
        return {'geometryHash':sha(v.astype('<f8').tobytes()),'identityHash':sha(neutral.astype('<f8').tobytes()),
                'weights':list(weights),'extraWeights':self.extra_weights.tolist(),'expression':self.expression,
                'camera':self.camera,'surfaceOnly':True,'modelSourceDigest':geometry_source_digest(),
                'nonAffineRMS':float(np.sqrt(np.mean((design@fit-target)**2))/self.camera['span']),
                'expressionRMS':float(np.sqrt(np.mean(self.expression_delta**2))/self.camera['span']),
                'maxExpressionDisplacementSpan':float(np.linalg.norm(self.expression_delta,axis=1).max()/self.camera['span'])}
