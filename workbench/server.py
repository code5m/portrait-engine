"""Local-first allowlisted research API; machine and human records stay separate.
S2 numerical history is immutable. S3-S6 are opt-in experiments, never ART_PASS.
This is for a trusted research group, not a public multi-tenant service.
"""
from __future__ import annotations
import argparse,contextlib,copy,hashlib,hmac,http.cookies,json,os,queue,re,secrets,shutil,sqlite3,subprocess,sys,threading,time
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit,unquote
from model import ROOT,CACHE,CONFIG,HeadModel,prepare,source_digest,canonical,sha,save_json
from surface_registry import catalog as surface_catalog,validate_payload as validate_surface_payload
from stage_archive import stage_result,image_data,validate_stage_review
# One origin: / shows the original CSS portrait; /workbench/ hosts the
# authenticated research and evidence lab. API endpoints remain /api/v1/.
STATIC={
    '/workbench':'index.html','/workbench/':'index.html',
    '/workbench/app.mjs':'app.mjs','/workbench/style.css':'style.css',
    '/workbench/renderer.mjs':'renderer.mjs',
    '/workbench/study_renderer.mjs':'study_renderer.mjs',
    '/workbench/surface_renderer.mjs':'surface_renderer.mjs',
    '/workbench/pipeline_renderer.mjs':'pipeline_renderer.mjs',
    '/workbench/api-guide':'api.html',
    '/api-guide':'api.html'
}
ROOT_STATIC_DIRS=('src','styles','study')
ROOT_STATIC_FILES=frozenset(('index.html','standalone.html'))
ROOT_MIME={'.html':'text/html; charset=utf-8','.css':'text/css; charset=utf-8',
           '.mjs':'text/javascript; charset=utf-8','.js':'text/javascript; charset=utf-8',
           '.json':'application/json; charset=utf-8',
           '.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg','.webp':'image/webp'}

def portrait_static(path):
    """Allowlist public portrait UI assets, never .git, research evidence or data."""
    relative=path.lstrip('/')
    parts=relative.split('/')
    if relative not in ROOT_STATIC_FILES and not (
        len(parts)>1 and parts[0] in ROOT_STATIC_DIRS
    ):return None
    file=(ROOT/relative).resolve()
    if not file.is_relative_to(ROOT.resolve()) or not file.is_file():return None
    kind=ROOT_MIME.get(file.suffix.lower())
    if not kind:return None
    return file,kind

def studio_home():
    """Non-destructive navigation: frozen original HTML and standalone stay byte-identical."""
    document=(ROOT/'index.html').read_text(encoding='utf8')
    slot='<div class="topbar-right">'
    if document.count(slot)!=1:raise RuntimeError('Original portrait navigation anchor changed')
    link='<a class="lab-entry" href="/workbench/" aria-label="进入研究实验室和阶段审核">研究实验室 · 阶段审核 ↗</a>'
    css='''<style>
    .lab-entry{color:#e4c69e;border:1px solid #6b6a56;padding:8px 12px;border-radius:5px;
      font-size:11px;font-weight:600;white-space:nowrap;text-decoration:none}
    .lab-entry:hover{background:#343a32;border-color:#c0a27c}
    .lab-entry:focus-visible{outline:2px solid #d8a878;outline-offset:3px}
    @media(max-width:800px){.topbar-right{gap:8px}.lab-entry{font-size:11px}}
    @media(max-width:520px){.lab-entry{font-size:10px;padding:7px;white-space:normal;max-width:128px;text-align:center}}
    </style>'''
    return document.replace(slot,slot+link,1).replace('</head>',css+'</head>',1)

