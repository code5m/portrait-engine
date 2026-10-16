"""Blender reference: independent surface normals and physical shadow rays.
The bounce shader is the same declared hemisphere MODEL, not measured real GI.
Run: blender --background --python-exit-code 1 --python this_file.py
"""
import bpy,hashlib,json,math,sys
from pathlib import Path
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'test-results/sketch-s1'
sys.path.insert(0,str(ROOT/'scripts'))
from sketch_s1_provenance import source_digest
SOURCE=source_digest()
C=json.loads((ROOT/'research/sketch/s1-scenes.json').read_text());OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=16;scene.cycles.use_denoising=False
scene.render.threads_mode='FIXED';scene.render.threads=2
scene.render.resolution_x=scene.render.resolution_y=C['frameSize'];scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGB';scene.render.dither_intensity=0
scene.view_settings.view_transform='Standard';scene.view_settings.look='None';scene.view_settings.exposure=0;scene.view_settings.gamma=1
world=bpy.data.worlds.new('reference world');world.use_nodes=True;scene.world=world
world.node_tree.nodes['Background'].inputs['Color'].default_value=(1,1,1,1)
camdata=bpy.data.cameras.new('fixed orthographic');cam=bpy.data.objects.new('camera',camdata);scene.collection.objects.link(cam)
cam.location=(0,0,10);camdata.type='ORTHO';camdata.ortho_scale=C['orthoScale'];scene.camera=cam
G=Vector(C['groundNormal']).normalized()
mat=bpy.data.materials.new('normal diagnostic / explicit hemisphere approximation');mat.use_nodes=True
nodes=mat.node_tree.nodes;nodes.clear();links=mat.node_tree.links
geo=nodes.new('ShaderNodeNewGeometry');norm=nodes.new('ShaderNodeVectorMath');norm.operation='NORMALIZE';links.new(geo.outputs['Normal'],norm.inputs[0])
ldot=nodes.new('ShaderNodeVectorMath');ldot.operation='DOT_PRODUCT';links.new(norm.outputs[0],ldot.inputs[0])
gdot=nodes.new('ShaderNodeVectorMath');gdot.operation='DOT_PRODUCT';gdot.inputs[1].default_value=G;links.new(norm.outputs[0],gdot.inputs[0])
def op(kind,a=None,b=0):
    n=nodes.new('ShaderNodeMath');n.operation=kind
    if a is not None:links.new(a,n.inputs[0])
    n.inputs[1].default_value=b
    return n
positive=op('MAXIMUM',ldot.outputs['Value'],0);direct=op('MULTIPLY',positive.outputs[0],C['direct'])
ambient=op('ADD',direct.outputs[0],C['ambient'])
neg=op('MULTIPLY',gdot.outputs['Value'],-1);one=op('ADD',neg.outputs[0],1);gain=op('MULTIPLY',one.outputs[0],0)
total=op('ADD',ambient.outputs[0]);links.new(gain.outputs[0],total.inputs[1])
emit=nodes.new('ShaderNodeEmission');links.new(total.outputs[0],emit.inputs['Color']);output=nodes.new('ShaderNodeOutputMaterial');links.new(emit.outputs[0],output.inputs['Surface'])
def diffuse(name,color):
    m=bpy.data.materials.new(name);m.use_nodes=True;n=m.node_tree.nodes;n.clear();d=n.new('ShaderNodeBsdfDiffuse');d.inputs['Color'].default_value=(color,color,color,1);o=n.new('ShaderNodeOutputMaterial');m.node_tree.links.new(d.outputs[0],o.inputs['Surface']);return m
white=diffuse('white receiving plane',1);black=diffuse('black occluder',0)
def mesh_object(name,verts,faces,smooth=False):
    data=bpy.data.meshes.new(name);data.from_pydata(verts,[],faces);data.update()
    obj=bpy.data.objects.new(name,data);scene.collection.objects.link(obj);obj.data.materials.append(mat)
    for p in data.polygons:p.use_smooth=smooth
    return obj

