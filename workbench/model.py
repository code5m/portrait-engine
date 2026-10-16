"""S2 reference-data preparation. No source code downloaded is executed.
Meshes remain numerical inputs. No raster/texture ever enters the CSS compiler.
"""
from __future__ import annotations
import hashlib,json,os,urllib.request,time
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
CONFIG=json.loads((ROOT/'research/sketch/s2-protocol.json').read_text(encoding='utf8'))
LOCK=json.loads((ROOT/'workbench/sources.json').read_text(encoding='utf8'))
CACHE=Path(os.environ.get('PORTRAIT_DATA',str(ROOT/'data/workbench'))).resolve()

def sha(data:bytes)->str:return hashlib.sha256(data).hexdigest()
def canonical(obj)->bytes:return json.dumps(obj,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
def source_digest()->str:
    paths=json.loads((ROOT/'workbench/source-files.json').read_text())
    h=hashlib.sha256()
    for p in sorted(paths):h.update(p.encode()+b'\0'+(ROOT/p).read_bytes()+b'\0')
    return h.hexdigest()
def save_json(path:Path,data)->None:
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_bytes(canonical(data));tmp.replace(path)
def prepare(progress=print):
    folder=CACHE/'vendor';folder.mkdir(parents=True,exist_ok=True)
    result=[]
    for path,expected in LOCK['files']:
        dest=folder/Path(path).name
        data=dest.read_bytes() if dest.exists() else None
        if data is None:
            url='https://raw.githubusercontent.com/'+LOCK['repository']+'/'+LOCK['commit']+'/'+path
            last=None
            for attempt in range(3):
                try:
                    with urllib.request.urlopen(url,timeout=45) as r:data=r.read(5_000_001)
                    break
                except OSError as e:last=e;time.sleep(attempt+1)
            if data is None:raise RuntimeError('Reference download failed: '+path) from last
        if len(data)>5_000_000:raise ValueError('Reference file too large')
        blob=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
        if blob!=expected:raise ValueError('Pinned reference hash mismatch: '+path)
        dest.write_bytes(data);result.append({'path':path,'blob':blob,'sha256':sha(data),'bytes':len(data)})
        progress('SOURCE_VERIFIED '+path)
    save_json(CACHE/'source-verification.json',{'repository':LOCK['repository'],'commit':LOCK['commit'],'files':result})
    return result

def obj_file(path):
    vertices=[];faces=[];groups=[];face_index=0
    for line in Path(path).read_text().splitlines():
        if line.startswith('v '):vertices.append([float(x) for x in line.split()[1:4]])
        elif line.startswith('f '):
            ids=[int(x.split('/')[0])-1 for x in line.split()[1:]]
            # Skin/head, eye and mouth sockets, eyeballs. No lashes/film/texture.
            if face_index<14034 or 21496<=face_index<24692:
                for j in range(1,len(ids)-1):faces.append([ids[0],ids[j],ids[j+1]]);groups.append(face_index)
            face_index+=1
    v=np.asarray(vertices,dtype=float);f=np.asarray(faces,dtype=np.int32)
    if v.shape!=(26719,3) or face_index!=26384 or not np.isfinite(v).all():raise ValueError('Unexpected ICT topology')
    return v,f,np.asarray(groups)

def unit(v):
    a=np.asarray(v,dtype=float);norm=np.linalg.norm(a,axis=-1,keepdims=True)
    return a/np.maximum(norm,1e-15)

class HeadModel:
    def __init__(self):
        for path,expected in LOCK['files']:
            data=(CACHE/'vendor'/Path(path).name).read_bytes()
            if hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()!=expected:raise ValueError('Reference cache modified')
        self.base,self.faces,self.groups=obj_file(CACHE/'vendor/generic_neutral_mesh.obj')
        modes=[]
        for i in range(6):
            v,f,g=obj_file(CACHE/'vendor'/('identity%03d.obj'%i))
            if not np.array_equal(f,self.faces):raise ValueError('PCA topology differs')
            modes.append(v-self.base)
        self.modes=np.asarray(modes)
        # Freeze one crop/camera on NEUTRAL, never re-fit per character.
        floor=float(self.base[:9409,1].min()-0.5)
        mask=(self.base[self.faces,1]>=floor).all(axis=1)
        self.faces=self.faces[mask];self.groups=self.groups[mask]
        used=np.unique(self.faces);bounds=np.array([self.base[used].min(0),self.base[used].max(0)])
        self.camera={'center':[float((bounds[0,0]+bounds[1,0])/2),float((bounds[0,1]+bounds[1,1])/2)],
                     'span':float(max(bounds[1,0]-bounds[0,0],bounds[1,1]-bounds[0,1])*1.15)}
        self.regions=self._regions()
    def _regions(self):
        # Semantic surface partitions only: not measured skull/bone anatomy.
        # Neutral topology assignment is frozen across identities and lights.
        p=self.base[self.faces].mean(1);x=np.abs(p[:,0]);y=p[:,1]
        region=np.zeros(len(p),dtype=int)
        region[y>5.3]=1  # cranial/forehead
        region[(y>1.6)&(y<=5.3)]=2 # brow/orbital envelope
        region[(y>-2.9)&(y<=3.5)&(x<1.75)]=3 # nasal root/bridge/base
        region[(y>-4.8)&(y<=1.6)&(x>=1.75)]=4 # cheek/malar surface
        region[(y>-6.3)&(y<=-2.9)&(x<3.1)]=5 # mouth/perioral
        region[y<=-6.3]=6 # lower jaw/chin
        region[(self.groups>=13226)&(self.groups<14034)]=2
        region[self.groups>=21496]=7 # eyeballs
        return region
    def mesh(self,weights):
        if not isinstance(weights,list) or len(weights)!=6 or any(type(x) not in (float,int) or not np.isfinite(x) or abs(x)>1.5 for x in weights):raise ValueError('Six finite coefficients in [-1.5,1.5] required')
        v=self.base+np.einsum('i,ijk->jk',np.asarray(weights),self.modes)
        f=self.faces;p=v[f];cross=np.cross(p[:,1]-p[:,0],p[:,2]-p[:,0]);areas=np.linalg.norm(cross,axis=1)
        if not np.isfinite(v).all() or np.count_nonzero(areas<1e-10)>len(f)*.001:raise ValueError('Degenerate identity geometry')
        n=np.zeros_like(v)
        for i in range(3):np.add.at(n,f[:,i],cross)
        return v,f,unit(n),self.regions
    def signature(self,weights):
        v,_,_,_=self.mesh(weights);base=self.base[:9409];target=v[:9409]
        fit=np.linalg.lstsq(np.c_[base,np.ones(len(base))],target,rcond=None)[0]
        residual=float(np.sqrt(np.mean((np.c_[base,np.ones(len(base))]@fit-target)**2))/self.camera['span'])
        return {'geometryHash':sha(v.astype('<f8').tobytes()),'nonAffineRMS':residual,
                'weights':weights,'camera':self.camera,'surfaceOnly':True}

if __name__=='__main__':
    prepare();m=HeadModel();print('S2_MODEL_READY',json.dumps({'camera':m.camera,'regions':np.bincount(m.regions).tolist(),'modeRMS':np.sqrt(np.mean(m.modes**2,axis=(1,2))).tolist(),'keys':list(json.loads((CACHE/'vendor/vertex_indices.json').read_text()))}))