ID=re.compile(r'^[a-z0-9-]{1,80};MAX_BODY=32768
DIMS=['structure','volume','eyes','identity','realism']
STAGES=('S2','S3','S4','S5','S6')
TOKEN=os.getenv('PORTRAIT_TOKEN','');MODEL=None;JOBS=queue.Queue(maxsize=8);SESSIONS={};LOCK=threading.RLock()


def descriptor_digest(d):
    stage=d.get('stage','S2')
    if stage=='S2':return source_digest()
    from study_service import current_digest
    return current_digest(stage)


@contextlib.contextmanager
def db():
    CACHE.mkdir(parents=True,exist_ok=True)
    c=sqlite3.connect(CACHE/'state.sqlite3',timeout=15);c.row_factory=sqlite3.Row
    try:
        with c:yield c
    finally:c.close()


def initialize():
    with db() as c:
        c.executescript('''PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY,operation TEXT,payload TEXT,status TEXT,result TEXT,error TEXT,created REAL);
        CREATE TABLE IF NOT EXISTS reviews(id TEXT PRIMARY KEY,reviewer TEXT,render_id TEXT,source_digest TEXT,content_hash TEXT,payload TEXT,created REAL);
         CREATE TABLE IF NOT EXISTS stage_reviews(id TEXT PRIMARY KEY,reviewer TEXT,stage TEXT,scene_id TEXT,revision TEXT,payload TEXT,created REAL);
        CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,kind TEXT,payload,created REAL);
        ''')
        c.execute("UPDATE jobs SET status='failed',error='Server restarted; retry explicitly' WHERE status IN ('queued','running')")


def emit(kind,data):
    with db() as c:c.execute('INSERT INTO events(kind,payload,created) VALUES(?,?,?)',(kind,canonical(data).decode(),time.time()))


def json_file(path):return json.loads(path.read_text(encoding='utf8'))
def read_render(ident):
    if not isinstance(ident,str) or not ID.fullmatch(ident):raise ValueError('Invalid render identifier')
    path=CACHE/'renders'/(ident+'.json')
    if not path.exists():raise FileNotFoundError('Render not found')
    return json_file(path)


def operation(op,payload):
    global MODEL
    if op=='prepare':
        files=prepare(lambda msg:print(msg,flush=True));MODEL=HeadModel()
        return {'files':len(files),'sourceDigest':source_digest(),'ready':True}
    if op=='render':
        if MODEL is None:MODEL=HeadModel()
        if payload.get('stage','S2')!='S2':
            from study_service import render
            return render(payload,MODEL)
        from geometry import Projection
        weights=payload['weights'];light=payload['light'];key=sha(canonical({'weights':weights,'light':light,'source':source_digest()}))[:24]
        descriptor=Projection(MODEL,weights).describe(light);descriptor['id']=key
        save_json(CACHE/'renders'/(key+'.json'),descriptor)
        save_json(CACHE/'specs'/(key+'.json'),{'id':key,'weights':weights,'light':light})
        return {'renderId':key,'contentHash':descriptor['contentHash'],'sourceDigest':descriptor['sourceDigest']}
    if op=='verify':
        ident=payload['renderId'];d=read_render(ident)
        if d['sourceDigest']!=descriptor_digest(d):raise ValueError('STALE_RENDER: regenerate using current source')
        if d.get('stage','S2')!='S2':
            from study_service import verify
            return verify(ident,d)
        blender=os.getenv('PORTRAIT_BLENDER') or shutil.which('blender')
        if not blender:raise RuntimeError('DEPENDENCY_MISSING: independent machine verification requires Blender')
        spec=CACHE/'specs'/(ident+'.json')
        if not spec.exists():save_json(spec,{'id':ident,'weights':d['geometry']['weights'],'light':d['light']})
        log=CACHE/'logs'/(ident+'.log');log.parent.mkdir(parents=True,exist_ok=True)
        with log.open('w') as f:
            for command in [[blender,'--background','--python-exit-code','1','--python',str(ROOT/'workbench/reference.py'),'--',str(spec)],
                            [sys.executable,str(ROOT/'workbench/validate.py'),ident]]:
                subprocess.run(command,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,timeout=240,check=True,env=os.environ.copy())
        return json_file(CACHE/'machine'/(ident+'.json'))
    raise ValueError('Unknown operation')


def worker():
    while True:
        job_id,op,payload=JOBS.get()
        with db() as c:c.execute("UPDATE jobs SET status='running' WHERE id=?",(job_id,))
        try:
            result=operation(op,payload)
            with db() as c:c.execute("UPDATE jobs SET status='succeeded',result=? WHERE id=?",(canonical(result).decode(),job_id))
        except Exception as exc:
            error=(type(exc).__name__+': '+str(exc))[:800]
            with db() as c:c.execute("UPDATE jobs SET status='failed',error=? WHERE id=?",(error,job_id))
        finally:emit('job-ended',{'id':job_id});JOBS.task_done()


def validate_render_payload(data):
    if data.get('stage') in ('S5','S6'):return validate_surface_payload(data)
    if set(data)-{'identity','weights','light','stage'}:raise ValueError('Unknown render field')
    stage=data.get('stage','S2')
    if stage not in ('S2','S3','S4'):raise ValueError('Choose an explicitly registered study: S2-S6')
    identities={i['id']:i for i in CONFIG['identities']};lights={l['id']:l['direction'] for l in CONFIG['lights']}
    if 'weights' in data:weights=data['weights']
    else:
        if data.get('identity') not in identities:raise ValueError('Choose an identity')
        weights=identities[data['identity']]['weights']
    if not isinstance(weights,list) or len(weights)!=6 or any(type(x) not in (int,float) or not -1.5<=x<=1.5 for x in weights):raise ValueError('Six finite weights between -1.5 and 1.5 required')
    if data.get('light','left') not in lights:raise ValueError('Unknown light')
    return {'weights':weights,'light':lights[data.get('light','left')],'stage':stage}


def review_payload(data,d):
    allowed={'renderId','sourceDigest','contentHash','verdict','scores','note','annotations','humanConfirmed','viewMode'}
    if set(data)-allowed:raise ValueError('Unknown review field; machine status cannot be supplied')
    if data.get('sourceDigest')!=descriptor_digest(d) or data.get('sourceDigest')!=d['sourceDigest'] or data.get('contentHash')!=d['contentHash']:raise ValueError('STALE_REVIEW: sample/source changed')
    if data.get('verdict') not in ('accept','revise','reject'):raise ValueError('Choose accept, revise or reject')
    if data.get('humanConfirmed') is not True:raise ValueError('Human confirmation required')
    scores=data.get('scores',{})
    if not isinstance(scores,dict) or set(scores)!=set(DIMS) or any(type(v) is not int or not 1<=v<=5 for v in scores.values()):raise ValueError('All five scores must be integers 1..5')
    views={'tone','structure'}
    if d.get('stage') in ('S3','S4','S5','S6'):views.add('masses')
    if d.get('stage') in ('S4','S5','S6'):views.add('edges-control')
    if d.get('stage') in ('S5','S6'):views.update(('material-control','hair-control'))
    if data.get('viewMode','tone') not in views:raise ValueError('Unknown review view')
    if not isinstance(data.get('note',''),str) or len(data.get('note',''))>2000:raise ValueError('Note too long')
    annotations=data.get('annotations',[])
    if not isinstance(annotations,list) or len(annotations)>30:raise ValueError('At most 30 annotations')
    for a in annotations:
        if not isinstance(a,dict) or set(a)!={'x','y','note'} or any(type(a[k]) not in (int,float) or not 0<=a[k]<=1 for k in ('x','y')) or not isinstance(a['note'],str) or len(a['note'])>300:raise ValueError('Invalid annotation')
    return {**data,'stage':d.get('stage','S2'),'viewMode':data.get('viewMode','tone'),
            'reviewType':'AUTOMATED_TEST' if os.getenv('PORTRAIT_TEST_MODE')=='1' else 'OWNER_SELF_REPORTED',
            'blinded':False,'observerIndependence':'NOT_VERIFIED','artStatus':'ART_UNVERIFIED'}


def validation(ident,d):
    digest=descriptor_digest(d)
    path=CACHE/'machine'/(ident+'.json');machine=json_file(path) if path.exists() else {'status':'NOT_RUN'}
    if machine.get('contentHash')!=d['contentHash'] or machine.get('sourceDigest')!=digest:machine={'status':'STALE' if path.exists() else 'NOT_RUN'}
    with db() as c:reviews=[json.loads(x['payload']) for x in c.execute('SELECT payload FROM reviews WHERE render_id=? AND source_digest=? AND content_hash=? ORDER BY created',(ident,digest,d['contentHash']))]
    latest={(r['reviewerSession'],r.get('viewMode','tone')):r for r in reviews}
    candidate_reviews=[r for r in latest.values() if not r.get('viewMode','tone').endswith('-control')]
    verdicts={r['verdict'] for r in candidate_reviews}
    tone_accepts=any(r['verdict']=='accept' and r.get('viewMode','tone')=='tone' for r in candidate_reviews)
    human='PENDING' if not verdicts else ('REJECT' if 'reject' in verdicts else ('REVISE' if 'revise' in verdicts else ('ACCEPT' if tone_accepts else 'PENDING')))
    decision='PENDING' if machine['status']!='PASS' or human=='PENDING' else ('OWNER_ACCEPTED' if human=='ACCEPT' else 'REVISION_REQUIRED')
    return {'machine':machine,'human':{'status':human,'reviews':reviews,'selfReportedSessions':len({k[0] for k in latest}),
            'independentHumansVerified':False},'decision':decision,'artStatus':'ART_UNVERIFIED','independentObservers':'NOT_VERIFIED',
            'stage':d.get('stage','S2'),'humanReview':json_file(ROOT/'research/sketch/stages.json').get('humanReview',{})}


def openapi_schema():
    """Extend the compatible v1 schema with stage-specific bounded inputs."""
    schema=json_file(ROOT/'workbench/openapi.json');schemas=schema['components']['schemas'];old=schemas['RenderPayload']
    surface=surface_catalog();new=copy.deepcopy(old);new['properties']['stage']={'enum':['S5','S6']}
    new['properties'].update(expression={'enum':surface['expressions'],'default':'neutral'},
                             material={'enum':surface['materials'],'default':'graphite'},hair={'enum':surface['hairstyles'],'default':'swept'})
    s5_condition={
        'if':{'properties':{'stage':{'const':'S5'}}},
        'then':{'properties':{'expression':{'const':'neutral'}},'not':{'required':['identity','weights']}}
    }
    s6_condition={
        'if':{'properties':{'stage':{'const':'S6'}}},
        'then':{
            'required':['identity'],
            'not':{'required':['weights']},
            'properties':{'identity':{'enum':[i['id'] for i in surface['identities']]}}
        }
    }
    new['required']=['stage'];new['allOf']=[s5_condition,s6_condition]
    schemas['RenderPayload']={'oneOf':[old,new]}
    schemas['Review']['properties']['viewMode']['enum']+=['material-control','hair-control']
    schemas['Review']['properties']['viewMode']['description']='Stage-bound views. masses: S3-S6; edges-control: S4-S6; material-control/hair-control: S5-S6. No control view can accept the candidate.'
    schema['info'].update(version='1.2.0',description='S2-S6 opt-in numerical/CSS research. Human review deferred by owner; no automated ART_PASS or default promotion. S6 tests new PCA modes, not real-person recognition.')
    schema['paths']['/api/v1/catalog']['get']['summary']='S2-S6 catalog, new-mode identities, expressions, materials and hair choices'
    return schema


class Handler(BaseHTTPRequestHandler):
    server_version='PortraitWorkbench/1'
    def log_message(self,*args):pass
    def setup(self):super().setup();self.connection.settimeout(15)
    def headers_ok(self):
        host=self.headers.get('Host','')
        if host not in self.server.allowed_hosts:raise PermissionError('Host not allowed')
        origin=self.headers.get('Origin')
        if origin and origin not in self.server.allowed_origins:raise PermissionError('Cross-origin access denied')
    def send(self,status,data,kind='application/json; charset=utf-8',extra=None):
        body=canonical(data) if kind.startswith('application/json') else (data.encode() if isinstance(data,str) else data)
        self.send_response(status);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(body)))
        self.send_header('X-Content-Type-Options','nosniff');self.send_header('Referrer-Policy','no-referrer');self.send_header('Cache-Control','no-store')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
        if extra:
            for k,v in extra.items():self.send_header(k,v)
        self.end_headers();self.wfile.write(body)
    def session(self,write=False):
        auth=self.headers.get('Authorization','')
        if TOKEN and auth.startswith('Bearer ') and hmac.compare_digest(auth[7:],TOKEN):return {'id':'api-token','name':'API operator'}
        cookie=http.cookies.SimpleCookie()
        try:cookie.load(self.headers.get('Cookie',''))
        except http.cookies.CookieError:raise PermissionError('Bad cookie')
        sid=cookie['portrait'].value if 'portrait' in cookie else ''
        with LOCK:s=SESSIONS.get(sid)
        if not s or s['expires']<time.time():raise PermissionError('SESSION_REQUIRED')
        if write and not hmac.compare_digest(self.headers.get('X-CSRF-Token',''),s['csrf']):raise PermissionError('CSRF token required')
        return s
    def body_json(self):
        if self.headers.get('Content-Type','').split(';')[0]!='application/json':raise ValueError('Content-Type application/json required')
        if self.headers.get('Transfer-Encoding'):raise ValueError('Chunked request not supported')
        size=int(self.headers.get('Content-Length','0'))
        if not 0<size<=MAX_BODY:raise ValueError('Request must be 1..32768 bytes')
        data=json.loads(self.rfile.read(size),parse_constant=lambda _:(_ for _ in ()).throw(ValueError('Nonfinite number')))
        if not isinstance(data,dict):raise ValueError('JSON object required')
        return data
    def endpoint(self):
        p=unquote(urlsplit(self.path).path)
        if '..' in p.split('/') or '\\' in p or '\x00' in p:raise ValueError('Invalid path')
        return p
    def do_GET(self):
        try:
            self.headers_ok();p=self.endpoint()
            if p in STATIC:
                path=ROOT/'workbench'/STATIC[p]
                kind=ROOT_MIME[path.suffix.lower()]
                return self.send(200,path.read_bytes(),kind)
            if p in ('/','/index.html'):
                return self.send(200,studio_home(),'text/html; charset=utf-8')
            original=portrait_static(p)
            if original:
                file,kind=original
                return self.send(200,file.read_bytes(),kind)
            if p=='/api/v1/health':return self.send(200,{'apiVersion':'1','requiresLogin':True,'remote':self.server.remote,'accessTokenRequired':bool(TOKEN),'artStatus':'ART_UNVERIFIED','modelReady':(CACHE/'source-verification.json').exists(),'blenderAvailable':bool(os.getenv('PORTRAIT_BLENDER') or shutil.which('blender'))})
            if p=='/api/v1/openapi':return self.send(200,openapi_schema())
            s=self.session()
            if p=='/api/v1/catalog':return self.send(200,{'identities':CONFIG['identities'],'lights':CONFIG['lights'],'sourceDigest':source_digest(),'thresholds':CONFIG['thresholds'],'stages':list(STAGES),'surface':surface_catalog(),'session':{'name':s['name']}})
            if p=='/api/v1/stages':return self.send(200,json_file(ROOT/'research/sketch/stages.json'))
            if p=='/api/v1/stage-results':
                return self.send(200,{'stages':[stage_result('S'+str(i),False) for i in range(7)]})
            if p.startswith('/api/v1/stage-results/'):
                parts=p.split('/')
                if len(parts)==5:
                    result=stage_result(parts[4])
                    with db() as c:rows=c.execute('SELECT payload FROM stage_reviews WHERE stage=? ORDER BY created DESC',(parts[4],)).fetchall()
                    result['reviews']=[json.loads(x['payload']) for x in rows]
                    return self.send(200,result)
                if len(parts)==8 and parts[5]=='images':
                    return self.send(200,image_data(parts[4],parts[6],parts[7]),'image/png')
                raise FileNotFoundError('Stage resource not found')
            if p=='/api/v1/jobs':
                with db() as c:rows=c.execute('SELECT * FROM jobs ORDER BY created DESC LIMIT 30').fetchall()
                return self.send(200,{'jobs':[dict(x) for x in rows]})
            if p.startswith('/api/v1/jobs/'):
                ident=p.rsplit('/',1)[1]
                if not ID.fullmatch(ident):raise ValueError('Invalid job id')
                with db() as c:r=c.execute('SELECT * FROM jobs WHERE id=?',(ident,)).fetchone()
                if not r:raise FileNotFoundError('Job not found')
                d=dict(r);d['result']=json.loads(d['result']) if d['result'] else None
                return self.send(200,d)
            if p=='/api/v1/renders':
                items=[]
                for file in sorted((CACHE/'renders').glob('*.json'),key=lambda x:x.stat().st_mtime,reverse=True)[:60]:
                    d=json_file(file);items.append({'id':file.stem,'weights':d['geometry']['weights'],'sourceDigest':d['sourceDigest'],'contentHash':d['contentHash'],'stage':d.get('stage','S2')})
                return self.send(200,{'renders':items})
            if p.startswith('/api/v1/renders/'):
                parts=p.split('/');ident=parts[4];d=read_render(ident)
                if len(parts)==5:return self.send(200,d)
                if len(parts)==6 and parts[5]=='validation':return self.send(200,validation(ident,d))
                if len(parts)==6 and parts[5]=='reference.png':
                    path=CACHE/'reference'/(ident+'.png')
                    if not path.exists():raise FileNotFoundError('Run machine verification to create the reference')
                    return self.send(200,path.read_bytes(),'image/png')
                if len(parts)==6 and parts[5]=='download.html':
                    if d.get('stage','S2')=='S2':
                        from validate import html
                        document=html(d)
                    elif d['stage'] in ('S5','S6'):
                        from surface_document import document as build_document
                        document=build_document(d)
                    else:
                        from validate_studies import document as build_document
                        document=build_document(d)
                    return self.send(200,document,'text/html; charset=utf-8',{'Content-Disposition':'attachment; filename="portrait-css-'+ident+'.html"'})
            if p=='/api/v1/export':
                with db() as c:reviews=[dict(x) for x in c.execute('SELECT * FROM reviews ORDER BY created')]
                return self.send(200,{'schemaVersion':1,'kind':'OWNER_REVIEW_EXPORT_NOT_INDEPENDENT_BLIND_STUDY','artStatus':'ART_UNVERIFIED','reviews':reviews},extra={'Content-Disposition':'attachment; filename="portrait-reviews.json"'})
            raise FileNotFoundError('Endpoint not found')
        except PermissionError as e:self.send(403,{'error':str(e)})
        except (ValueError,json.JSONDecodeError) as e:self.send(400,{'error':str(e)})
        except FileNotFoundError as e:self.send(404,{'error':str(e)})
        except Exception as e:self.send(500,{'error':'INTERNAL_ERROR','detail':type(e).__name__})
    def do_POST(self):
        try:
            self.headers_ok();p=self.endpoint();data=self.body_json()
            if p=='/api/v1/session':
                if TOKEN and not hmac.compare_digest(str(data.get('token','')),TOKEN):raise PermissionError('Incorrect access token')
                name=data.get('name','Reviewer')
                if not isinstance(name,str) or not 1<=len(name)<=40:raise ValueError('Name: 1..40 characters')
                sid=secrets.token_hex(32);s={'id':secrets.token_hex(16),'name':name,'csrf':secrets.token_hex(32),'expires':time.time()+86400}
                with LOCK:
                    for k in list(SESSIONS):
                        if SESSIONS[k]['expires']<time.time():del SESSIONS[k]
                    if len(SESSIONS)>=200:raise ValueError('Session capacity reached')
                    SESSIONS[sid]=s
                return self.send(200,{'csrf':s['csrf'],'name':name},extra={'Set-Cookie':'portrait='+sid+'; HttpOnly; SameSite=Strict; Path=/' + ('; Secure' if os.getenv('PORTRAIT_PUBLIC_ORIGIN') else '')})
            s=self.session(write=True)
            if p=='/api/v1/jobs':
                if set(data)-{'operation','payload'}:raise ValueError('Unknown job field')
                op=data.get('operation');payload=data.get('payload',{})
                if not isinstance(payload,dict):raise ValueError('Object payload required')
                if op=='render':payload=validate_render_payload(payload)
                elif op=='verify':
                    if set(payload)!={'renderId'}:raise ValueError('renderId required')
                    read_render(payload['renderId'])
                elif op=='prepare':
                    if payload:raise ValueError('Prepare accepts no external URL/path/command')
                else:raise ValueError('Allowed operations: prepare, render, verify')
                ident=secrets.token_hex(12)
                with LOCK:
                    if JOBS.full():return self.send(429,{'error':'Queue full; wait for current jobs'})
                    with db() as c:c.execute('INSERT INTO jobs VALUES(?,?,?,?,?,?,?)',(ident,op,canonical(payload).decode(),'queued',None,None,time.time()))
                    JOBS.put_nowait((ident,op,payload))
                emit('job-created',{'id':ident,'operation':op})
                return self.send(202,{'jobId':ident,'status':'queued'})
            if p=='/api/v1/stage-reviews':
                record=validate_stage_review(data)
                ident=secrets.token_hex(12)
                record.update(id=ident,reviewerSession=s['id'],reviewerLabel=s['name'],
                              reviewType='AUTOMATED_TEST' if os.getenv('PORTRAIT_TEST_MODE')=='1' else 'OWNER_SELF_REPORTED',
                              createdAt=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()))
                with db() as c:c.execute('INSERT INTO stage_reviews VALUES(?,?,?,?,?,?,?)',
                    (ident,s['id'],record['stage'],record['sceneId'],record['revision'],canonical(record).decode(),time.time()))
                emit('stage-review-created',{'id':ident,'stage':record['stage'],'sceneId':record['sceneId']})
                return self.send(201,{'id':ident,'artStatus':'ART_UNVERIFIED'})
            if p=='/api/v1/reviews':
                d=read_render(str(data.get('renderId','')));record=review_payload(data,d);ident=secrets.token_hex(12)
                record.update(id=ident,reviewerSession=s['id'],reviewerLabel=s['name'],createdAt=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()))
                with db() as c:c.execute('INSERT INTO reviews VALUES(?,?,?,?,?,?,?)',(ident,s['id'],data['renderId'],d['sourceDigest'],d['contentHash'],canonical(record).decode(),time.time()))
                emit('human-review-created',{'id':ident,'renderId':data['renderId']})
                return self.send(201,{'id':ident,'artStatus':'ART_UNVERIFIED','reviewType':record['reviewType']})
            raise FileNotFoundError('Endpoint not found')
        except PermissionError as e:self.send(403,{'error':str(e)})
        except (ValueError,json.JSONDecodeError) as e:self.send(400,{'error':str(e)})
        except FileNotFoundError as e:self.send(404,{'error':str(e)})
        except Exception as e:self.send(500,{'error':'INTERNAL_ERROR','detail':type(e).__name__})


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--host',default='127.0.0.1');parser.add_argument('--port',default=4173,type=int);args=parser.parse_args()
    remote=args.host not in ('127.0.0.1','localhost','::1')
    if remote and len(TOKEN)<32:raise SystemExit('Non-loopback binding requires PORTRAIT_TOKEN with at least 32 characters. Use a TLS proxy for sharing.')
    initialize();threading.Thread(target=worker,daemon=True).start()
    server=ThreadingHTTPServer((args.host,args.port),Handler);server.remote=remote
    names={'127.0.0.1:'+str(args.port),'localhost:'+str(args.port),args.host+':'+str(args.port)}
    public=os.getenv('PORTRAIT_PUBLIC_ORIGIN')
    server.allowed_origins={'http://'+x for x in names};server.allowed_hosts=names
    if public:
        u=urlsplit(public)
        if u.scheme!='https' or not u.netloc or u.path not in ('','/'):raise SystemExit('Public origin must be an https origin')
        server.allowed_hosts.add(u.netloc);server.allowed_origins.add(public.rstrip('/'))
    print('PORTRAIT_STUDIO http://'+args.host+':'+str(args.port)+'/ (research: /workbench/)',flush=True)
    try:server.serve_forever()
    finally:server.server_close()
