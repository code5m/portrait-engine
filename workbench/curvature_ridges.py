"""Geometry-only crease sparsification; no per-identity or pixel information."""
import numpy as np


def vertex_curvature(vertices, faces):
    """Cotangent mean-curvature magnitude on the original 3D mesh.

    Barycentric vertex areas normalize density. Open boundaries are returned
    separately: their one-sided Laplacian is not an interior ridge estimate.
    """
    v=np.asarray(vertices,dtype=float);f=np.asarray(faces,dtype=int)
    if v.ndim!=2 or v.shape[1]!=3 or not np.isfinite(v).all():
        raise ValueError('Finite three-dimensional vertices required')
    if f.ndim!=2 or f.shape[1]!=3 or f.size==0 or f.min()<0 or f.max()>=len(v):
        raise ValueError('Valid triangle indices required')
    tri=v[f];cross=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);twice=np.linalg.norm(cross,axis=1)
    scale=max(float(np.ptp(v,axis=0).max()),1e-12)
    valid=twice>scale*scale*1e-14
    areas=np.zeros(len(v));delta=np.zeros_like(v)
    for k in range(3):
        np.add.at(areas,f[valid,k],twice[valid]/6)
        j=(k+1)%3;m=(k+2)%3
        cot=np.einsum('ij,ij->i',tri[valid,j]-tri[valid,k],tri[valid,m]-tri[valid,k])/twice[valid]
        a=f[valid,j];b=f[valid,m];weighted=cot[:,None]*(v[b]-v[a])
        np.add.at(delta,a,weighted);np.add.at(delta,b,-weighted)
    curvature=np.linalg.norm(delta,axis=1)/np.maximum(4*areas,scale*scale*1e-14)
    edges=np.sort(np.concatenate([f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]]),axis=1)
    unique,counts=np.unique(edges,axis=0,return_counts=True)
    boundary=np.zeros(len(v),dtype=bool);boundary[np.unique(unique[counts!=2])]=True
    return curvature,boundary


def ridge_supported(curvature,boundary,edge,opposites):
    """Keep a cross-edge curvature maximum, not every curved mesh facet.

    A ridge may continue along its tangent. Only the two opposite triangle
    vertices compete across the edge, avoiding arbitrary top-K or ink caps.
    """
    a,b=edge;c,d=opposites
    values=np.asarray(curvature)[[a,b,c,d]]
    if not np.isfinite(values).all() or (values<0).any():raise ValueError('Finite nonnegative curvature required')
    if boundary[a] or boundary[b]:return False
    crest=float((values[0]+values[1])/2);flank=float(max(values[2:]))
    return crest>flank+max(crest,flank,1e-12)*1e-9
