"""Build a fully offline research page, using unchanged S0 functions for A/C."""
import json,re,sys
from pathlib import Path
from sketch_s1_provenance import source_digest
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'test-results/sketch-s1';OUT.mkdir(parents=True,exist_ok=True)
s0=(ROOT/'study/sketch-s0.mjs').read_text().split("if(typeof document!=='undefined')")[0]
s0=re.sub(r'\bexport\s+', '', s0)
core=(ROOT/'study/sketch-s1.mjs').read_text()
core=re.sub(r"import .*?from './sketch-s0.mjs';",'const {unit,srgb,surfacePoint,bandContour,sceneMarkup}=S0;',core)
core=re.sub(r'\bexport\s+', '', core)
config=(ROOT/'research/sketch/s1-scenes.json').read_text().replace('<','\\u003c')
js='const S0=(()=>{'+s0+';return {unit,srgb,surfacePoint,bandContour,sceneMarkup};})();\n'+core
app=r'''
const config=JSON.parse(document.getElementById('config').textContent), all=cases(config);
const select=document.getElementById('scene-select'), variant=document.getElementById('variant'), layer=document.getElementById('layer'), bounce=document.getElementById('bounce');
for(const item of all){const opt=document.createElement('option');opt.value=item.id;opt.textContent=item.id+' / '+item.shape.split;select.append(opt);}
function show(id,mode='flat32',reflected=false,part='form'){
 const item=all.find(x=>x.id===id);if(!item)throw Error('Unknown fixture');
 const start=performance.now(),html=renderScene(item.shape,item.light,config,{variant:mode,bounce:reflected,layer:part});
 const viewport=document.getElementById('viewport');viewport.innerHTML=html;
 const generated=performance.now();viewport.getBoundingClientRect();const laidOut=performance.now();
 select.value=id;variant.value=mode;layer.value=part;bounce.checked=reflected;
 const stat={scene:id,variant:mode,bounce:reflected,layer:part,generateMs:generated-start,layoutMs:laidOut-generated,nodeCount:viewport.querySelectorAll('*').length,patchCount:viewport.querySelectorAll('.form>i,.surface>i').length};
 document.getElementById('stats').textContent=JSON.stringify(stat,null,2);
 return stat;
}
window.S1={show,config,all,renderScene,shadowGeometry,illumination};
function update(){show(select.value,variant.value,bounce.checked,layer.value);}
for(const el of [select,variant,layer,bounce])el.addEventListener('change',update);
const p=new URLSearchParams(location.search);
show(p.get('scene')||all[0].id,p.get('variant')||'flat32',p.get('bounce')==='1',p.get('layer')||'composite');
document.documentElement.dataset.ready='true';
'''
html='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>S1 / CSS Form Laboratory</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#f5f4ef;color:#252626;font:15px/1.7 system-ui,sans-serif}main{max-width:1080px;margin:40px auto;padding:24px}h1{font-size:30px;margin:0 0 12px}.label{letter-spacing:.15em;font-size:12px}header{border-bottom:1px solid #ccc;padding-bottom:20px}.controls{display:flex;gap:16px;flex-wrap:wrap;margin:24px 0}label{display:flex;gap:8px;align-items:center}select{max-width:340px;padding:8px;background:white;border:1px solid #aaa}.work{display:flex;gap:40px;align-items:flex-start;flex-wrap:wrap}.scene{position:relative;width:256px;height:256px;background:white;overflow:hidden;flex-shrink:0}.form{position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);border-radius:50%;overflow:hidden}.form>i,.surface>i,.surface,.receiver,.cast-shadow{display:block;position:absolute;inset:0}.form>i,.surface>i{pointer-events:none}pre{font:12px/1.6 monospace;white-space:pre-wrap}.notes{max-width:520px}.notice{border-left:3px solid #666;padding-left:16px}footer{margin-top:28px;color:#555}.viewport-frame{padding:24px;background:#fff;border:1px solid #ddd}
</style><main><header><div class="label">PORTRAIT ENGINE / SKETCH RESEARCH S1</div><h1>基本形体、明暗与投影</h1><p>HTML + CSS 原生绘制；此页不加载图片、SVG 或 Canvas。</p></header>
<div class="controls"><label>场景 <select id="scene-select"></select></label><label>表达 <select id="variant"><option value="flat16">A / 16 层平色</option><option value="gradient16">B / 16 层渐变（椭球）</option><option value="flat32" selected>C / 32 层平色</option></select></label><label>视图 <select id="layer"><option value="form">形体明暗</option><option value="shadow">几何投影</option><option value="composite">形体 + 接收平面</option></select></label><label><input id="bounce" type="checkbox">地面反光近似</label></div>
<div class="work"><div class="viewport-frame"><div id="viewport" class="scene"></div></div><div class="notes"><p class="notice">ART_UNVERIFIED / 人像写实质量未经独立观察者验证。这是形体研究页，不是新的人物作品。</p><p>反光使用无限、均匀受光地面的半球近似，不包含有限地面、二次遮挡或多次光反射。</p><p>B 只用于椭球渐变候选对照；其他形体在 B 下保持 16 区域基线。开启反光时使用分段等照度算法。</p><pre id="stats"></pre></div></div><footer>新场景只改几何与光照参数，不添加专属 CSS。默认人像渲染器不受影响。</footer></main><script type="application/json" id="config">'''+config+'''</script><script>'''+js+app+'''</script></html>'''
html=html.replace('<meta charset="utf-8">','<meta charset="utf-8"><meta name="source-digest" content="'+source_digest()+'">')
path=OUT/'lab.html'
if '--check' in sys.argv:
 assert path.read_text()==html,'S1 offline build drift'
else:path.write_text(html,encoding='utf-8')
print('S1_OFFLINE_PAGE',len(html.encode()))