if __name__=='__main__':main()
);MAX_BODY=32768
DIMS=['structure','volume','eyes','identity','realism']
STAGES=('S2','S3','S4','S5','S6')
TOKEN=os.getenv('PORTRAIT_TOKEN','');MODEL=None;JOBS=queue.Queue(maxsize=8);SESSIONS={};LOCK=threading.RLock()


def descriptor_digest(d):
    stage=d.get('stage','S2')
    if stage=='S2':return source_digest()
    from study_service import current_digest
    return current_digest(stage)


@contextlib.contextmanager
def db():
    CACHE.mkdir(parents=True,exist_ok=True)
    c=sqlite3.connect(CACHE/'state.sqlite3',timeout=15);c.row_factory=sqlite3.Row
    try:
        with c:yield c
    finally:c.close()


def initialize():
    with db() as c:
        c.executescript('''PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY,operation TEXT,payload TEXT,status TEXT,result TEXT,error TEXT,created REAL);
        CREATE TABLE IF NOT EXISTS reviews(id TEXT PRIMARY KEY,reviewer TEXT,render_id TEXT,source_digest TEXT,content_hash TEXT,payload TEXT,created REAL);
         CREATE TABLE IF NOT EXISTS stage_reviews(id TEXT PRIMARY KEY,reviewer TEXT,stage TEXT,scene_id TEXT,revision TEXT,payload TEXT,created REAL);
        CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,kind TEXT,payload,created REAL);
        ''')
        c.execute("UPDATE jobs SET status='failed',error='Server restarted; retry explicitly' WHERE status IN ('queued','running')")


