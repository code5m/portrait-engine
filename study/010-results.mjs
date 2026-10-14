import { summarize } from '../src/blind010.mjs';
const input=document.querySelector('#files');
const text=document.querySelector('#summary');
const status=document.querySelector('#status');
const download=document.querySelector('#download');
let last=null;
document.querySelector('#analyze').addEventListener('click',async()=>{
  const files=[...input.files];
  if(files.length>500){status.textContent='Limit: 500 files';return;}
  const parsed=[];
  for(const file of files){
    if(file.size>128*1024){parsed.push({fileTooLarge:true});continue;}
    try{parsed.push(JSON.parse(await file.text()));}
    catch{parsed.push({invalidJSON:true});}
  }
  last=summarize(parsed);
  text.textContent=JSON.stringify(last,null,2);
  status.textContent=`Read ${files.length} files locally. Accepted ${last.evaluatedSessions}; excluded ${last.rejectedCount}. Human identity/independence cannot be technically verified.`;
  download.disabled=false;
});
download.addEventListener('click',()=>{
  if(!last)return;
  const url=URL.createObjectURL(new Blob([JSON.stringify(last,null,2)+'\n'],{type:'application/json'}));
  const a=document.createElement('a');a.href=url;a.download='portrait-r010-aggregate-only.json';document.body.append(a);a.click();a.remove();
  setTimeout(()=>URL.revokeObjectURL(url),1500);
});
