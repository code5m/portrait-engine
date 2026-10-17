"""Unified studio HTTP contracts: one origin, no static evidence leaks.
This file is intentionally outside the frozen S2 source-files.json digest.
"""
from __future__ import annotations
import http.client,json,sys,tempfile,threading,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import server

class UnifiedStudioRoutes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        cls.previous=server.CACHE
        server.CACHE=Path(cls.tmp.name)
        server.initialize()
        cls.http=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
        cls.http.remote=False
        cls.host='127.0.0.1:'+str(cls.http.server_port)
        cls.http.allowed_hosts={cls.host}
        cls.http.allowed_origins={'http://'+cls.host}
        cls.worker=threading.Thread(target=cls.http.serve_forever,daemon=True)
        cls.worker.start()

    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown()
        cls.worker.join(timeout=5)
        cls.http.server_close()
        server.CACHE=cls.previous
        cls.tmp.cleanup()

    def request(self,path,host=None):
        conn=http.client.HTTPConnection('127.0.0.1',self.http.server_port,timeout=10)
        conn.request('GET',path,headers={'Host':host or self.host})
        result=conn.getresponse()
        data=result.read()
        code=result.status
        headers=dict(result.getheaders())
        conn.close()
        return code,data,headers

    def test_default_portrait_and_lab_share_an_origin(self):
        st,home,headers=self.request('/')
        self.assertEqual(st,200)
        self.assertIn(b'href="/workbench/"',home)
        self.assertIn(b'./src/app.mjs',home)
        self.assertIn(b'<style>',home)
        self.assertIn("default-src 'self'",headers['Content-Security-Policy'])
        for path,snippet in (
            ('/index.html',b'href="/workbench/"'),
            ('/src/app.mjs',b'portrait'),
            ('/styles/layout.css',b'.topbar'),
            ('/workbench/',b'id="stage-grid"'),
            ('/workbench/app.mjs',b'pipeline_renderer.mjs'),
            ('/workbench/style.css',b'.shell'),
            ('/workbench/api-guide',b'/api/v1/jobs'),
            ('/standalone.html',b'html'),
        ):
            with self.subTest(path=path):
                code,body,_=self.request(path)
                self.assertEqual(code,200)
                self.assertIn(snippet,body)

    def test_private_evidence_and_source_are_not_static(self):
        for path in (
            '/api/v1/stage-results',
            '/research/sketch/evidence/S6.json',
            '/data/workbench/state.sqlite3',
            '/.git/config',
            '/workbench/server.py',
        ):
            with self.subTest(path=path):
                status,_,_=self.request(path)
                self.assertIn(status,(403,404))
        self.assertEqual(self.request('/%2e%2e/.git/config')[0],400)
        self.assertEqual(self.request('/api/v1/health',host='evil.invalid')[0],403)

if __name__=='__main__':unittest.main()