def make_shape(s):
    if s['kind']=='ellipsoid':
        bpy.ops.mesh.primitive_uv_sphere_add(segments=192,ring_count=96,radius=1);obj=bpy.context.object;obj.scale=s['radii'];obj.data.materials.append(mat)
        for p in obj.data.polygons:p.use_smooth=True
        offset=-math.sqrt(sum((s['radii'][i]*G[i])**2 for i in range(3)))
        return [obj],offset
    if s['kind']=='cylinder':
        count=192;R=Matrix.Rotation(math.radians(s['tilt']),3,'X');r=s['radius'];h=s['halfHeight']
        verts=[tuple(R@Vector((r*math.sin(2*math.pi*i/count),y,r*math.cos(2*math.pi*i/count)))) for y in [-h,h] for i in range(count)]
        sides=[(i,(i+1)%count,(i+1)%count+count,i+count) for i in range(count)]
        barrel=mesh_object('cylinder barrel',verts,sides,True)
        caps=mesh_object('cylinder planar caps',verts,[tuple(reversed(range(count))),tuple(range(count,count*2))])
        local=R.transposed()@G;offset=-(r*math.hypot(local.x,local.z)+h*abs(local.y))
        return [barrel,caps],offset
    x,y,z=s['half'];R=Matrix.Rotation(math.radians(s['yaw']),3,'Y')
    verts=[R@Vector(p) for p in [(-x,-y,-z),(x,-y,-z),(x,-y,z),(-x,-y,z),(-x,y,-z),(x,y,-z),(x,.15*y,z),(-x,.15*y,z)]]
    center=sum(verts,Vector())/8
    faces=[]
    for ids in [(0,3,2,1),(0,1,5,4),(3,7,6,2),(0,4,7,3),(1,2,6,5),(4,5,6,7)]:
        n=(verts[ids[1]]-verts[ids[0]]).cross(verts[ids[2]]-verts[ids[0]])
        faces.append(tuple(reversed(ids)) if n.dot(verts[ids[0]]-center)<0 else ids)
    return [mesh_object('wedge',verts,faces)],min(G.dot(v) for v in verts)
records=[]
def render(name):
    path=OUT/name;scene.render.filepath=str(path);bpy.ops.render.render(write_still=True)
    records.append({'file':name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
for shape in C['profiles']:
    lights=C['holdoutLights'] if shape['split']=='holdout' else C['lights']
    for light in lights:
        ident=shape['id']+'-'+light['id'];L=Vector(light['direction']).normalized();objects,offset=make_shape(shape)
        world.node_tree.nodes['Background'].inputs['Strength'].default_value=1
        ldot.inputs[1].default_value=L
        for bounce in [False,True]:
            gain.inputs[1].default_value=C['bounceStrength']*C['receiverAlbedo']*C['direct']*max(0,G.dot(L))/2 if bounce else 0
            render('reference-'+ident+'-'+str(int(bounce))+'.png')
        # A real Cycles directional-light occlusion pass, not a copied CSS mask.
        world.node_tree.nodes['Background'].inputs['Strength'].default_value=0
        for obj in objects:obj.visible_camera=False;obj.visible_shadow=True;obj.data.materials.clear();obj.data.materials.append(black)
        tangent=Vector((1,0,0));other=G.cross(tangent);center=G*offset
        verts=[tuple(center+20*a*tangent+20*b*other) for a,b in [(-1,-1),(1,-1),(1,1),(-1,1)]]
        floor=mesh_object('receiving plane',verts,[(0,1,2,3)]);floor.data.materials.clear();floor.data.materials.append(white)
        sun_data=bpy.data.lights.new('directional source','SUN');sun_data.energy=math.pi;sun_data.angle=0
        sun=bpy.data.objects.new('sun',sun_data);scene.collection.objects.link(sun);sun.rotation_euler=L.to_track_quat('Z','Y').to_euler()
        render('shadow-reference-'+ident+'.png')
        for obj in objects+[floor,sun]:bpy.data.objects.remove(obj,do_unlink=True)
assert source_digest()==SOURCE,'Source changed during reference render'
report={'sourceDigest':SOURCE,'blenderVersion':bpy.app.version_string,'viewTransform':scene.view_settings.view_transform,'look':scene.view_settings.look,'normalFrames':54,'physicalShadowFrames':27,'outputs':records,'bounceBoundary':'diagnostic hemisphere irradiance, not a full Cycles bounce match'}
(OUT/'reference.json').write_text(json.dumps(report,indent=2));print('S1_BLENDER_REFERENCE_COMPLETE',len(records),bpy.app.version_string)
