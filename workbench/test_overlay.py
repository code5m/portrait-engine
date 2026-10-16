"""Areal overlay regression tests; synthetic inputs are not artistic evidence."""
import unittest
from shapely.geometry import Polygon, LineString, Point, GeometryCollection
from shapely import union_all
from study_light import area_geometry, area_intersection

class AreaOverlayTests(unittest.TestCase):
    def test_mixed_dimension_contacts_keep_holes_and_disconnected_areas(self):
        ring=Polygon([(0,0),(4,0),(4,4),(0,4)],holes=[[(1,1),(1,2),(2,2),(2,1)]])
        island=Polygon([(6,0),(7,0),(7,1),(6,1)])
        mixed=GeometryCollection([ring,island,LineString([(4,4),(5,5)]),Point(9,9)])
        got=area_geometry(mixed,1e-8)
        self.assertTrue(got.is_valid)
        self.assertAlmostEqual(got.area,16)
        self.assertFalse(got.contains(Point(1.5,1.5)))
        self.assertTrue(got.contains(Point(6.5,.5)))
        self.assertEqual(len(got.geoms),2)
    def test_contact_without_area_does_not_reach_overlay_as_a_line(self):
        a=Polygon([(0,0),(1,0),(1,1),(0,1)])
        b=Polygon([(1,0),(2,0),(2,1),(1,1)])
        self.assertTrue(area_intersection(a,b,1e-8).is_empty)
        self.assertTrue(area_geometry(LineString([(0,0),(1,1)]),1e-8).is_empty)
        self.assertTrue(area_geometry(Point(0,0),1e-8).is_empty)
    def test_fixed_precision_intersection_is_commutative_and_bounded(self):
        a=Polygon([(0,0),(2,0),(2,2),(0,2)])
        b=Polygon([(.5,-1),(1.5,-1),(1.5,3),(.5,3)])
        ab=area_intersection(a,b,1e-8);ba=area_intersection(b,a,1e-8)
        self.assertTrue(ab.equals(ba));self.assertAlmostEqual(ab.area,2)
        self.assertLess(ab.difference(a).area,1e-12)
if __name__=='__main__':unittest.main()