def emit(kind,data):
    with db() as c:c.execute('INSERT INTO events(kind,payload,created) VALUES(?,?,?)',(kind,canonical(data).decode(),time.time()))


def json_file(path):return json.loads(path.read_text(encoding='utf8'))
def read_render(ident):
    if not isinstance(ident,str) or not ID.fullmatch(ident):raise ValueError('Invalid render identifier')
    path=CACHE/'renders'/(ident+'.json')
    if not path.exists():raise FileNotFoundError('Render not found')
    return json_file(path)


def operation(op,payload):
    global MODEL
    if op=='prepare':
        files=prepare(lambda msg:print(msg,flush=True));MODEL=HeadModel()
        return {'files':len(files),'sourceDigest':source_digest(),'ready':True}
    if op=='render':
        if MODEL is None:MODEL=HeadModel()
        if payload.get('stage','S2')!='S2':
            from study_service import render
            return render(payload,MODEL)
        from geometry import Projection
        weights=payload['weights'];light=payload['light'];key=sha(canonical({'weights':weights,'light':light,'source':source_digest()}))[:24]
        descriptor=Projection(MODEL,weights).describe(light);descriptor['id']=key
        save_json(CACHE/'renders'/(key+'.json'),descriptor)
        save_json(CACHE/'specs'/(key+'.json'),{'id':key,'weights':weights,'light':light})
        return {'renderId':key,'contentHash':descriptor['contentHash'],'sourceDigest':descriptor['sourceDigest']}
    if op=='verify':
        ident=payload['renderId'];d=read_render(ident)
        if d['sourceDigest']!=descriptor_digest(d):raise ValueError('STALE_RENDER: regenerate using current source')
        if d.get('stage','S2')!='S2':
            from study_service import verify
            return verify(ident,d)
        blender=os.getenv('PORTRAIT_BLENDER') or shutil.which('blender')
        if not blender:raise RuntimeError('DEPENDENCY_MISSING: independent machine verification requires Blender')
        spec=CACHE/'specs'/(ident+'.json')
        if not spec.exists():save_json(spec,{'id':ident,'weights':d['geometry']['weights'],'light':d['light']})
        log=CACHE/'logs'/(ident+'.log');log.parent.mkdir(parents=True,exist_ok=True)
        with log.open('w') as f:
            for command in [[blender,'--background','--python-exit-code','1','--python',str(ROOT/'workbench/reference.py'),'--',str(spec)],
                            [sys.executable,str(ROOT/'workbench/validate.py'),ident]]:
                subprocess.run(command,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,timeout=240,check=True,env=os.environ.copy())
        return json_file(CACHE/'machine'/(ident+'.json'))
    raise ValueError('Unknown operation')


