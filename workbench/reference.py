"""Independent Blender camera visibility/normal shader. Reference image only;
its bytes never enter geometry.py or the CSS rendering subtree.
"""
import sys,json,math
from pathlib import Path
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'workbench'))
from model import CONFIG,CACHE,HeadModel,save_json,sha,canonical
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
model=HeadModel()
specs=[json.loads(Path(args[0]).read_text())] if args else [dict(id=x['id']+'-'+l['id'],weights=x['weights'],light=l['direction']) for x in CONFIG['identities'] for l in CONFIG['lights']]
for spec in specs:
    ident=spec['id'];v,f,n,regions=model.mesh(spec['weights'])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=8;scene.cycles.use_denoising=False
    scene.render.threads_mode='FIXED';scene.render.threads=2
    scene.render.resolution_x=scene.render.resolution_y=CONFIG['frameSize'];scene.render.resolution_percentage=100
    scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA';scene.render.dither_intensity=0
    scene.view_settings.view_transform='Standard';scene.view_settings.look='None';scene.view_settings.exposure=0;scene.view_settings.gamma=1
    data=bpy.data.meshes.new('Same numerical identity surface');data.from_pydata(v.tolist(),[],f.tolist());data.update()
    obj=bpy.data.objects.new('Head / surface only',data);scene.collection.objects.link(obj)
    for poly in data.polygons:poly.use_smooth=True
    m=bpy.data.materials.new('Normal light calibration, not skin');m.use_nodes=True;nodes=m.node_tree.nodes;nodes.clear();links=m.node_tree.links
    geo=nodes.new('ShaderNodeNewGeometry');norm=nodes.new('ShaderNodeVectorMath');norm.operation='NORMALIZE';links.new(geo.outputs['Normal'],norm.inputs[0])
    dot=nodes.new('ShaderNodeVectorMath');dot.operation='DOT_PRODUCT';dot.inputs[1].default_value=Vector(spec['light']).normalized();links.new(norm.outputs[0],dot.inputs[0])
    pos=nodes.new('ShaderNodeMath');pos.operation='MAXIMUM';pos.inputs[1].default_value=0;links.new(dot.outputs['Value'],pos.inputs[0])
    scale=nodes.new('ShaderNodeMath');scale.operation='MULTIPLY';scale.inputs[1].default_value=CONFIG['direct'];links.new(pos.outputs[0],scale.inputs[0])
    ambient=nodes.new('ShaderNodeMath');ambient.operation='ADD';ambient.inputs[1].default_value=CONFIG['ambient'];links.new(scale.outputs[0],ambient.inputs[0])
    emission=nodes.new('ShaderNodeEmission');links.new(ambient.outputs[0],emission.inputs['Color']);output=nodes.new('ShaderNodeOutputMaterial');links.new(emission.outputs[0],output.inputs['Surface']);data.materials.append(m)
    c=bpy.data.cameras.new('Fixed orthographic');cam=bpy.data.objects.new('Camera',c);scene.collection.objects.link(cam)
    cam.location=(*model.camera['center'],80);c.type='ORTHO';c.ortho_scale=model.camera['span'];scene.camera=cam
    out=CACHE/'reference';out.mkdir(parents=True,exist_ok=True);path=out/(ident+'.png')
    scene.render.filepath=str(path);bpy.ops.render.render(write_still=True)
    save_json(out/(ident+'.json'),{'id':ident,'camera':model.camera,'geometryHash':sha(v.astype('<f8').tobytes()),'imageHash':sha(path.read_bytes()),'blenderVersion':bpy.app.version_string,'shader':'same declared normal illumination; no cast/bounce/skin','view':'Standard/None'})
    print('S2_BLENDER_REFERENCE',ident,flush=True)
