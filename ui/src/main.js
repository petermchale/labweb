import {App, applyDocumentTheme, applyHostStyleVariables} from '@modelcontextprotocol/ext-apps';
import {compose,mountComposition,inspectComposition,defaultComponents} from './a2ui.js';
import {el} from './graph.js';
import './style.css';
const root=document.getElementById('labweb'), status=document.getElementById('status');
let current, requestGraph, selectedComponents=defaultComponents;
function fail(error){status.textContent=String(error.message||error);status.setAttribute('role','alert');}
function show(result){
  const messages=Array.isArray(result)?result:result?.contract==='labkg.view/v1'?result.a2ui:compose(result,selectedComponents);
  const {data,components}=inspectComposition(messages);
  mountComposition(root,messages,{expand:requestGraph?async id=>{
    const s=current.scope;
    status.textContent='Loading neighborhood…';
    try{show(await requestGraph({query:s.query,project_id:s.project_id,focus:id,depth:Math.min(3,s.depth+1),max_nodes:s.max_nodes,max_edges:s.max_edges,predicates:s.predicates,components:selectedComponents}));}catch(e){fail(e);}
  }:undefined});
  current=data;selectedComponents=components;status.textContent='';status.removeAttribute('role');
}
function unpack(result){
  if(result.isError)throw Error(result.content?.find(c=>c.type==='text')?.text||'Graph request failed');
  if(result.structuredContent?.contract)return result.structuredContent;
  for(const item of result.content||[])if(item.type==='text'){try{const d=JSON.parse(item.text);if(d.contract)return d;}catch{}}
  throw Error('No graph data in tool result');
}
const initial=document.getElementById('labkg-data');
if(initial && initial.textContent.trim()!=='null'){
  try{show(JSON.parse(initial.textContent));}catch(e){fail(e);}
}else if(window.parent!==window){
  const app=new App({name:'Labweb EvidenceGraph',version:'0.2.0'});
  // Inline tool results can be collapsed by the host. Prefer a visible viewer,
  // but let hosts without fullscreen support keep their normal inline display.
  let presented=false;
  async function present(){
    const context=app.getHostContext();
    if(presented || !current || !context)return;
    presented=true;
    if(context.displayMode==='inline' && context.availableDisplayModes?.includes('fullscreen')){
      try{await app.requestDisplayMode({mode:'fullscreen'});}catch{/* Inline remains usable if the host declines. */}
    }
  }
  requestGraph=async args=>unpack(await app.callServerTool({name:'graph_view',arguments:args}));
  app.ontoolresult=result=>{try{show(unpack(result));void present();}catch(e){fail(e);}};
  app.onerror=fail;
  app.onhostcontextchanged=ctx=>{if(ctx.theme)applyDocumentTheme(ctx.theme);if(ctx.styles?.variables)applyHostStyleVariables(ctx.styles.variables);};
  app.connect().then(present).catch(fail);
}else{
  // Browser fallback: credentials remain in this page's memory, never a URL or storage.
  const form=el('form',undefined,root);form.className='controls';
  const input=(name,type='text')=>{const label=el('label',name,form),i=el('input',undefined,label);i.type=type;return i;};
  const token=input('Access token','password');token.autocomplete='off';token.required=true;
  const project=input('Project ID'); const query=input('Query');
  const submit=el('button','Show subgraph',form);submit.type='submit';
  form.onsubmit=async event=>{
    event.preventDefault();const credential=token.value;
    requestGraph=async args=>{const response=await fetch('/view/a2ui',{method:'POST',headers:{'Content-Type':'application/json',Authorization:`Bearer ${credential}`},body:JSON.stringify(args)});if(!response.ok)throw Error(`Graph request failed (${response.status})`);return (await response.text()).trim().split('\n').map(JSON.parse);};
    try{show(await requestGraph({query:query.value,project_id:project.value||null}));}catch(e){fail(e);}
  };
}
