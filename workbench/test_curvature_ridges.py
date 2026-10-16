"""Synthetic curvature selection controls, never head or human evidence."""
import unittest
import numpy as np
from curvature_ridges import vertex_curvature,ridge_supported


def mesh(fold=0):
    xs=np.arange(-3,4,dtype=float);ys=np.arange(-3,4,dtype=float)
    v=np.array([[x,y,fold*abs(x)] for y in ys for x in xs])
    f=[]
    for j in range(6):
        for i in range(6):
            a=j*7+i;f.extend([[a,a+1,a+8],[a,a+8,a+7]])
    return v,np.array(f)


class CurvatureTests(unittest.TestCase):
    def test_planar_interior_has_no_curvature_or_ridge(self):
        v,f=mesh();h,b=vertex_curvature(v,f)
        self.assertTrue(np.all(h[~b]<1e-12));self.assertFalse(ridge_supported(h,b,[17,24],[16,25]))
    def test_fold_crest_is_retained_and_density_normalized(self):
        v,f=mesh(1);h,b=vertex_curvature(v,f)
        self.assertTrue(ridge_supported(h,b,[17,24],[16,25]))
        self.assertGreater(h[17],.1);self.assertLess(h[16],1e-12)
        scaled,_=vertex_curvature(v*7+np.array([8,9,-4]),f)
        self.assertTrue(np.allclose(scaled,h/7))
        self.assertTrue(ridge_supported(scaled,b,[17,24],[16,25]))
    def test_constant_curvature_plateau_and_monotone_slope_are_not_ridges(self):
        b=np.zeros(4,dtype=bool)
        self.assertFalse(ridge_supported(np.ones(4),b,[0,1],[2,3]))
        self.assertFalse(ridge_supported(np.array([2,2,1,3.]),b,[0,1],[2,3]))
        self.assertTrue(ridge_supported(np.array([3,3,1,2.]),b,[0,1],[2,3]))
    def test_boundary_and_invalid_data_cannot_be_called_interior_ridges(self):
        self.assertFalse(ridge_supported(np.array([3,3,1,1.]),np.array([1,0,0,0],bool),[0,1],[2,3]))
        with self.assertRaises(ValueError):vertex_curvature(np.array([[0,0,np.nan]]),np.array([[0,0,0]]))
        with self.assertRaises(ValueError):ridge_supported(np.array([np.nan,3,1,1]),np.zeros(4,bool),[0,1],[2,3])
    def test_face_order_and_rigid_rotation_do_not_change_ridge_selection(self):
        v,f=mesh(1);h,b=vertex_curvature(v,f)
        rotation=np.array([[0,0,1],[1,0,0],[0,1,0.]])
        other,b2=vertex_curvature(v@rotation,f[::-1,::-1])
        self.assertTrue(np.allclose(h,other));self.assertTrue(np.array_equal(b,b2))
        self.assertEqual(ridge_supported(h,b,[17,24],[16,25]),ridge_supported(other,b2,[24,17],[25,16]))
if __name__=='__main__':unittest.main()
