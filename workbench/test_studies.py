"""Synthetic math/policy tests, never human art observations."""
import json,sys,unittest
from pathlib import Path
import numpy as np
from shapely.geometry import Polygon,Point
sys.path.insert(0,str(Path(__file__).resolve().parent))
from model import ROOT,unit
from geometry import Projection
from study_light import frame,to_camera,compile_light,describe
from study_edges import classify,describe_edges


class TwoPlanes:
    camera={'center':[0,0],'span':6}
    def mesh(self,_):
        v=np.array([[-2,-2,0],[2,-2,0],[2,2,0],[-2,2,0],[-.4,-.4,1],[.4,-.4,1],[.4,.4,1],[-.4,.4,1]],float)
        f=np.array([[0,1,2],[0,2,3],[4,5,6],[4,6,7]],int)
        return v,f,np.tile([0.,0.,1.],(8,1)),np.array([1,1,3,3])
    def signature(self,weights):return {'geometryHash':'0'*64,'weights':weights,'camera':self.camera,'surfaceOnly':True}


def ray_hits(point,direction,vertices,faces):
    for face in faces:
        a,b,c=vertices[face];e1=b-a;e2=c-a;h=np.cross(direction,e2);det=e1@h
        if abs(det)<1e-10:continue
        inv=1/det;s=point-a;u=inv*(s@h)
        if not 0<=u<=1:continue
        q=np.cross(s,e1);v=inv*(direction@q);t=inv*(e2@q)
        if v>=0 and u+v<=1 and t>1e-6:return True
    return False


class StudyTests(unittest.TestCase):
    def test_orthonormal_frame_and_polygon_inverse(self):
        for l in [[0,0,1],[.6,.4,.8],[0,1,.01],[-.6,.4,.8]]:
            r=frame(l);np.testing.assert_allclose(r@r.T,np.eye(3),atol=1e-12);self.assertAlmostEqual(np.linalg.det(r),1)
            p=np.array([[-.2,-.3,1],[.7,-.3,1],[.7,.4,1]])
            q=p@r.T
            if abs(np.linalg.det(np.c_[q[:,:2],np.ones(3)]))<1e-10:continue
            plane=np.linalg.solve(np.c_[q[:,:2],np.ones(3)],q[:,2])
            restored=to_camera(Polygon(q[:,:2]),plane,r)
            self.assertLess(restored.symmetric_difference(Polygon(p[:,:2])).area,1e-10)
        for bad in [[0,0,0],[float('nan'),0,1],[1,2]]:self.assertRaises(ValueError,frame,bad)
    def test_light_plane_visibility_matches_independent_rays(self):
        model=TwoPlanes();p=Projection(model,[0]*6);l=unit([-.6,0,.8]);s=compile_light(model,[0]*6,l,p)
        v,f,_,_=model.mesh(None);rng=np.random.default_rng(20261016)
        for x,y in rng.uniform(-1.95,1.95,(150,2)):
            point=Point(x,y)
            for i,area in enumerate(p.visible):
                if not area.contains(point):continue
                z=p.planes[i]@np.array([x,y,1.])
                observed=s['lit'][i].contains(point)
                expected=not ray_hits(np.array([x,y,z]),l,v,f)
                self.assertEqual(observed,expected,(x,y,z))
        self.assertGreater(sum(g.area for g in s['dark']),.2)
        d=describe(s,levels=3);self.assertEqual(len(d['toneRegions']),3)
        e=describe_edges(s,d);self.assertEqual(e['geometry'],d['geometry']);self.assertEqual(e['toneRegions'],d['toneRegions'])
        self.assertEqual(e['artStatus'],'ART_UNVERIFIED')
    def test_explicit_edge_hierarchy(self):
        self.assertEqual(classify(1,1,True),'hard')
        self.assertEqual(classify(45,20),'hard');self.assertEqual(classify(20,10),'soft')
        self.assertEqual(classify(2,20),'lost');self.assertEqual(classify(40,2),'lost')
        self.assertRaises(ValueError,classify,float('nan'),3)
    def test_no_reference_pixels_or_unbounded_raster_in_compiler(self):
        light=(ROOT/'workbench/study_light.py').read_text();edge=(ROOT/'workbench/study_edges.py').read_text()
        for source in [light,edge]:
            self.assertNotIn('Image.open(',source);self.assertNotIn('np.mgrid',source);self.assertNotIn('read_pixels',source)
        painter=(ROOT/'workbench/study_renderer.mjs').read_text()
        self.assertNotIn('target.style.filter',painter);self.assertNotIn('createElement(\'canvas\')',painter)
        self.assertIn('wrapper.style.filter',painter)
if __name__=='__main__':unittest.main()