def worker():
    while True:
        job_id,op,payload=JOBS.get()
        with db() as c:c.execute("UPDATE jobs SET status='running' WHERE id=?",(job_id,))
        try:
            result=operation(op,payload)
            with db() as c:c.execute("UPDATE jobs SET status='succeeded',result=? WHERE id=?",(canonical(result).decode(),job_id))
        except Exception as exc:
            error=(type(exc).__name__+': '+str(exc))[:800]
            with db() as c:c.execute("UPDATE jobs SET status='failed',error=? WHERE id=?",(error,job_id))
        finally:emit('job-ended',{'id':job_id});JOBS.task_done()


def validate_render_payload(data):
    if data.get('stage') in ('S5','S6'):return validate_surface_payload(data)
    if set(data)-{'identity','weights','light','stage'}:raise ValueError('Unknown render field')
    stage=data.get('stage','S2')
    if stage not in ('S2','S3','S4'):raise ValueError('Choose an explicitly registered study: S2-S6')
    identities={i['id']:i for i in CONFIG['identities']};lights={l['id']:l['direction'] for l in CONFIG['lights']}
    if 'weights' in data:weights=data['weights']
    else:
        if data.get('identity') not in identities:raise ValueError('Choose an identity')
        weights=identities[data['identity']]['weights']
    if not isinstance(weights,list) or len(weights)!=6 or any(type(x) not in (int,float) or not -1.5<=x<=1.5 for x in weights):raise ValueError('Six finite weights between -1.5 and 1.5 required')
    if data.get('light','left') not in lights:raise ValueError('Unknown light')
    return {'weights':weights,'light':lights[data.get('light','left')],'stage':stage}


