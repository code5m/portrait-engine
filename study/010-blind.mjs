import { METRICS, CONTROLLED, makeTrialPlan, createResponse } from '../src/blind010.mjs';

// Do not expose a result until the browser has rendered and verified BOTH
// original portrait engines with the same locked geometry and lighting.
const metricNames={
  orbit:'Eye socket / gaze naturalness',
  nose:'Nose bridge / alar volume',
  structure:'Cheek / jaw / skull coherence',
  graphite:'Credible graphite pencil marks',
  credibility:'Overall human portrait credibility'
};
const random = new Uint8Array(4);
crypto.getRandomValues(random);
const plan = makeTrialPlan(random);
const sessionId = crypto.randomUUID();
const trials=[];
let trialIndex=0;
const form=document.querySelector('#rating-form');
const host=document.querySelector('#cards');
const next=document.querySelector('#next');
const progress=document.querySelector('#progress');
const status=document.querySelector('#status');

function scoreCard(label) {
  const card=document.createElement('section');
  card.className='card';card.dataset.label=label;
  const title=document.createElement('h2');title.textContent=`Candidate ${label}`;
  const container=document.createElement('div');container.className='preview';
  const frame=document.createElement('iframe');frame.title=`Blind CSS portrait candidate ${label}`;
  frame.tabIndex=-1;frame.referrerPolicy='no-referrer';
  container.append(frame);
  const fieldset=document.createElement('fieldset');
  const legend=document.createElement('legend');legend.textContent=`Candidate ${label}: rate each quality (1 low / 5 high)`;
  fieldset.append(legend);
  for (const metric of METRICS) {
    const row=document.createElement('label');row.className='metric';
    const text=document.createElement('span');text.textContent=metricNames[metric];
    const select=document.createElement('select');select.name=`${label}-${metric}`;select.required=true;
    select.setAttribute('aria-label',`${label}: ${metricNames[metric]}`);
    for (const [value,labelText] of [['','Choose'],...[1,2,3,4,5].map(n=>[String(n),String(n)])]) {
      const option=document.createElement('option');option.value=value;option.textContent=labelText;select.append(option);
    }
    row.append(text,select);fieldset.append(row);
  }
  card.append(title,container,fieldset);
  return card;
}
for(const label of ['A','B'])host.append(scoreCard(label));

function lockFace(frame,scene,variant) {
  const doc=frame.contentDocument;
  if (!doc) throw new Error('Cross-origin iframe: serve this repository over localhost HTTP.');
  const root=doc.querySelector('#portrait');
  if (!root || root.dataset.r009!==variant)throw new Error('Original renderer or requested study variant did not load.');
  for(const [key,val] of Object.entries({...CONTROLLED,lightDirection:scene.lightDirection})) {
    const control=doc.getElementById(`param-${key}`);
    if(!control)throw new Error(`Missing face control: ${key}`);
    control.value=String(val);
    control.dispatchEvent(new Event('input',{bubbles:true}));
    if(Number(control.value)!==val)throw new Error(`Face control not locked: ${key}`);
  }
  if(doc.querySelectorAll('#portrait img,#portrait svg,#portrait canvas').length)
    throw new Error('Not a pure CSS portrait.');
  if(!root.getBoundingClientRect().width)throw new Error('Portrait did not render.');
  frame.dataset.variant=variant;
  frame.dataset.lightDirection=String(scene.lightDirection);
}
function loadCandidate(frame,scene,variant) {
  return new Promise((resolve,reject)=>{
    const timer=setTimeout(()=>{cleanup();reject(new Error('Renderer timed out. Use a local HTTP server.'));},12000);
    function cleanup(){clearTimeout(timer);frame.removeEventListener('load',onLoad);frame.removeEventListener('error',onError);}
    function onLoad(){try{lockFace(frame,scene,variant);cleanup();resolve();}catch(error){cleanup();reject(error);}}
    function onError(){cleanup();reject(new Error('Cannot load the original CSS renderer.'));}
    frame.addEventListener('load',onLoad);frame.addEventListener('error',onError);
    frame.src=`./010-renderer.html?r009=${encodeURIComponent(variant)}&embed=1`;
  });
}
async function draw() {
  const trial=plan[trialIndex];
  next.disabled=true;
  form.reset();
  progress.textContent=`Lighting scene ${trialIndex+1} of ${plan.length} / ${trial.lightDirection} degrees`;
  status.textContent='Loading and locking both CSS portraits...';
  const cards=[...host.querySelectorAll('.card')];
  try {
    await Promise.all(cards.map((card,i)=>loadCandidate(card.querySelector('iframe'),trial,i===0?trial.left:trial.right)));
    status.textContent='Both candidates verified: identical face parameters and lighting. Score independently.';
    next.disabled=false;
  }catch(error){status.textContent=`Study cannot continue: ${error.message}. Try python3 -m http.server 4173 from repository root and visit http://localhost:4173/study/010-blind.html`;}
}
form.addEventListener('submit',event=>{
  event.preventDefault();
  if(!form.reportValidity() || next.disabled)return;
  const data=new FormData(form);
  const scene=plan[trialIndex];
  const candidates=['A','B'].map((label,i)=>({
    label,
    variant:i===0?scene.left:scene.right,
    scores:Object.fromEntries(METRICS.map(m=>[m,Number(data.get(`${label}-${m}`))]))
  }));
  trials.push({sceneId:scene.sceneId,lightDirection:scene.lightDirection,fixed:{...CONTROLLED},
    candidates,preference:data.get('preference')});
  trialIndex++;
  if(trialIndex<plan.length){draw();return;}
  document.querySelector('#experiment').hidden=true;
  document.querySelector('#finished').hidden=false;
});
document.querySelector('#independent').addEventListener('change',event=>{
  document.querySelector('#download').disabled=!event.target.checked;
});
document.querySelector('#download').addEventListener('click',()=>{
  try{
    const response=createResponse({sessionId,trials,independent:document.querySelector('#independent').checked});
    const url=URL.createObjectURL(new Blob([JSON.stringify(response,null,2)+'\n'],{type:'application/json'}));
    const link=document.createElement('a');link.href=url;link.download='portrait-r010-human-evaluation.json';
    document.body.append(link);link.click();link.remove();
    setTimeout(()=>URL.revokeObjectURL(url),1500);
    document.querySelector('#final-status').textContent='Saved on this device only. If you choose, send the JSON to the researcher.';
  }catch(error){document.querySelector('#final-status').textContent=`Cannot export: ${error.message}`;}
});
draw();
