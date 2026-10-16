"""S3 independent Cycles diffuse-direct reference with real shadow rays.
The hemisphere fill is a declared unoccluded approximation, not measured GI.
No reference pixels feed the numerical compiler. Also exports no-shadow ablation.
"""
import sys,json,math
from pathlib import Path
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'workbench'))
from model import CONFIG,CACHE,HeadModel,save_json,sha
from study_light import protocol,source_digest
S=protocol();model=HeadModel()
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
if args and args[0].endswith('.json'):specs=[json.loads(Path(args[0]).read_text())]
else:
    split=args[0] if args else 'all'
    specs=[dict(id=x['id']+'-'+l['id'],weights=x['weights'],light=l['direction'])
           for x in CONFIG['identities'] if split=='all' or x['split']==split for l in CONFIG['lights']]


def setup(camera):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU'
    scene.cycles.samples=16;scene.cycles.use_denoising=False
    scene.cycles.max_bounces=1;scene.cycles.diffuse_bounces=0
    scene.render.threads_mode='FIXED';scene.render.threads=2
    scene.render.resolution_x=scene.render.resolution_y=CONFIG['frameSize'];scene.render.resolution_percentage=100
    scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
    scene.render.dither_intensity=0;scene.view_settings.view_transform='Standard';scene.view_settings.look='None'
    scene.view_settings.exposure=0;scene.view_settings.gamma=1
    world=bpy.data.worlds.new('no sampled world irradiance');world.use_nodes=True
    world.node_tree.nodes['Background'].inputs['Strength'].default_value=0;scene.world=world
    c=bpy.data.cameras.new('same orthographic camera');cam=bpy.data.objects.new('camera',c);scene.collection.objects.link(cam)
    cam.location=(*camera['center'],80);c.type='ORTHO';c.ortho_scale=camera['span'];scene.camera=cam
    return scene


def material():
    m=bpy.data.materials.new('Diffuse direct + camera-only hemisphere diagnostic');m.use_nodes=True
    n=m.node_tree.nodes;n.clear();links=m.node_tree.links
    diff=n.new('ShaderNodeBsdfDiffuse');diff.inputs['Color'].default_value=(CONFIG['direct'],)*3+(1,)
    geo=n.new('ShaderNodeNewGeometry');unit=n.new('ShaderNodeVectorMath');unit.operation='NORMALIZE';links.new(geo.outputs['Normal'],unit.inputs[0])
    dot=n.new('ShaderNodeVectorMath');dot.operation='DOT_PRODUCT';dot.inputs[1].default_value=Vector(S['fillUp']).normalized();links.new(unit.outputs['Vector'],dot.inputs[0])
    add=n.new('ShaderNodeMath');add.operation='ADD';add.inputs[1].default_value=1;links.new(dot.outputs['Value'],add.inputs[0])
    mul=n.new('ShaderNodeMath');mul.operation='MULTIPLY';mul.inputs[1].default_value=S['fillStrength']/2;links.new(add.outputs[0],mul.inputs[0])
    amb=n.new('ShaderNodeMath');amb.operation='ADD';amb.inputs[1].default_value=CONFIG['ambient'];links.new(mul.outputs[0],amb.inputs[0])
    path=n.new('ShaderNodeLightPath');camera=n.new('ShaderNodeMath');camera.operation='MULTIPLY';links.new(amb.outputs[0],camera.inputs[0]);links.new(path.outputs['Is Camera Ray'],camera.inputs[1])
    emission=n.new('ShaderNodeEmission');links.new(camera.outputs[0],emission.inputs['Color'])
    total=n.new('ShaderNodeAddShader');links.new(diff.outputs[0],total.inputs[0]);links.new(emission.outputs[0],total.inputs[1])
    out=n.new('ShaderNodeOutputMaterial');links.new(total.outputs[0],out.inputs['Surface'])
    return m


def sun(scene,direction):
    data=bpy.data.lights.new('directional unit irradiance','SUN');data.energy=math.pi;data.angle=0
    obj=bpy.data.objects.new('sun',data);scene.collection.objects.link(obj)
    obj.rotation_euler=Vector(direction).normalized().to_track_quat('Z','Y').to_euler()


def mesh(scene,v,f):
    data=bpy.data.meshes.new('same identity vertices');data.from_pydata(v.tolist(),[],f.tolist());data.update()
    obj=bpy.data.objects.new('head',data);scene.collection.objects.link(obj);data.materials.append(material())
    for poly in data.polygons:poly.use_smooth=True
    return obj


out=CACHE/'studies/reference';out.mkdir(parents=True,exist_ok=True)
for cosine in [.25,.65,1.0]:
    import numpy as np
    scene=setup({'center':[0,0],'span':2})
    obj=mesh(scene,np.array([[-2,-2,0],[2,-2,0],[2,2,0],[-2,2,0]],float),np.array([[0,1,2],[0,2,3]],int))
    sun(scene,[math.sqrt(1-cosine*cosine),0,cosine]);scene.render.filepath=str(out/('calibration-'+str(cosine)+'.png'))
    bpy.ops.render.render(write_still=True)
for spec in specs:
    ident=spec['id'];v,f,n,r=model.mesh(spec['weights']);scene=setup(model.camera);obj=mesh(scene,v,f);sun(scene,spec['light'])
    for enabled in [False,True]:
        obj.visible_shadow=enabled
        path=out/(ident+('-shadow' if enabled else '-unshadowed')+'.png')
        scene.render.filepath=str(path);bpy.ops.render.render(write_still=True)
        save_json(path.with_suffix('.json'),{'id':ident,'castVisibility':enabled,'sourceDigest':source_digest(),
                    'geometryHash':sha(v.astype('<f8').tobytes()),'camera':model.camera,'imageHash':sha(path.read_bytes()),
                    'blenderVersion':bpy.app.version_string,'model':'Cycles diffuse direct shadows + declared camera-only hemisphere fill, no GI'})
    print('S3_REFERENCE_COMPLETE',ident,flush=True)
