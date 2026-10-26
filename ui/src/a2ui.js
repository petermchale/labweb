// Deliberately bounded A2UI v0.9.1 catalog adapter, not a general A2UI runtime.
import {graphComponent, evidencePanel, validateGraph, el} from './graph.js';
const disposers=new WeakMap();
export const catalogId = 'urn:labweb:a2ui:catalog:v1';
export function compose(graph) {
  return [
    {version:'v0.9.1',createSurface:{surfaceId:'labweb-evidence',catalogId}},
    {version:'v0.9.1',updateComponents:{surfaceId:'labweb-evidence',components:[
      {id:'root',component:'Column',children:['graph','evidence']},
      {id:'graph',component:'EvidenceGraph',graph:{path:'/graph'},selection:{path:'/selection'}},
      {id:'evidence',component:'EvidencePanel',graph:{path:'/graph'},selection:{path:'/selection'}}]}},
    {version:'v0.9.1',updateDataModel:{surfaceId:'labweb-evidence',value:{graph,selection:null}}}
  ];
}
export function mountComposition(root, messages, {expand,onSelection}={}) {
  if(!Array.isArray(messages)||messages.length!==3||messages.some(m=>m.version!=='v0.9.1'))throw Error('Unsupported A2UI stream');
  const [create,components,update]=messages;
  const surface=create.createSurface;
  if(surface?.catalogId!==catalogId || components.updateComponents?.surfaceId!==surface.surfaceId || update.updateDataModel?.surfaceId!==surface.surfaceId)throw Error('Unsupported catalog or surface');
  const definitions=components.updateComponents.components;
  // Only this published composition is supported. Unknown code/components/bindings never execute.
  const expected=compose(null)[1].updateComponents.components;
  if(JSON.stringify(definitions)!==JSON.stringify(expected))throw Error('Unsupported component composition');
  const data=validateGraph(update.updateDataModel.value.graph);
  disposers.get(root)?.();root.replaceChildren();const graphRoot=el('section',undefined,root), evidenceRoot=el('section',undefined,root);
  evidenceRoot.setAttribute('aria-live','polite');
  const select=selection=>{evidencePanel(evidenceRoot,data,selection);onSelection?.(selection);};
  disposers.set(root,graphComponent(graphRoot,data,{select,expand}));select(update.updateDataModel.value.selection);
}
