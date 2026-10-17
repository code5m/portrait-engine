import {draw} from './pipeline_renderer.mjs';
const $=s=>document.querySelector(s);
const state={csrf:sessionStorage.getItem('portrait-csrf'),descriptor:null,renderId:null,annotations:[],busy:false};
const statuses={PASS:'通过',FAIL:'失败',PENDING:'待评审',NOT_RUN:'未运行',STALE:'版本已过期',ACCEPT:'已接受',REVISE:'需修改',REJECT:'不接受',COMPLETE:'技术完成',READY:'待开始',IN_PROGRESS:'进行中',NOT_STARTED:'未开始',BLOCKED:'技术阻塞'};
const operations={prepare:'准备模型',render:'生成样本',verify:'机器验证'};
const dimensions={structure:'头部结构',volume:'立体关系',eyes:'五官整合',identity:'身份区分',realism:'整体真实感'};
const viewNames={tone:'体积与候选效果',structure:'结构区域',masses:'三大灰阶','edges-control':'对照：全部结构硬边','material-control':'对照：关闭全部材料','hair-control':'对照：关闭头发'};
const stageNames={S2:'S2 头部结构',S3:'S3 大明暗与光源遮挡',S4:'S4 边缘层次',S5:'S5 排线、头发与材料',S6:'S6 新参数与表情验证'};
const expressionNames={neutral:'中性',smile:'微笑',frown:'嘴角下压',blink:'部分闭眼','jaw-open':'轻度张口'};
const materialNames={graphite:'石墨',charcoal:'炭笔'},hairNames={none:'无头发',short:'短发纤维',swept:'侧梳纤维'};
const stageLabel=document.createElement('label');stageLabel.textContent='研究阶段';
const pipeline=document.createElement('select');pipeline.id='pipeline';stageLabel.append(pipeline);$('#identity').closest('label').before(stageLabel);
for(const [key,labelText] of [['expression','表情姿态'],['material','绘画材料'],['hair','头皮纤维']]){
 const label=document.createElement('label');label.textContent=labelText;label.dataset.surfaceControl=key;
 const select=document.createElement('select');select.id=key;label.append(select);$('#light').closest('label').after(label);
}
function text(sel,t){$(sel).textContent=t;}
function toast(msg,error=false){text('#toast',msg);$('#toast').className='toast'+(error?' error':'');$('#toast').hidden=false;setTimeout(()=>$('#toast').hidden=true,7000);}
async function api(path,body){const r=await fetch('/api/v1/'+path,{method:body?'POST':'GET',headers:body?{'Content-Type':'application/json','X-CSRF-Token':state.csrf||''}:{},body:body?JSON.stringify(body):undefined});const d=await r.json();if(!r.ok)throw new Error(d.error||('HTTP '+r.status));return d;}
function setBusy(flag,message){state.busy=flag;for(const id of ['#prepare','#generate','#verify'])$(id).disabled=flag||(id==='#verify'&&!state.renderId);if(message)text('#status',message);}
async function job(operation,payload={}){
 if(state.busy)throw Error('请等待当前任务完成');setBusy(true,'任务已提交，正在处理...');
 try{const created=await api('jobs',{operation,payload});for(let k=0;k<1800;k++){const r=await api('jobs/'+created.jobId);text('#status',(r.status==='queued'?'排队中':'正在执行')+' / '+operations[operation]+' / '+created.jobId.slice(0,8));if(r.status==='succeeded'){text('#status','任务完成'+(r.result?.cached?'（复用当前版本的同参数数值结果）':''));return r.result;}if(r.status==='failed')throw Error(r.error);await new Promise(done=>setTimeout(done,1000));}throw Error('任务仍在运行，请在记录中查看');}finally{setBusy(false);}
}
function clearReview(){state.annotations=[];for(const e of $('#ratings').querySelectorAll('select'))e.value='';$('#verdict').value='';$('#note').value='';$('#human-confirmed').checked=false;renderPins();}
function renderPins(){const overlay=$('#pins'),list=$('#annotation-list');overlay.replaceChildren();list.replaceChildren();state.annotations.forEach((a,i)=>{const dot=document.createElement('span');dot.className='pin';dot.style.left=a.x*100+'%';dot.style.top=a.y*100+'%';dot.textContent=String(i+1);overlay.append(dot);const li=document.createElement('li');li.textContent=a.note;const remove=document.createElement('button');remove.textContent='删除';remove.onclick=()=>{state.annotations.splice(i,1);renderPins();};li.append(remove);list.append(li);});}
function populate(select,items,label){const previous=select.value;select.replaceChildren();for(const item of items){const option=document.createElement('option');option.value=typeof item==='string'?item:item.id;option.textContent=label(item);select.append(option);}if([...select.options].some(o=>o.value===previous))select.value=previous;}
function identities(){return pipeline.value==='S6'?state.catalog.surface.identities:state.catalog.identities;}
function syncWeights(){const item=identities().find(x=>x.id===$('#identity').value);if(item)for(let i=0;i<6;i++)$('#weight-'+i).value=item.weights[i];}
function configureInputs(){
 if(!state.catalog)return;const stage=pipeline.value,surface=['S5','S6'].includes(stage),catalog=state.catalog.surface;
 populate($('#identity'),identities(),item=>(stage==='S6'?'新模式样本 ':item.split==='holdout'?'预留样本 ':'基准样本 ')+item.label);
 populate($('#expression'),stage==='S6'?catalog.expressions:['neutral'],name=>expressionNames[name]||name);
 populate($('#material'),catalog.materials,name=>materialNames[name]||name);populate($('#hair'),catalog.hairstyles,name=>hairNames[name]||name);
 if(!$('#hair').dataset.initialized){$('#hair').value='swept';$('#hair').dataset.initialized='1';}
 for(const label of document.querySelectorAll('[data-surface-control]'))label.hidden=!surface;
 $('#expression').disabled=stage!=='S6';$('#custom').disabled=stage==='S6';if(stage==='S6')$('#custom').checked=false;syncWeights();
}
function viewOptions(stage){const modes=['tone','structure'];if(stage!=='S2')modes.push('masses');if(['S4','S5','S6'].includes(stage))modes.push('edges-control');if(['S5','S6'].includes(stage))modes.push('material-control','hair-control');populate($('#view'),modes,mode=>viewNames[mode]);$('#view').value='tone';}
async function loadRender(id){
 state.renderId=id;state.descriptor=await api('renders/'+id);const stage=state.descriptor.stage||'S2';pipeline.value=stage;configureInputs();viewOptions(stage);
 const spec=state.descriptor.surfaceSpec;if(spec){for(const [key,value] of Object.entries({identity:spec.identity,expression:spec.expression,material:spec.material,hair:spec.hair,light:spec.lightId}))$('#'+key).value=value;syncWeights();}
 draw($('#candidate'),state.descriptor,$('#view').value);$('#candidate-empty').hidden=true;$('#verify').disabled=false;$('#submit-review').disabled=false;
 text('#sample-name',stage+' / '+id.slice(-8));text('#hash',stage+' / sample '+state.descriptor.contentHash+' / source '+state.descriptor.sourceDigest);$('.eyebrow').textContent='SKETCH RESEARCH / '+stage;
 const legends={S2:'结构区域是表面概括，不是骨骼或肌肉解剖模型。',S3:'光源遮挡与明确的半球补光近似；三大灰阶观察整体关系，不等于完整光传输。',S4:'边缘只选择几何遮挡与有依据的转折。全部硬边对照的评价不会冒充候选评价。',S5:'随形排线、石墨／炭笔颗粒与头皮纤维实验。不是皮肤毛孔或完整三维毛发；真人观察延期，不阻塞机器验证。',S6:'新 PCA 模式与五种表情姿态迁移，不是陌生真人识别。机器验证底层形体与材料约束，不能认证艺术质量。'};
 text('#legend',legends[stage]);$('#download').href='/api/v1/renders/'+id+'/download.html';$('#download').hidden=false;clearReview();await validation();
}
async function validation(){
 if(!state.renderId)return;const v=await api('renders/'+state.renderId+'/validation'),machine=v.machine.status,human=v.human.status;
 text('#machine-badge','机器：'+(statuses[machine]||machine));text('#human-badge','人工：'+(human==='PENDING'&&v.humanReview?.status==='DEFERRED_BY_OWNER'?'延期，尚未评审':statuses[human]||human));
 $('#machine-badge').className='badge'+(machine==='PASS'?' pass':machine==='FAIL'?' fail':'');$('#human-badge').className='badge'+(human==='ACCEPT'?' pass':['REJECT','REVISE'].includes(human)?' fail':'');
 text('#machine-summary',machine==='PASS'?(['S5','S6'].includes(v.stage)?'当前样本通过底层形体、独立参考与材料消融技术检查。头发/表情的自然程度和艺术质量仍未验证。':'当前样本通过真实浏览器与独立参考的技术检查，艺术质量另行评审。'):machine==='FAIL'?'机器检查未通过，意见仍可保存。':'尚无当前版本的有效机器结果。');
 $('#metrics').replaceChildren();for(const [key,value] of Object.entries(v.machine.metrics||{})){const box=document.createElement('div');box.className='metric';const number=document.createElement('b');number.textContent=String(value);const desc=document.createElement('small');desc.textContent={fullMAE:'底层全图灰度误差',interiorMAE:'底层内部灰度误差',featureMAE:'底层五官误差',silhouetteIoU:'底层轮廓重合度'}[key]||key;box.append(number,desc);$('#metrics').append(box);}
 let history=$('#saved-reviews');if(!history){history=document.createElement('div');history.id='saved-reviews';$('#review-receipt').after(history);}history.replaceChildren();
 for(const r of v.human.reviews){const entry=document.createElement('p');entry.className='small';entry.textContent=(r.reviewerLabel||'评审者')+' / '+(statuses[r.verdict.toUpperCase()]||r.verdict)+' / '+(r.note||'')+' / '+(viewNames[r.viewMode]||r.viewMode);history.append(entry);}
 const img=$('#reference');if(['PASS','FAIL'].includes(machine)){img.src='/api/v1/renders/'+state.renderId+'/reference.png';img.hidden=false;$('#reference-empty').hidden=true;}else{img.hidden=true;img.removeAttribute('src');$('#reference-empty').hidden=false;}
}
async function stages(){const data=await api('stages');$('#stage-grid').replaceChildren();for(const s of data.stages){const card=document.createElement('article'),head=document.createElement('h3'),p=document.createElement('p'),report=document.createElement('div');head.textContent=s.id+' / '+s.title;p.textContent=(statuses[s.status]||s.status)+' · 艺术质量未验证';report.className='hash';report.textContent=s.report||'无阶段结果';card.append(head,p,report);$('#stage-grid').append(card);}}
async function history(){const [r,j]=await Promise.all([api('renders'),api('jobs')]);$('#history').replaceChildren();for(const row of r.renders){const b=document.createElement('button');b.className='quiet';b.textContent=(row.stage||'S2')+' / '+row.id.slice(-12)+' / '+row.weights.map(x=>x.toFixed(1)).join(' ');b.onclick=()=>{tab('lab');loadRender(row.id).catch(e=>toast(e.message,true));};$('#history').append(b);}text('#jobs',j.jobs.map(x=>x.id.slice(0,8)+'  '+(operations[x.operation]||x.operation)+'  '+({succeeded:'完成',failed:'失败',running:'执行中',queued:'排队'}[x.status]||x.status)+(x.error?'\n'+x.error:'')).join('\n'));}
function tab(name){for(const t of ['lab','stages','history'])$('#tab-'+t).hidden=t!==name;for(const b of document.querySelectorAll('[data-tab]'))b.classList.toggle('active',b.dataset.tab===name);if(name==='stages')stages().catch(e=>toast(e.message,true));if(name==='history')history().catch(e=>toast(e.message,true));}
async function ready(){const data=await api('catalog');state.catalog=data;populate(pipeline,data.stages,stage=>stageNames[stage]||stage);populate($('#light'),data.lights,item=>({left:'左侧光',front:'正面光',right:'右侧光'}[item.id]||item.id));configureInputs();text('#status','已就绪。选择研究阶段、人物和光照。首次计算需要等待；真人评价延期不会阻止生成与机器验证。');}
for(let i=0;i<6;i++){const label=document.createElement('label');label.textContent='身份模式 '+(i+1);const input=document.createElement('input');input.type='range';input.min=-1.5;input.max=1.5;input.step=.05;input.value=0;input.id='weight-'+i;input.setAttribute('aria-label',label.textContent);label.append(input);$('#sliders').append(label);}
for(const [key,title] of Object.entries(dimensions)){const label=document.createElement('label');label.htmlFor='score-'+key;label.textContent=title;const sel=document.createElement('select');sel.id='score-'+key;for(let i=0;i<=5;i++){const option=document.createElement('option');option.value=i?i:'';option.textContent=i?String(i):'—';sel.append(option);}$('#ratings').append(label,sel);}
$('#identity').onchange=syncWeights;pipeline.onchange=()=>{configureInputs();text('#status','下一次生成将使用 '+pipeline.value+'。当前固定样本未改变。');};
for(const id of ['expression','material','hair'])$('#'+id).onchange=()=>text('#status','参数仅影响下一次生成，当前固定样本和验证记录未改变。');
$('#view').onchange=()=>{if(state.descriptor){draw($('#candidate'),state.descriptor,$('#view').value);clearReview();}};
$('#prepare').onclick=async()=>{try{await job('prepare');toast('参考模型已校验并准备完成');}catch(e){text('#status',e.message);toast(e.message,true);}};
$('#generate').onclick=async()=>{try{const payload={light:$('#light').value,stage:pipeline.value};if($('#custom').checked&&pipeline.value!=='S6')payload.weights=Array.from({length:6},(_,i)=>+$('#weight-'+i).value);else payload.identity=$('#identity').value;if(['S5','S6'].includes(pipeline.value))Object.assign(payload,{expression:$('#expression').value,material:$('#material').value,hair:$('#hair').value});const result=await job('render',payload);await loadRender(result.renderId);toast('固定样本已就绪，可立即进行机器验证');}catch(e){text('#status',e.message);toast(e.message,true);}};
$('#verify').onclick=async()=>{try{await job('verify',{renderId:state.renderId});await validation();}catch(e){await validation().catch(()=>{});text('#status',e.message);toast(e.message,true);}};
$('#candidate-paper').onclick=e=>{if(!state.descriptor||!$('#pin-note').value.trim())return;const r=$('#candidate-paper').getBoundingClientRect();if(state.annotations.length>=30)return;state.annotations.push({x:Math.max(0,Math.min(1,(e.clientX-r.left)/r.width)),y:Math.max(0,Math.min(1,(e.clientY-r.top)/r.height)),note:$('#pin-note').value.trim()});$('#pin-note').value='';renderPins();};
$('#submit-review').onclick=async()=>{try{if(!state.descriptor)throw Error('请先生成样本');const scores=Object.fromEntries(Object.keys(dimensions).map(k=>[k,+$('#score-'+k).value]));if(Object.values(scores).some(v=>v<1)||!$('#verdict').value||!$('#human-confirmed').checked)throw Error('请完成五项评分、结论和人工确认');const r=await api('reviews',{renderId:state.renderId,sourceDigest:state.descriptor.sourceDigest,contentHash:state.descriptor.contentHash,viewMode:$('#view').value,scores,verdict:$('#verdict').value,note:$('#note').value,annotations:state.annotations,humanConfirmed:true});text('#review-receipt','已保存：'+r.id+'。与阶段、样本、版本和观察方式绑定，不签发 ART_PASS。');await validation();toast('你的评审已持久保存');}catch(e){toast(e.message,true);}};
$('#export').onclick=()=>{location.href='/api/v1/export';};
for(const b of document.querySelectorAll('[data-tab]'))b.onclick=()=>tab(b.dataset.tab);
$('#login-form').onsubmit=async e=>{e.preventDefault();try{const r=await api('session',{name:$('#reviewer-name').value,token:$('#access-token').value});$('#access-token').value='';state.csrf=r.csrf;sessionStorage.setItem('portrait-csrf',r.csrf);$('#login').close();await ready();}catch(err){text('#login-error',err.message);}};
try{const health=await api('health');$('#token-label').hidden=!health.accessTokenRequired;if(state.csrf){try{await ready();}catch{state.csrf=null;$('#login').showModal();}}else $('#login').showModal();}catch(e){text('#status',e.message);}