def review_payload(data,d):
    allowed={'renderId','sourceDigest','contentHash','verdict','scores','note','annotations','humanConfirmed','viewMode'}
    if set(data)-allowed:raise ValueError('Unknown review field; machine status cannot be supplied')
    if data.get('sourceDigest')!=descriptor_digest(d) or data.get('sourceDigest')!=d['sourceDigest'] or data.get('contentHash')!=d['contentHash']:raise ValueError('STALE_REVIEW: sample/source changed')
    if data.get('verdict') not in ('accept','revise','reject'):raise ValueError('Choose accept, revise or reject')
    if data.get('humanConfirmed') is not True:raise ValueError('Human confirmation required')
    scores=data.get('scores',{})
    if not isinstance(scores,dict) or set(scores)!=set(DIMS) or any(type(v) is not int or not 1<=v<=5 for v in scores.values()):raise ValueError('All five scores must be integers 1..5')
    views={'tone','structure'}
    if d.get('stage') in ('S3','S4','S5','S6'):views.add('masses')
    if d.get('stage') in ('S4','S5','S6'):views.add('edges-control')
    if d.get('stage') in ('S5','S6'):views.update(('material-control','hair-control'))
    if data.get('viewMode','tone') not in views:raise ValueError('Unknown review view')
    if not isinstance(data.get('note',''),str) or len(data.get('note',''))>2000:raise ValueError('Note too long')
    annotations=data.get('annotations',[])
    if not isinstance(annotations,list) or len(annotations)>30:raise ValueError('At most 30 annotations')
    for a in annotations:
        if not isinstance(a,dict) or set(a)!={'x','y','note'} or any(type(a[k]) not in (int,float) or not 0<=a[k]<=1 for k in ('x','y')) or not isinstance(a['note'],str) or len(a['note'])>300:raise ValueError('Invalid annotation')
    return {**data,'stage':d.get('stage','S2'),'viewMode':data.get('viewMode','tone'),
            'reviewType':'AUTOMATED_TEST' if os.getenv('PORTRAIT_TEST_MODE')=='1' else 'OWNER_SELF_REPORTED',
            'blinded':False,'observerIndependence':'NOT_VERIFIED','artStatus':'ART_UNVERIFIED'}


def validation(ident,d):
    digest=descriptor_digest(d)
    path=CACHE/'machine'/(ident+'.json');machine=json_file(path) if path.exists() else {'status':'NOT_RUN'}
    if machine.get('contentHash')!=d['contentHash'] or machine.get('sourceDigest')!=digest:machine={'status':'STALE' if path.exists() else 'NOT_RUN'}
    with db() as c:reviews=[json.loads(x['payload']) for x in c.execute('SELECT payload FROM reviews WHERE render_id=? AND source_digest=? AND content_hash=? ORDER BY created',(ident,digest,d['contentHash']))]
    latest={(r['reviewerSession'],r.get('viewMode','tone')):r for r in reviews}
    candidate_reviews=[r for r in latest.values() if not r.get('viewMode','tone').endswith('-control')]
    verdicts={r['verdict'] for r in candidate_reviews}
    tone_accepts=any(r['verdict']=='accept' and r.get('viewMode','tone')=='tone' for r in candidate_reviews)
    human='PENDING' if not verdicts else ('REJECT' if 'reject' in verdicts else ('REVISE' if 'revise' in verdicts else ('ACCEPT' if tone_accepts else 'PENDING')))
    decision='PENDING' if machine['status']!='PASS' or human=='PENDING' else ('OWNER_ACCEPTED' if human=='ACCEPT' else 'REVISION_REQUIRED')
    return {'machine':machine,'human':{'status':human,'reviews':reviews,'selfReportedSessions':len({k[0] for k in latest}),
            'independentHumansVerified':False},'decision':decision,'artStatus':'ART_UNVERIFIED','independentObservers':'NOT_VERIFIED',
            'stage':d.get('stage','S2'),'humanReview':json_file(ROOT/'research/sketch/stages.json').get('humanReview',{})}


def openapi_schema():
    """Extend the compatible v1 schema with stage-specific bounded inputs."""
    schema=json_file(ROOT/'workbench/openapi.json');schemas=schema['components']['schemas'];old=schemas['RenderPayload']
    surface=surface_catalog();new=copy.deepcopy(old);new['properties']['stage']={'enum':['S5','S6']}
    new['properties'].update(expression={'enum':surface['expressions'],'default':'neutral'},
                             material={'enum':surface['materials'],'default':'graphite'},hair={'enum':surface['hairstyles'],'default':'swept'})
    s5_condition={
        'if':{'properties':{'stage':{'const':'S5'}}},
        'then':{'properties':{'expression':{'const':'neutral'}},'not':{'required':['identity','weights']}}
    }
    s6_condition={
        'if':{'properties':{'stage':{'const':'S6'}}},
        'then':{
            'required':['identity'],
            'not':{'required':['weights']},
            'properties':{'identity':{'enum':[i['id'] for i in surface['identities']]}}
        }
    }
    new['required']=['stage'];new['allOf']=[s5_condition,s6_condition]
    schemas['RenderPayload']={'oneOf':[old,new]}
    schemas['Review']['properties']['viewMode']['enum']+=['material-control','hair-control']
    schemas['Review']['properties']['viewMode']['description']='Stage-bound views. masses: S3-S6; edges-control: S4-S6; material-control/hair-control: S5-S6. No control view can accept the candidate.'
    schema['info'].update(version='1.2.0',description='S2-S6 opt-in numerical/CSS research. Human review deferred by owner; no automated ART_PASS or default promotion. S6 tests new PCA modes, not real-person recognition.')
    schema['paths']['/api/v1/catalog']['get']['summary']='S2-S6 catalog, new-mode identities, expressions, materials and hair choices'
    return schema


