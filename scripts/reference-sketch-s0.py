"""Run with Blender --background --python-exit-code 1 --python.
Offline REFERENCE, never CSS output. The emission shader evaluates a
Lambertian-direction diagnostic without GI: ambient + direct * max(0,N dot L).
It is not real skin illumination.
"""
import bpy,json,hashlib
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'test-results/sketch-s0'
CONFIG=json.loads((ROOT/'research/sketch/s0-scenes.json').read_text())
OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene
scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=8;scene.cycles.use_denoising=False
scene.render.threads_mode='FIXED';scene.render.threads=2
scene.render.resolution_x=scene.render.resolution_y=CONFIG['frameSize'];scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGB';scene.render.dither_intensity=0
scene.view_settings.view_transform='Standard';scene.view_settings.exposure=0;scene.view_settings.gamma=1
try:scene.view_settings.look='None'
except TypeError:pass
scene.world=bpy.data.worlds.new('Calibration white background');scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(1,1,1,1)
scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=1
camera=bpy.data.cameras.new('Orthographic calibration');cam=bpy.data.objects.new('Camera',camera);scene.collection.objects.link(cam)
cam.location=(0,0,6);camera.type='ORTHO';camera.ortho_scale=CONFIG['orthoScale'];scene.camera=cam
mat=bpy.data.materials.new('Normal diagnostic - NOT a skin shader');mat.use_nodes=True
nodes=mat.node_tree.nodes;nodes.clear();links=mat.node_tree.links
geo=nodes.new('ShaderNodeNewGeometry');unit=nodes.new('ShaderNodeVectorMath');unit.operation='NORMALIZE';links.new(geo.outputs['Normal'],unit.inputs[0])
dot=nodes.new('ShaderNodeVectorMath');dot.operation='DOT_PRODUCT';links.new(unit.outputs['Vector'],dot.inputs[0])
positive=nodes.new('ShaderNodeMath');positive.operation='MAXIMUM';positive.inputs[1].default_value=0;links.new(dot.outputs['Value'],positive.inputs[0])
scale=nodes.new('ShaderNodeMath');scale.operation='MULTIPLY';scale.inputs[1].default_value=CONFIG['direct'];links.new(positive.outputs[0],scale.inputs[0])
ambient=nodes.new('ShaderNodeMath');ambient.operation='ADD';ambient.inputs[1].default_value=CONFIG['ambient'];links.new(scale.outputs[0],ambient.inputs[0])
emission=nodes.new('ShaderNodeEmission');links.new(ambient.outputs[0],emission.inputs['Color'])
output=nodes.new('ShaderNodeOutputMaterial');links.new(emission.outputs[0],output.inputs['Surface'])
records=[]
def render(label):
    scene.render.filepath=str(OUT/label);bpy.ops.render.render(write_still=True)
    file=Path(scene.render.filepath);records.append({'file':file.name,'sha256':hashlib.sha256(file.read_bytes()).hexdigest()})
def attach(obj):
    obj.data.materials.append(mat)
    for poly in obj.data.polygons:poly.use_smooth=True
for profile in CONFIG['profiles']:
    bpy.ops.mesh.primitive_uv_sphere_add(segments=128,ring_count=64,radius=1)
    obj=bpy.context.object;obj.scale=profile['radii'];attach(obj)
    for light in CONFIG['lights']:
        dot.inputs[1].default_value=Vector(light['direction']).normalized()
        render('reference-'+profile['id']+'-'+light['id']+'.png')
    bpy.data.objects.remove(obj,do_unlink=True)
# Pinned upstream human geometry is a reference IMPORT CHECK, not an A/B identity match.
verts=[];faces=[]
for line in (OUT/'vendor/neutral.obj').read_text().splitlines():
    cols=line.split()
    if not cols:continue
    if cols[0]=='v':verts.append(tuple(map(float,cols[1:4])))
    elif cols[0]=='f':faces.append(tuple(int(v.split('/')[0])-1 for v in cols[1:]))
assert len(verts)==26719 and len(faces)==26384,(len(verts),len(faces))
lo=[min(v[i] for v in verts) for i in range(3)];hi=[max(v[i] for v in verts) for i in range(3)]
center=[(a+b)/2 for a,b in zip(lo,hi)];factor=2.8/max(b-a for a,b in zip(lo,hi))
verts=[tuple((v[i]-center[i])*factor for i in range(3)) for v in verts]
mesh=bpy.data.meshes.new('ICT Light neutral reference');mesh.from_pydata(verts,[],faces);mesh.update()
obj=bpy.data.objects.new('ICT reference only',mesh);scene.collection.objects.link(obj);attach(obj)
dot.inputs[1].default_value=Vector(CONFIG['lights'][0]['direction']).normalized();render('ict-neutral-reference.png')
scene.render.use_freestyle=True
settings=scene.view_layers[0].freestyle_settings
settings.mode='EDITOR'
lines=settings.linesets
if not len(lines):lines.new('Contours')
# An empty factory scene can have a line set but no linked style data-block.
# Initialize it explicitly instead of assuming UI defaults were created.
line_set=lines[0]
if line_set.linestyle is None:
    line_set.linestyle=bpy.data.linestyles.new('S0 reference contour')
style=line_set.linestyle
style.color=(0.02,0.02,0.02);style.thickness=1.0
line_set.select_by_edge_types=True;line_set.select_by_visibility=True
line_set.visibility='VISIBLE';line_set.select_silhouette=True
line_set.select_crease=False;line_set.select_border=True
render('ict-neutral-freestyle.png')
report={'blenderVersion':bpy.app.version_string,'viewTransform':scene.view_settings.view_transform,'look':scene.view_settings.look,'purpose':'calibration plus upstream head import; NOT CSS and NOT a realism verdict','referenceScenes':9,'ictVertices':len(verts),'ictFaces':len(faces),'outputs':records}
(OUT/'reference-manifest.json').write_text(json.dumps(report,indent=2))
print('S0_BLENDER_REFERENCE_COMPLETE',json.dumps(report))
