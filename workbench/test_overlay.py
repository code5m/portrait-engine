"""Areal overlay regression tests; synthetic inputs are not artistic evidence."""
import copy,unittest
from types import SimpleNamespace
import numpy as np
from shapely.geometry import Polygon,LineString,Point,GeometryCollection,box
from study_light import area_geometry,area_intersection
from study_edges import describe_edges,visible_intensity,crease_support,crease_parts,classify
from run_study_shard import select_identity
from model import CONFIG
# unittest.main discovers imported TestCase subclasses too: the geometry-only
# ridge controls run in the same preflight job before any expensive head work.
from test_curvature_ridges import CurvatureTests

class AreaOverlayTests(unittest.TestCase):
    def test_mixed_dimension_contacts_keep_holes_and_disconnected_areas(self):
        ring=Polygon([(0,0),(4,0),(4,4),(0,4)],holes=[[(1,1),(1,2),(2,2),(2,1)]])
        island=Polygon([(6,0),(7,0),(7,1),(6,1)])
        mixed=GeometryCollection([ring,island,LineString([(4,4),(5,5)]),Point(9,9)])
        got=area_geometry(mixed,1e-8)
        self.assertTrue(got.is_valid);self.assertAlmostEqual(got.area,16)
        self.assertFalse(got.contains(Point(1.5,1.5)));self.assertTrue(got.contains(Point(6.5,.5)))
        self.assertEqual(len(got.geoms),2)
    def test_contact_without_area_does_not_reach_overlay_as_a_line(self):
        a=Polygon([(0,0),(1,0),(1,1),(0,1)]);b=Polygon([(1,0),(2,0),(2,1),(1,1)])
        self.assertTrue(area_intersection(a,b,1e-8).is_empty)
        self.assertTrue(area_geometry(LineString([(0,0),(1,1)]),1e-8).is_empty)
        self.assertTrue(area_geometry(Point(0,0),1e-8).is_empty)
    def test_fixed_precision_intersection_is_commutative_and_bounded(self):
        a=Polygon([(0,0),(2,0),(2,2),(0,2)]);b=Polygon([(.5,-1),(1.5,-1),(1.5,3),(.5,3)])
        ab=area_intersection(a,b,1e-8);ba=area_intersection(b,a,1e-8)
        self.assertTrue(ab.equals(ba));self.assertAlmostEqual(ab.area,2)
        self.assertLess(ab.difference(a).area,1e-12)
    def test_s4_mixed_boundary_matches_the_same_painted_area(self):
        vertices=np.array([[0.,0.,0.],[2.,0.,0.],[0.,2.,0.]])
        faces=np.array([[0,1,2]]);polygon=Polygon(vertices[:,:2])
        mixed=GeometryCollection([polygon,LineString([(3,3),(4,4)]),Point(8,8)])
        def render(shape):
            p=SimpleNamespace(camera={'center':[1.,1.],'span':4.},grid=1e-8,
                visible=[shape],footprints=[shape],silhouette=shape,tri=vertices[faces],regions=np.array([0]))
            scene={'projection':p,'faceIndices':np.array([0]),'cameraFaces':faces,
                   'cameraVertices':vertices,'shaded':np.array([[.3,.4,.5]]),
                   'unlit':np.array([[.1,.1,.1]]),'lit':[polygon],'dark':[Polygon()]}
            result=describe_edges(scene,{'sourceDigest':'synthetic','limitations':[]})
            self.assertIs(p.visible[0],shape,'S4 must not mutate frozen S2 projection')
            return result
        self.assertEqual(render(mixed),render(polygon))
    def test_shards_select_all_frozen_identities_without_mutation(self):
        before=copy.deepcopy(CONFIG)
        got=[select_identity(CONFIG,x['id']) for x in CONFIG['identities']]
        self.assertEqual(got,CONFIG['identities']);self.assertEqual(CONFIG,before)
        self.assertEqual(len(got),6);self.assertEqual(len(CONFIG['lights']),3)
        self.assertEqual({x['split'] for x in got},{'baseline','holdout'})
        with self.assertRaises(ValueError):select_identity(CONFIG,'not-a-registered-person')
        bad={**CONFIG,'identities':[got[0],got[0]]}
        with self.assertRaises(ValueError):select_identity(bad,got[0]['id'])
    def test_occluded_direct_light_cannot_create_a_crease(self):
        area=box(0,0,1,1)
        scene={'shaded':np.array([[.8,.8,.8],[.2,.2,.2]]),
               'unlit':np.full((2,3),.1),'lit':[Polygon(),Polygon()]}
        values=visible_intensity(scene,[area,area])
        self.assertTrue(np.allclose(values,[.1,.1]))
        self.assertEqual(classify(40,abs(values[0]-values[1])*255),'lost')
        self.assertEqual(classify(40,abs(.8-.2)*255),'hard','Old unshadowed control exposes the defect')
        scene['lit']=[area,area]
        self.assertTrue(np.allclose(visible_intensity(scene,[area,area]),[.8,.2]))
        scene['lit']=[box(0,0,.5,1),area]
        self.assertTrue(np.allclose(visible_intensity(scene,[area,area]),[.45,.2]))
        scene['shaded'][0,0]=np.nan
        with self.assertRaises(ValueError):visible_intensity(scene,[area,area])
    def test_crease_requires_two_visible_sides_not_an_occluded_neighbor(self):
        left=box(0,0,1,1);right=box(1,0,2,1);line=LineString([(1,0),(1,1)])
        self.assertAlmostEqual(crease_support(line,left,right,1e-8).length,1)
        self.assertTrue(crease_support(line,left,Polygon(),1e-8).is_empty)
        part=crease_support(line,left,box(1,.5,2,1),1e-8)
        self.assertAlmostEqual(part.length,.5,places=6)
    def test_shadow_fraction_difference_is_not_local_crease_contrast(self):
        left=box(0,0,1,1);right=box(1,0,2,1);line=LineString([(1,0),(1,1)])
        lit=[left,box(1,.5,2,1)];dark=[Polygon(),box(1,0,2,.5)]
        values=np.full((2,3),.8);fill=np.full((2,3),.1)
        old=visible_intensity({'shaded':values,'unlit':fill,'lit':lit},[left,right])
        self.assertEqual(classify(40,abs(old[0]-old[1])*255),'hard','Area-mean negative control')
        parts=crease_parts(line,40,lit,dark,values,fill,1e-8)
        self.assertTrue(all(g.is_empty for g in parts.values()))
    def test_true_branch_contrast_keeps_hard_soft_and_partial_support(self):
        left=box(0,0,1,1);right=box(1,0,2,1);line=LineString([(1,0),(1,1)])
        values=np.array([[.8]*3,[.2]*3]);fill=np.full((2,3),.1)
        full=crease_parts(line,40,[left,right],[Polygon(),Polygon()],values,fill,1e-8)
        self.assertAlmostEqual(full['hard'].length,1);self.assertTrue(full['soft'].is_empty)
        half=crease_parts(line,40,[left,box(1,.5,2,1)],[Polygon(),box(1,0,2,.5)],values,fill,1e-8)
        self.assertAlmostEqual(half['hard'].length,.5,places=6)
        soft=crease_parts(line,20,[left,right],[Polygon(),Polygon()],[[.5]*3,[.46]*3],fill,1e-8)
        self.assertAlmostEqual(soft['soft'].length,1);self.assertTrue(soft['hard'].is_empty)
    def test_shadow_transition_is_not_double_outlined_and_bad_inputs_fail(self):
        left=box(0,0,1,1);right=box(1,0,2,1);line=LineString([(1,0),(1,1)])
        values=np.array([[.8]*3,[.2]*3]);fill=np.full((2,3),.1)
        parts=crease_parts(line,40,[left,Polygon()],[Polygon(),right],values,fill,1e-8)
        self.assertTrue(all(g.is_empty for g in parts.values()))
        values[0,0]=np.nan
        with self.assertRaises(ValueError):crease_parts(line,40,[left,right],[Polygon(),Polygon()],values,fill,1e-8)
        with self.assertRaises(ValueError):crease_parts(line,40,[left],[],fill,fill,1e-8)
        with self.assertRaises(ValueError):crease_parts(line,40,[left,right],[Polygon(),Polygon()],fill,fill,0)
if __name__=='__main__':unittest.main()
