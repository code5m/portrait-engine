"""Synthetic unit/security fixtures only. Never artistic or human evidence."""
import http.client,json,os,sys,tempfile,threading,unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
import server
from geometry import Projection,clip,region_data,precision_geometry
from model import source_digest,save_json
from shapely.geometry import Polygon

class Dummy:
    camera={'center':[0,0],'span':4}
    def mesh(self,_):
        v=np.array([[-1,-1,0],[1,-1,0],[0,1,0],[-.3,-.3,1],[.3,-.3,1],[0,.4,1]])
        f=np.array([[0,1,2],[3,4,5]]);return v,f,np.tile([0,0,1.],(6,1)),np.array([1,3])
    def signature(self,_):return {'geometryHash':'0'*64,'weights':[0]*6,'camera':self.camera}

class GeometryTests(unittest.TestCase):
    def test_hidden_surface_is_not_convex_hull(self):
        p=Projection(Dummy(),[0]*6)
        self.assertAlmostEqual(sum(x.area for x in p.visible),2)
        self.assertEqual(p.visibility['partlyOrFullyOccluded'],1)
        d=p.describe([0,0,1]);self.assertEqual(len(d['toneRegions']),24)
        self.assertLess(d['contourPoints'],1000)
    def test_nearly_coincident_overlay_is_valid_without_filling_holes(self):
        from shapely import union_all
        grid=4/320*1e-5
        pieces=[Polygon([(0,0),(1,0),(1,1e-15),(1,1),(0,1)]),Polygon([(1-1e-14,0),(2,0),(2,1),(1,1)])]
        result=union_all([precision_geometry(p,grid) for p in pieces],grid_size=grid)
        self.assertTrue(result.is_valid);self.assertAlmostEqual(result.area,2)
        donut=Polygon([(0,0),(3,0),(3,3),(0,3)],holes=[[(1,1),(2,1),(2,2),(1,2)]])
        self.assertAlmostEqual(precision_geometry(donut,grid).area,8)
    def test_cut(self):
        points=np.array([[0.,0],[1,0],[0,1]])
        self.assertAlmostEqual(Polygon(clip(points,[0,1,0],.5)).area,.125)
    def test_region_holes_preserved(self):
        p=Polygon([[-1,-1],[1,-1],[1,1],[-1,1]],holes=[[[-.2,-.2],[.2,-.2],[.2,.2],[-.2,.2]]])
        self.assertEqual(len(region_data(p,{'center':[0,0],'span':4},0)),2)

class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.old=server.CACHE;server.CACHE=Path(cls.tmp.name);server.TOKEN='';server.initialize()
        cls.http=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler);cls.http.remote=False;cls.host='127.0.0.1:'+str(cls.http.server_port)
        cls.http.allowed_hosts={cls.host};cls.http.allowed_origins={'http://'+cls.host};threading.Thread(target=cls.http.serve_forever,daemon=True).start()
        descriptor=Projection(Dummy(),[0]*6).describe([0,0,1]);save_json(server.CACHE/'renders/test-render.json',descriptor);cls.d=descriptor
    @classmethod
    def tearDownClass(cls):cls.http.shutdown();cls.http.server_close();server.CACHE=cls.old;cls.tmp.cleanup()
    def request(self,method,path,body=None,headers=None):
        conn=http.client.HTTPConnection('127.0.0.1',self.http.server_port,timeout=10)
        h={'Host':self.host,'Content-Type':'application/json'};h.update(headers or {})
        conn.request(method,path,body=json.dumps(body) if body is not None else None,headers=h);r=conn.getresponse();data=r.read();hs=dict(r.getheaders());conn.close()
        try:data=json.loads(data)
        except ValueError:pass
        return r.status,data,hs
    def login(self):
        st,d,h=self.request('POST','/api/v1/session',{'name':'SYNTHETIC_TEST'})
        self.assertEqual(st,200);return {'Cookie':h['Set-Cookie'].split(';')[0],'X-CSRF-Token':d['csrf']}
    def test_origin_host_and_traversal(self):
        self.assertEqual(self.request('GET','/api/v1/health',headers={'Host':'evil.invalid'})[0],403)
        self.assertEqual(self.request('POST','/api/v1/session',{'name':'x'},headers={'Origin':'https://evil.invalid'})[0],403)
        self.assertEqual(self.request('GET','/../../.git/config')[0],400)
    def test_session_csrf_and_no_command_api(self):
        h=self.login();h0={'Cookie':h['Cookie']}
        self.assertEqual(self.request('POST','/api/v1/jobs',{'operation':'prepare'},headers=h0)[0],403)
        self.assertEqual(self.request('POST','/api/v1/jobs',{'operation':'shell','payload':{'cmd':'pwd'}},headers=h)[0],400)
        self.assertEqual(self.request('POST','/api/v1/jobs',{'operation':'prepare','payload':{'url':'https://x'}},headers=h)[0],400)
    def review(self):return {'renderId':'test-render','sourceDigest':source_digest(),'contentHash':self.d['contentHash'],'scores':dict.fromkeys(server.DIMS,3),'verdict':'revise','annotations':[{'x':.2,'y':.3,'note':'test'}],'note':'Synthetic, not human evaluation','humanConfirmed':True}
    def test_human_review_does_not_create_machine_pass(self):
        h=self.login();st,d,_=self.request('POST','/api/v1/reviews',self.review(),headers=h);self.assertEqual(st,201)
        st,v,_=self.request('GET','/api/v1/renders/test-render/validation',headers=h)
        self.assertEqual(v['machine']['status'],'NOT_RUN');self.assertEqual(v['human']['status'],'REVISE');self.assertEqual(v['artStatus'],'ART_UNVERIFIED')
        with server.db() as c:self.assertTrue(c.execute('SELECT * FROM reviews WHERE id=?',(d['id'],)).fetchone())
    def test_other_reviewers_cannot_hide_an_unresolved_rejection(self):
        a=self.login();b=self.login()
        self.assertEqual(self.request('POST','/api/v1/reviews',{**self.review(),'verdict':'reject'},headers=a)[0],201)
        self.assertEqual(self.request('POST','/api/v1/reviews',{**self.review(),'verdict':'accept'},headers=b)[0],201)
        _,v,_=self.request('GET','/api/v1/renders/test-render/validation',headers=b)
        self.assertEqual(v['human']['status'],'REJECT')
        self.assertFalse(v['human']['independentHumansVerified'])
    def test_stale_incomplete_fake_machine_and_injection(self):
        h=self.login()
        for change in [{'sourceDigest':'0'*64},{'scores':{'realism':5}},{'scores':None},{'viewMode':'pixels'},{'machineStatus':'PASS'},{'annotations':[{'x':-2,'y':.5,'note':'x'}]},{'humanConfirmed':False}]:
            self.assertEqual(self.request('POST','/api/v1/reviews',{**self.review(),**change},headers=h)[0],400)
        self.assertEqual(self.request('GET','/api/v1/renders/%2e%2e/reference.png',headers=h)[0],400)
        self.assertEqual(self.request('POST','/api/v1/jobs',{'operation':'render','payload':{'weights':[100]*6,'light':'left'}},headers=h)[0],400)
        self.assertEqual(self.request('POST','/api/v1/jobs',{'operation':'render','payload':{'weights':[True]*6}},headers=h)[0],400)

if __name__=='__main__':unittest.main()
