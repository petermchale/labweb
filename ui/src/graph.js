import cytoscape from 'cytoscape';
import dagre from 'cytoscape-dagre';
cytoscape.use(dagre);
// Host-independent graph and evidence components. All KG strings enter textContent.
export function validateGraph(data) {
  if (data?.contract !== 'labkg.graph/v2' || data.component !== 'EvidenceGraph' ||
      !Array.isArray(data.nodes) || !Array.isArray(data.edges) || !data.scope ||
      data.nodes.length > 100 || data.edges.length > 200) throw Error('Unsupported graph contract');
  const ids = new Set(data.nodes.map(n => n.id));
  if (ids.size !== data.nodes.length || data.nodes.some(n => typeof n.id !== 'string' || typeof n.label !== 'string' || !Array.isArray(n.properties))) throw Error('Invalid graph nodes');
  if (data.edges.some(e => !ids.has(e.subject) || !ids.has(e.object) || typeof e.id !== 'string' || typeof e.predicate !== 'string')) throw Error('Invalid graph edges');
  return data;
}
export const short = s => String(s).split(/[\/#]/).pop();
export function el(tag, text, parent) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (parent) parent.append(node);
  return node;
}
export function evidencePanel(root, data, selection) {
  root.replaceChildren();
  el('h2', 'Evidence', root);
  if (!selection) { el('p', 'Select a node or relationship to inspect its source evidence.', root); return; }
  const node = selection.kind === 'node' && data.nodes.find(n => n.id === selection.id);
  const edge = selection.kind === 'edge' && data.edges.find(e => e.id === selection.id);
  el('h3', node ? node.label : edge ? short(edge.predicate) : 'Selection unavailable', root);
  const entries = node ? node.properties : edge ? [edge] : [];
  if (node) el('p', node.id, root);
  if (!entries.length) el('p', 'No property evidence returned for this node. Select a connected relationship.', root);
  for (const entry of entries) {
    const detail = el('details', undefined, root); detail.open = !!edge;
    el('summary', `${short(entry.predicate)} · ${entry.status}`, detail);
    el('p', entry.object, detail);
    el('p', `Source: ${entry.source} · line ${entry.line} · ${entry.method}`, detail);
    el('p', `Revision: ${entry.revision}`, detail);
    el('pre', entry.evidence || 'No quotation supplied.', detail);
  }
}
export function graphComponent(root, data, {select, expand} = {}) {
  validateGraph(data); root.replaceChildren();
  el('h1', 'Evidence subgraph', root);
  const s = data.scope;
  el('p', `${data.nodes.length} nodes · ${data.edges.length} relationships · ${s.project_id || 'All authorized projects'}`, root);
  const scope=el('details',undefined,root);el('summary',s.truncated ? `Limited view: ${s.omitted_nodes} nodes and ${s.omitted_edges} relationships omitted` : 'View scope',scope);
  el('p',`${s.selection}. Depth ${s.depth}.`,scope);
  const controls = el('div', undefined, root); controls.className = 'controls';
  const label = el('label', 'Relationship ', controls), filter = el('select', undefined, label);
  filter.setAttribute('aria-label','Relationship');
  el('option', 'All', filter).value = '';
  [...new Set(data.edges.map(e => e.predicate))].sort().forEach(p => el('option', short(p), filter).value = p);
  const graph = el('div', undefined, root); graph.className = 'graph';
  graph.setAttribute('role','img');graph.setAttribute('aria-label','Interactive evidence graph. Pan, zoom and select nodes or edges; equivalent keyboard controls follow.');
  const list = el('div', undefined, root); list.className = 'relationships';
  let cy;
  const button=(text, action)=>{const b=el('button',text,controls);b.onclick=action;};
  button('Zoom in',()=>cy?.zoom({level:cy.zoom()*1.25,renderedPosition:{x:graph.clientWidth/2,y:graph.clientHeight/2}}));
  button('Zoom out',()=>cy?.zoom({level:cy.zoom()/1.25,renderedPosition:{x:graph.clientWidth/2,y:graph.clientHeight/2}}));
  button('Fit',()=>cy?.fit(undefined,35));
  const color=value=>{const probe=el('span',undefined,root);probe.style.color=value;const result=getComputedStyle(probe).color;probe.remove();return result;};
  function choose(selection){
    cy?.elements().unselect();
    if(selection)cy?.getElementById(selection.id).select();
    select?.(selection);
  }
  function draw(){
    cy?.destroy();graph.replaceChildren();list.replaceChildren();
    const edges=data.edges.filter(e=>!filter.value||e.predicate===filter.value);
    const ids=new Set(edges.flatMap(e=>[e.subject,e.object]));
    const nodes=filter.value?data.nodes.filter(n=>ids.has(n.id)):data.nodes;
    if(!nodes.length){el('p','No matching graph nodes. Try a different query or scope.',graph);return;}
    const text=getComputedStyle(root).color,background=color('Canvas'),accent=color('Highlight');
    cy=cytoscape({container:graph,
      elements:[...nodes.map(n=>({data:{id:n.id,label:n.label}})),...edges.map(e=>({data:{id:e.id,source:e.subject,target:e.object,label:short(e.predicate)}}))],
      layout:{name:'dagre',rankDir:'LR',animate:false,padding:30,nodeSep:45,rankSep:100},
      minZoom:.15,maxZoom:3,wheelSensitivity:.25,
      style:[
        {selector:'node',style:{label:'data(label)',shape:'round-rectangle',width:150,height:48,'background-color':background,'border-color':text,'border-width':1,color:text,'text-valign':'center','text-halign':'center','font-size':13,'text-wrap':'wrap','text-max-width':140}},
        {selector:'edge',style:{label:'data(label)',width:1.5,'curve-style':'bezier','target-arrow-shape':'triangle','line-color':text,'target-arrow-color':text,color:text,'font-size':11,'text-background-color':background,'text-background-opacity':1,'text-background-padding':3,'text-rotation':'none'}},
        {selector:':selected',style:{'border-color':accent,'border-width':3,'line-color':accent,'target-arrow-color':accent}},
      ]});
    cy.on('tap','node',event=>choose({kind:'node',id:event.target.id()}));
    cy.on('tap','edge',event=>choose({kind:'edge',id:event.target.id()}));
    const nodeDetails=el('details',undefined,list);el('summary','Nodes and neighborhood expansion',nodeDetails);
    for(const n of nodes){
      const row=el('div',undefined,nodeDetails);row.className='controls';
      const b=el('button',n.label,row);b.className='node-choice';b.onclick=()=>choose({kind:'node',id:n.id});
      if(expand&&(!s.project_id||n.id.startsWith(`https://labkg.local/id/project/${s.project_id}/`))){const b=el('button','Expand neighborhood',row);b.setAttribute('aria-label',`Expand ${n.label}`);b.onclick=()=>expand(n.id);}
    }
    const edgeLabel=el('label','Inspect relationship ',list),pick=el('select',undefined,edgeLabel);
    el('option','Choose a relationship',pick).value='';
    for(const e of edges)el('option',`${data.nodes.find(n=>n.id===e.subject)?.label} → ${short(e.predicate)} → ${data.nodes.find(n=>n.id===e.object)?.label}`,pick).value=e.id;
    pick.onchange=()=>choose(pick.value?{kind:'edge',id:pick.value}:null);
  }
  filter.onchange=()=>{choose(null);draw();};draw();
  const resize=new ResizeObserver(()=>cy?.resize());resize.observe(graph);
  return ()=>{resize.disconnect();cy?.destroy();};
}
