"""Local-first API. Allowlisted computation only; separate machine/human records.
Network binding requires explicit access credentials. Trusted research group,
not a public multi-tenant service. All saved human claims remain self-reported.
"""
from __future__ import annotations
import argparse,contextlib,hashlib,hmac,http.cookies,json,os,queue,re,secrets,shutil,sqlite3,subprocess,sys,threading,time
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit,unquote
from model import ROOT,CACHE,CONFIG,HeadModel,prepare,source_digest,canonical,sha,save_json
STATIC={'/':'index.html','/app.mjs':'app.mjs','/style.css':'style.css','/renderer.mjs':'renderer.mjs','/api-guide':'api.html'}
ID=re.compile(r'^[a-z0-9-]{1,80}$');MAX_BODY=32768
DIMS=['structure','volume','eyes','identity','realism']
TOKEN=os.getenv('PORTRAIT_TOKEN','');MODEL=None;JOBS=queue.Queue(maxsize=8);SESSIONS={};LOCK=threading.RLock()

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
        CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,kind TEXT,payload TEXT,created REAL);
        ''')
        c.execute("UPDATE jobs SET status='failed',error='Server restarted; retry explicitly' WHERE status IN ('queued','running')")

def emit(kind,data):
    with db() as c:c.execute('INSERT INTO events(kind,payload,created) VALUES(?,?,?)',(kind,canonical(data).decode(),time.time()))

def json_file(path):return json.loads(path.read_text(encoding='utf8'))
def read_render(ident):
    if not ID.fullmatch(ident):raise ValueError('Invalid render identifier')
    path=CACHE/'renders'/(ident+'.json')
    if not path.exists():raise FileNotFoundError('Render not found')
    return json_file(path)

def operation(op,payload):
    global MODEL
    if op=='prepare':
        files=prepare(lambda msg:print(msg,flush=True));MODEL=HeadModel()
        return {'files':len(files),'sourceDigest':source_digest(),'ready':True}
    if op=='render':
        from geometry import Projection
        if MODEL is None:MODEL=HeadModel()
        weights=payload['weights'];light=payload['light'];key=sha(canonical({'weights':weights,'light':light,'source':source_digest()}))[:24]
        descriptor=Projection(MODEL,weights).describe(light);descriptor['id']=key
        save_json(CACHE/'renders'/(key+'.json'),descriptor)
        save_json(CACHE/'specs'/(key+'.json'),{'id':key,'weights':weights,'light':light})
        return {'renderId':key,'contentHash':descriptor['contentHash'],'sourceDigest':descriptor['sourceDigest']}
    if op=='verify':
        ident=payload['renderId'];d=read_render(ident)
        if d['sourceDigest']!=source_digest():raise ValueError('STALE_RENDER: regenerate using current source')
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
    if set(data)-{'identity','weights','light'}:raise ValueError('Unknown render field')
    identities={i['id']:i for i in CONFIG['identities']};lights={l['id']:l['direction'] for l in CONFIG['lights']}
    if 'weights' in data:weights=data['weights']
    else:
        if data.get('identity') not in identities:raise ValueError('Choose an identity')
        weights=identities[data['identity']]['weights']
    if not isinstance(weights,list) or len(weights)!=6 or any(type(x) not in (int,float) or not -1.5<=x<=1.5 for x in weights):raise ValueError('Six finite weights between -1.5 and 1.5 required')
    if data.get('light','left') not in lights:raise ValueError('Unknown light')
    return {'weights':weights,'light':lights[data.get('light','left')]}

def review_payload(data,d):
    allowed={'renderId','sourceDigest','contentHash','verdict','scores','note','annotations','humanConfirmed','viewMode'}
    if set(data)-allowed:raise ValueError('Unknown review field; machine status cannot be supplied')
    if data.get('sourceDigest')!=source_digest() or data.get('sourceDigest')!=d['sourceDigest'] or data.get('contentHash')!=d['contentHash']:raise ValueError('STALE_REVIEW: sample/source changed')
    if data.get('verdict') not in ('accept','revise','reject'):raise ValueError('Choose accept, revise or reject')
    if data.get('humanConfirmed') is not True:raise ValueError('Human confirmation required')
    scores=data.get('scores',{})
    if not isinstance(scores,dict) or set(scores)!=set(DIMS) or any(type(v) is not int or not 1<=v<=5 for v in scores.values()):raise ValueError('All five scores must be integers 1..5')
    if data.get('viewMode','tone') not in ('tone','structure'):raise ValueError('Unknown review view')
    if not isinstance(data.get('note',''),str) or len(data.get('note',''))>2000:raise ValueError('Note too long')
    annotations=data.get('annotations',[])
    if not isinstance(annotations,list) or len(annotations)>30:raise ValueError('At most 30 annotations')
    for a in annotations:
        if not isinstance(a,dict) or set(a)!={'x','y','note'} or any(type(a[k]) not in (int,float) or not 0<=a[k]<=1 for k in ('x','y')) or not isinstance(a['note'],str) or len(a['note'])>300:raise ValueError('Invalid annotation')
    return {**data,'viewMode':data.get('viewMode','tone'),'reviewType':'AUTOMATED_TEST' if os.getenv('PORTRAIT_TEST_MODE')=='1' else 'OWNER_SELF_REPORTED','blinded':False,'observerIndependence':'NOT_VERIFIED','artStatus':'ART_UNVERIFIED'}

def validation(ident,d):
    path=CACHE/'machine'/(ident+'.json');machine=json_file(path) if path.exists() else {'status':'NOT_RUN'}
    if machine.get('contentHash')!=d['contentHash'] or machine.get('sourceDigest')!=source_digest():machine={'status':'STALE' if path.exists() else 'NOT_RUN'}
    with db() as c:reviews=[json.loads(x['payload']) for x in c.execute('SELECT payload FROM reviews WHERE render_id=? AND source_digest=? AND content_hash=? ORDER BY created',(ident,source_digest(),d['contentHash']))]
    # An acceptance must not erase another reviewer's unresolved rejection.
    latest={r['reviewerSession']:r for r in reviews}
    verdicts={r['verdict'] for r in latest.values()}
    human='PENDING' if not verdicts else ('REJECT' if 'reject' in verdicts else ('REVISE' if 'revise' in verdicts else 'ACCEPT'))
    decision='PENDING' if machine['status']!='PASS' or human=='PENDING' else ('OWNER_ACCEPTED' if human=='ACCEPT' else 'REVISION_REQUIRED')
    return {'machine':machine,'human':{'status':human,'reviews':reviews,'selfReportedSessions':len(latest),'independentHumansVerified':False},'decision':decision,'artStatus':'ART_UNVERIFIED','independentObservers':'NOT_VERIFIED'}

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
                path=ROOT/'workbench'/STATIC[p];kind='text/css; charset=utf-8' if p.endswith('.css') else ('text/javascript; charset=utf-8' if p.endswith('.mjs') else 'text/html; charset=utf-8')
                return self.send(200,path.read_bytes(),kind)
            if p=='/api/v1/health':return self.send(200,{'apiVersion':'1','requiresLogin':True,'remote':self.server.remote,'accessTokenRequired':bool(TOKEN),'artStatus':'ART_UNVERIFIED','modelReady':(CACHE/'source-verification.json').exists(),'blenderAvailable':bool(os.getenv('PORTRAIT_BLENDER') or shutil.which('blender'))})
            if p=='/api/v1/openapi':return self.send(200,json_file(ROOT/'workbench/openapi.json'))
            s=self.session()
            if p=='/api/v1/catalog':return self.send(200,{'identities':CONFIG['identities'],'lights':CONFIG['lights'],'sourceDigest':source_digest(),'thresholds':CONFIG['thresholds'],'session':{'name':s['name']}})
            if p=='/api/v1/stages':return self.send(200,json_file(ROOT/'research/sketch/stages.json'))
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
                    d=json_file(file);items.append({'id':file.stem,'weights':d['geometry']['weights'],'sourceDigest':d['sourceDigest'],'contentHash':d['contentHash']})
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
                    from validate import html
                    return self.send(200,html(d),'text/html; charset=utf-8',{'Content-Disposition':'attachment; filename="portrait-css-'+ident+'.html"'})
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
            if p=='/api/v1/reviews':
                d=read_render(str(data.get('renderId','')));record=review_payload(data,d);ident=secrets.token_hex(12)
                record.update(id=ident,reviewerSession=s['id'],reviewerLabel=s['name'],createdAt=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()))
                with db() as c:c.execute('INSERT INTO reviews VALUES(?,?,?,?,?,?,?)',(ident,s['id'],data['renderId'],source_digest(),d['contentHash'],canonical(record).decode(),time.time()))
                emit('human-review-created',{'id':ident,'renderId':data['renderId']})
                return self.send(201,{'id':ident,'artStatus':'ART_UNVERIFIED','reviewType':record['reviewType']})
            raise FileNotFoundError('Endpoint not found')
        except PermissionError as e:self.send(403,{'error':str(e)})
        except (ValueError,json.JSONDecodeError) as e:self.send(400,{'error':str(e)})
        except FileNotFoundError as e:self.send(404,{'error':str(e)})
        except Exception as e:self.send(500,{'error':'INTERNAL_ERROR','detail':type(e).__name__})

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--host',default='127.0.0.1');parser.add_argument('--port',default=4186,type=int);args=parser.parse_args()
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
    print('PORTRAIT_WORKBENCH http://'+args.host+':'+str(args.port),flush=True)
    try:server.serve_forever()
    finally:server.server_close()
if __name__=='__main__':main()