class Handler(BaseHTTPRequestHandler):
    server_version='PortraitWorkbench/1'
    def log_message(self,*args):pass
    def setup(self):super().setup();self.connection.settimeout(15)
    def headers_ok(self):
        host=self.headers.get('Host','')
        if host not in self.server.allowed_hosts:raise PermissionError('Host not allowed')
        origin=self.headers.get('Origin')
        if origin and origin not in self.server.allowed_origins:raise PermissionError('Cross-origin access denied')
    def send(self,status,data,kind='application/json; charset=utf-8',extra=None):
        body=canonical(data) if kind.startswith('application/json') else (data.encode() if isinstance(data,str) else data)
        self.send_response(status);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(body)))
        self.send_header('X-Content-Type-Options','nosniff');self.send_header('Referrer-Policy','no-referrer');self.send_header('Cache-Control','no-store')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
        if extra:
            for k,v in extra.items():self.send_header(k,v)
        self.end_headers();self.wfile.write(body)
    def session(self,write=False):
        auth=self.headers.get('Authorization','')
        if TOKEN and auth.startswith('Bearer ') and hmac.compare_digest(auth[7:],TOKEN):return {'id':'api-token','name':'API operator'}
        cookie=http.cookies.SimpleCookie()
        try:cookie.load(self.headers.get('Cookie',''))
        except http.cookies.CookieError:raise PermissionError('Bad cookie')
        sid=cookie['portrait'].value if 'portrait' in cookie else ''
        with LOCK:s=SESSIONS.get(sid)
        if not s or s['expires']<time.time():raise PermissionError('SESSION_REQUIRED')
        if write and not hmac.compare_digest(self.headers.get('X-CSRF-Token',''),s['csrf']):raise PermissionError('CSRF token required')
        return s
    def body_json(self):
        if self.headers.get('Content-Type','').split(';')[0]!='application/json':raise ValueError('Content-Type application/json required')
        if self.headers.get('Transfer-Encoding'):raise ValueError('Chunked request not supported')
        size=int(self.headers.get('Content-Length','0'))
        if not 0<size<=MAX_BODY:raise ValueError('Request must be 1..32768 bytes')
        data=json.loads(self.rfile.read(size),parse_constant=lambda _:(_ for _ in ()).throw(ValueError('Nonfinite number')))
        if not isinstance(data,dict):raise ValueError('JSON object required')
        return data
    def endpoint(self):
        p=unquote(urlsplit(self.path).path)
        if '..' in p.split('/') or '\\' in p or '\x00' in p:raise ValueError('Invalid path')
        return p
    def do_GET(self):
        try:
            self.headers_ok();p=self.endpoint()
            if p in STATIC:
                path=ROOT/'workbench'/STATIC[p]
                kind=ROOT_MIME[path.suffix.lower()]
                return self.send(200,path.read_bytes(),kind)
            original=portrait_static('/index.html' if p=='/' else p)
            if original:
                file,kind=original
                return self.send(200,file.read_bytes(),kind)
            if p=='/api/v1/health':return self.send(200,{'apiVersion':'1','requiresLogin':True,'remote':self.server.remote,'accessTokenRequired':bool(TOKEN),'artStatus':'ART_UNVERIFIED','modelReady':(CACHE/'source-verification.json').exists(),'blenderAvailable':bool(os.getenv('PORTRAIT_BLENDER') or shutil.which('blender'))})
            if p=='/api/v1/openapi':return self.send(200,openapi_schema())
            s=self.session()
            if p=='/api/v1/catalog':return self.send(200,{'identities':CONFIG['identities'],'lights':CONFIG['lights'],'sourceDigest':source_digest(),'thresholds':CONFIG['thresholds'],'stages':list(STAGES),'surface':surface_catalog(),'session':{'name':s['name']}})
            if p=='/api/v1/stages':return self.send(200,json_file(ROOT/'research/sketch/stages.json'))
            if p=='/api/v1/stage-results':
                return self.send(200,{'stages':[stage_result('S'+str(i),False) for i in range(7)]})
            if p.startswith('/api/v1/stage-results/'):
                parts=p.split('/')
                if len(parts)==5:
                    result=stage_result(parts[4])
                    with db() as c:rows=c.execute('SELECT payload FROM stage_reviews WHERE stage=? ORDER BY created DESC',(parts[4],)).fetchall()
                    result['reviews']=[json.loads(x['payload']) for x in rows]
                    return self.send(200,result)
                if len(parts)==8 and parts[5]=='images':
                    return self.send(200,image_data(parts[4],parts[6],parts[7]),'image/png')
                raise FileNotFoundError('Stage resource not found')
            if p=='/api/v1/jobs':
                with db() as c:rows=c.execute('SELECT * FROM jobs ORDER BY created DESC LIMIT 30').fetchall()
                return self.send(200,{'jobs':[dict(x) for x in rows]})
            if p.startswith('/api/v1/jobs/'):
                ident=p.rsplit('/',1)[1]
                if not ID.fullmatch(ident):raise ValueError('Invalid job id')
                with db() as c:r=c.execute('SELECT * FROM jobs WHERE id=?',(ident,)).fetchone()
                if not r:raise FileNotFoundError('Job not found')
                d=dict(r);d['result']=json.loads(d['result']) if d['result'] else None
                return self.send(200,d)
            if p=='/api/v1/renders':
                items=[]
                for file in sorted((CACHE/'renders').glob('*.json'),key=lambda x:x.stat().st_mtime,reverse=True)[:60]:
                    d=json_file(file);items.append({'id':file.stem,'weights':d['geometry']['weights'],'sourceDigest':d['sourceDigest'],'contentHash':d['contentHash'],'stage':d.get('stage','S2')})
                return self.send(200,{'renders':items})
            if p.startswith('/api/v1/renders/'):
                parts=p.split('/');ident=parts[4];d=read_render(ident)
                if len(parts)==5:return self.send(200,d)
                if len(parts)==6 and parts[5]=='validation':return self.send(200,validation(ident,d))
                if len(parts)==6 and parts[5]=='reference.png':
                    path=CACHE/'reference'/(ident+'.png')
                    if not path.exists():raise FileNotFoundError('Run machine verification to create the reference')
                    return self.send(200,path.read_bytes(),'image/png')
                if len(parts)==6 and parts[5]=='download.html':
                    if d.get('stage','S2')=='S2':
                        from validate import html
                        document=html(d)
                    elif d['stage'] in ('S5','S6'):
                        from surface_document import document as build_document
                        document=build_document(d)
                    else:
                        from validate_studies import document as build_document
                        document=build_document(d)
                    return self.send(200,document,'text/html; charset=utf-8',{'Content-Disposition':'attachment; filename="portrait-css-'+ident+'.html"'})
            if p=='/api/v1/export':
                with db() as c:reviews=[dict(x) for x in c.execute('SELECT * FROM reviews ORDER BY created')]
                return self.send(200,{'schemaVersion':1,'kind':'OWNER_REVIEW_EXPORT_NOT_INDEPENDENT_BLIND_STUDY','artStatus':'ART_UNVERIFIED','reviews':reviews},extra={'Content-Disposition':'attachment; filename="portrait-reviews.json"'})
            raise FileNotFoundError('Endpoint not found')
        except PermissionError as e:self.send(403,{'error':str(e)})
        except (ValueError,json.JSONDecodeError) as e:self.send(400,{'error':str(e)})
        except FileNotFoundError as e:self.send(404,{'error':str(e)})
        except Exception as e:self.send(500,{'error':'INTERNAL_ERROR','detail':type(e).__name__})
    def do_POST(self):
        try:
            self.headers_ok();p=self.endpoint();data=self.body_json()
            if p=='/api/v1/session':
                if TOKEN and not hmac.compare_digest(str(data.get('token','')),TOKEN):raise PermissionError('Incorrect access token')
                name=data.get('name','Reviewer')
                if not isinstance(name,str) or not 1<=len(name)<=40:raise ValueError('Name: 1..40 characters')
                sid=secrets.token_hex(32);s={'id':secrets.token_hex(16),'name':name,'csrf':secrets.token_hex(32),'expires':time.time()+86400}
                with LOCK:
                    for k in list(SESSIONS):
                        if SESSIONS[k]['expires']<time.time():del SESSIONS[k]
                    if len(SESSIONS)>=200:raise ValueError('Session capacity reached')
                    SESSIONS[sid]=s
                return self.send(200,{'csrf':s['csrf'],'name':name},extra={'Set-Cookie':'portrait='+sid+'; HttpOnly; SameSite=Strict; Path=/' + ('; Secure' if os.getenv('PORTRAIT_PUBLIC_ORIGIN') else '')})
            s=self.session(write=True)
            if p=='/api/v1/jobs':
                if set(data)-{'operation','payload'}:raise ValueError('Unknown job field')
                op=data.get('operation');payload=data.get('payload',{})
                if not isinstance(payload,dict):raise ValueError('Object payload required')
                if op=='render':payload=validate_render_payload(payload)
                elif op=='verify':
                    if set(payload)!={'renderId'}:raise ValueError('renderId required')
                    read_render(payload['renderId'])
                elif op=='prepare':
                    if payload:raise ValueError('Prepare accepts no external URL/path/command')
                else:raise ValueError('Allowed operations: prepare, render, verify')
                ident=secrets.token_hex(12)
                with LOCK:
                    if JOBS.full():return self.send(429,{'error':'Queue full; wait for current jobs'})
                    with db() as c:c.execute('INSERT INTO jobs VALUES(?,?,?,?,?,?,?)',(ident,op,canonical(payload).decode(),'queued',None,None,time.time()))
                    JOBS.put_nowait((ident,op,payload))
                emit('job-created',{'id':ident,'operation':op})
                return self.send(202,{'jobId':ident,'status':'queued'})
            if p=='/api/v1/stage-reviews':
                record=validate_stage_review(data)
                ident=secrets.token_hex(12)
                record.update(id=ident,reviewerSession=s['id'],reviewerLabel=s['name'],
                              reviewType='AUTOMATED_TEST' if os.getenv('PORTRAIT_TEST_MODE')=='1' else 'OWNER_SELF_REPORTED',
                              createdAt=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()))
                with db() as c:c.execute('INSERT INTO stage_reviews VALUES(?,?,?,?,?,?,?)',
                    (ident,s['id'],record['stage'],record['sceneId'],record['revision'],canonical(record).decode(),time.time()))
                emit('stage-review-created',{'id':ident,'stage':record['stage'],'sceneId':record['sceneId']})
                return self.send(201,{'id':ident,'artStatus':'ART_UNVERIFIED'})
            if p=='/api/v1/reviews':
                d=read_render(str(data.get('renderId','')));record=review_payload(data,d);ident=secrets.token_hex(12)
                record.update(id=ident,reviewerSession=s['id'],reviewerLabel=s['name'],createdAt=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()))
                with db() as c:c.execute('INSERT INTO reviews VALUES(?,?,?,?,?,?,?)',(ident,s['id'],data['renderId'],d['sourceDigest'],d['contentHash'],canonical(record).decode(),time.time()))
                emit('human-review-created',{'id':ident,'renderId':data['renderId']})
                return self.send(201,{'id':ident,'artStatus':'ART_UNVERIFIED','reviewType':record['reviewType']})
            raise FileNotFoundError('Endpoint not found')
        except PermissionError as e:self.send(403,{'error':str(e)})
        except (ValueError,json.JSONDecodeError) as e:self.send(400,{'error':str(e)})
        except FileNotFoundError as e:self.send(404,{'error':str(e)})
        except Exception as e:self.send(500,{'error':'INTERNAL_ERROR','detail':type(e).__name__})


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--host',default='127.0.0.1');parser.add_argument('--port',default=4173,type=int);args=parser.parse_args()
    remote=args.host not in ('127.0.0.1','localhost','::1')
    if remote and len(TOKEN)<32:raise SystemExit('Non-loopback binding requires PORTRAIT_TOKEN with at least 32 characters. Use a TLS proxy for sharing.')
    initialize();threading.Thread(target=worker,daemon=True).start()
    server=ThreadingHTTPServer((args.host,args.port),Handler);server.remote=remote
    names={'127.0.0.1:'+str(args.port),'localhost:'+str(args.port),args.host+':'+str(args.port)}
    public=os.getenv('PORTRAIT_PUBLIC_ORIGIN')
    server.allowed_origins={'http://'+x for x in names};server.allowed_hosts=names
    if public:
        u=urlsplit(public)
        if u.scheme!='https' or not u.netloc or u.path not in ('','/'):raise SystemExit('Public origin must be an https origin')
        server.allowed_hosts.add(u.netloc);server.allowed_origins.add(public.rstrip('/'))
    print('PORTRAIT_STUDIO http://'+args.host+':'+str(args.port)+'/ (research: /workbench/)',flush=True)
    try:server.serve_forever()
    finally:server.server_close()
if __name__=='__main__':main()
