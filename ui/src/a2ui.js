// Bounded A2UI v0.9.1 catalog adapter. Only maintained components may execute.
import {graphComponent, evidencePanel, validateGraph, el} from './graph.js';
const disposers=new WeakMap();
export const catalogId = 'urn:labweb:a2ui:catalog:v1';
export const defaultComponents = ['EvidenceGraph','EvidencePanel'];
const componentIds={EvidenceGraph:'graph',EvidencePanel:'evidence'};
function choices(components){
  if(!Array.isArray(components)||!components.length||components.length>2||new Set(components).size!==components.length||components.some(c=>!Object.hasOwn(componentIds,c)))throw Error('Unsupported component choices');
  return components;
}
export function compose(graph, components=defaultComponents) {
  choices(components);
  return [
    {version:'v0.9.1',createSurface:{surfaceId:'labweb-evidence',catalogId}},
    {version:'v0.9.1',updateComponents:{surfaceId:'labweb-evidence',components:[
      {id:'root',component:'Column',children:components.map(c=>componentIds[c])},
      ...components.map(component=>({id:componentIds[component],component,graph:{path:'/graph'},selection:{path:'/selection'}}))]}},
    {version:'v0.9.1',updateDataModel:{surfaceId:'labweb-evidence',value:{graph,selection:null}}}
  ];
}
// Compare objects independently of JSON key order; reject extra props and bindings.
function same(a,b){
  if(a===b)return true;
  if(!a||!b||typeof a!=='object'||typeof b!=='object'||Array.isArray(a)!==Array.isArray(b))return false;
  const keys=Object.keys(a);
  return keys.length===Object.keys(b).length&&keys.every(k=>Object.hasOwn(b,k)&&same(a[k],b[k]));
}
export function inspectComposition(messages){
  if(!Array.isArray(messages)||messages.length!==3||messages.some(m=>m.version!=='v0.9.1'))throw Error('Unsupported A2UI stream');
  const [create,components,update]=messages;
  const surface=create.createSurface;
  if(!surface?.surfaceId||surface.catalogId!==catalogId || components.updateComponents?.surfaceId!==surface.surfaceId || update.updateDataModel?.surfaceId!==surface.surfaceId)throw Error('Unsupported catalog or surface');
  const definitions=components.updateComponents.components;
  if(!Array.isArray(definitions))throw Error('Unsupported component composition');
  const byId=new Map(definitions.map(d=>[d.id,d]));
  const root=byId.get('root');
  if(!Array.isArray(root?.children))throw Error('Unsupported component composition');
  const selected=choices(root.children.map(id=>byId.get(id)?.component));
  const expected=compose(null,selected)[1].updateComponents.components;
  if(definitions.length!==expected.length||new Set(definitions.map(d=>d.id)).size!==definitions.length||expected.some(d=>!same(d,byId.get(d.id))))throw Error('Unsupported component composition');
  if(update.updateDataModel.path!==undefined&&update.updateDataModel.path!=='/')throw Error('Unsupported data binding');
  const data=validateGraph(update.updateDataModel.value.graph);
  const selection=update.updateDataModel.value.selection;
  if(selection!==null&&(!selection||!['node','edge'].includes(selection.kind)||!(selection.kind==='node'?data.nodes:data.edges).some(item=>item.id===selection.id)))throw Error('Invalid selection');
  return {data,components:selected,selection};
}
export function mountComposition(root, messages, {expand,onSelection}={}) {
  // Validate everything before replacing the current view.
  const {data,components,selection}=inspectComposition(messages);
  disposers.get(root)?.();root.replaceChildren();
  const roots=new Map(components.map(c=>[c,el('section',undefined,root)]));
  const evidenceRoot=roots.get('EvidencePanel');
  let panel=evidenceRoot;
  if(evidenceRoot){
    evidenceRoot.setAttribute('aria-live','polite');
    // An evidence-only view still needs a way to inspect every returned item.
    if(!roots.has('EvidenceGraph')){
      const label=el('label','Evidence item ',evidenceRoot), picker=el('select',undefined,label);
      el('option','Choose a node or relationship',picker).value='';
      const items=[...data.nodes.map(n=>({selection:{kind:'node',id:n.id},label:n.label})),...data.edges.map(e=>({selection:{kind:'edge',id:e.id},label:`${data.nodes.find(n=>n.id===e.subject)?.label} → ${e.predicate.split(/[\/#]/).pop()} → ${data.nodes.find(n=>n.id===e.object)?.label}`}))];
      items.forEach((item,i)=>{el('option',item.label,picker).value=String(i);});
      if(selection)picker.value=String(items.findIndex(item=>same(item.selection,selection)));
      picker.onchange=()=>select(picker.value===''?null:items[Number(picker.value)].selection);
      panel=el('div',undefined,evidenceRoot);
    }
  }
  const select=value=>{if(panel)evidencePanel(panel,data,value);onSelection?.(value);};
  const graphRoot=roots.get('EvidenceGraph');
  if(graphRoot)disposers.set(root,graphComponent(graphRoot,data,{select,expand}));
  else disposers.delete(root);
  select(selection);
}
