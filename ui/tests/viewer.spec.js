import {test,expect} from '@playwright/test';
const base='http://127.0.0.1:8779';
test('packaged standalone graph selects evidence without source execution',async({page})=>{
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(base+'/fixture');
  await expect(page.getByRole('heading',{name:'Evidence subgraph'})).toBeVisible();
  await expect(page.locator('.node-choice')).toHaveCount(3);
  await page.getByLabel('Inspect relationship').selectOption({index:1});
  await expect(page.locator('pre')).toContainText('Synthetic');
  expect(await page.evaluate(()=>window.injected)).toBeUndefined();
  await page.getByLabel('Relationship',{exact:true}).selectOption({label:'output'});
  await expect(page.locator('.node-choice')).toHaveCount(2);
  await page.getByLabel('Inspect relationship').selectOption({index:1});
  expect(errors).toEqual([]);
  await page.screenshot({path:'test-results/evidence-subgraph.png',fullPage:true});
});
test('remote browser fallback authenticates and expands without local files',async({page})=>{
  await page.setViewportSize({width:390,height:844});
  await page.goto(base+'/viewer');
  await page.getByLabel('Access token').fill('synthetic-browser-token');
  await page.getByLabel('Project ID').fill('demo');
  await page.getByLabel('Query',{exact:true}).fill('hifi');
  await page.getByRole('button',{name:'Show subgraph'}).click();
  await expect(page.locator('.node-choice')).toHaveCount(2);
  await page.getByText('Nodes and neighborhood expansion',{exact:true}).click();
  await page.getByRole('button',{name:'Expand outputs',exact:true}).click();
  await expect(page.locator('.node-choice')).toHaveCount(3);
  expect(await page.evaluate(()=>localStorage.length)).toBe(0);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
});
test('MCP App handshake, tool result and expansion through host',async({page})=>{
  await page.goto(base+'/host');
  const frame=page.frameLocator('#app');
  await expect(frame.locator('.node-choice')).toHaveCount(2);
  await expect.poll(()=>page.evaluate(()=>window.displayMode)).toBe('fullscreen');
  await frame.getByText('Nodes and neighborhood expansion',{exact:true}).press('Enter');
  await frame.getByRole('button',{name:'Expand outputs',exact:true}).press('Enter');
  await expect(frame.locator('.node-choice')).toHaveCount(3);
  const methods=await page.evaluate(()=>window.messages);
  expect(methods).toContain('ui/initialize');
  expect(methods).toContain('tools/call');
  expect(methods.filter(m=>m==='ui/request-display-mode')).toHaveLength(1);
});
for(const mode of ['inline-only','decline'])test(`MCP App remains usable when host is ${mode}`,async({page})=>{
  await page.goto(base+'/host?'+mode);
  const frame=page.frameLocator('#app');
  await expect(frame.locator('.node-choice')).toHaveCount(2);
  await frame.getByLabel('Inspect relationship').selectOption({index:1});
  await expect(frame.locator('pre')).toContainText('Synthetic');
  if(mode==='inline-only')expect(await page.evaluate(()=>window.messages)).not.toContain('ui/request-display-mode');
  else await expect.poll(()=>page.evaluate(()=>window.messages.includes('ui/request-display-mode'))).toBe(true);
});
test('server A2UI stream uses the same components and rejects unknown catalog',async({page})=>{
  await page.goto(base+'/composition-test');
  const rejected=await page.evaluate(async()=>{
    const {mountComposition}=await import('/test-modules/a2ui.js');
    const response=await fetch('/view/a2ui',{method:'POST',headers:{Authorization:'Bearer synthetic-browser-token','Content-Type':'application/json'},body:JSON.stringify({query:'hifi',project_id:'demo',depth:2})});
    const messages=(await response.text()).trim().split('\n').map(JSON.parse);
    mountComposition(document.getElementById('labweb'),messages);
    const bad=structuredClone(messages);bad[0].createSurface.catalogId='urn:untrusted:catalog';
    try{mountComposition(document.createElement('div'),bad);return false;}catch{return true;}
  });
  expect(rejected).toBe(true);
  await expect(page.locator('.node-choice')).toHaveCount(3);
  await page.getByLabel('Inspect relationship').selectOption({index:2});
  await expect(page.locator('pre')).toContainText('<script>window.injected=true</script>');
  expect(await page.evaluate(()=>window.injected)).toBeUndefined();
});
for(const mode of ['graph-only','evidence-only','evidence-first'])test(`MCP renders requested components: ${mode}`,async({page})=>{
  await page.goto(base+'/host?'+mode);
  const frame=page.frameLocator('#app');
  if(mode==='evidence-only'){
    await expect(frame.getByRole('heading',{name:'Evidence',exact:true})).toBeVisible();
    await expect(frame.locator('.graph')).toHaveCount(0);
    await frame.getByLabel('Evidence item').selectOption({index:3});
    await expect(frame.locator('pre')).toContainText('Synthetic');
  }else{
    await expect(frame.locator('.node-choice')).toHaveCount(2);
    await expect(frame.getByRole('heading',{name:'Evidence',exact:true})).toHaveCount(mode==='graph-only'?0:1);
    if(mode==='evidence-first')await expect(frame.locator('#labweb > section').first().getByRole('heading',{name:'Evidence',exact:true})).toBeVisible();
    await frame.getByText('Nodes and neighborhood expansion',{exact:true}).press('Enter');
    await frame.getByRole('button',{name:'Expand outputs',exact:true}).press('Enter');
    await expect(frame.locator('.node-choice')).toHaveCount(3);
    expect(await page.evaluate(()=>window.toolArguments[0].components)).toEqual(mode==='graph-only'?['EvidenceGraph']:['EvidencePanel','EvidenceGraph']);
    await expect(frame.getByRole('heading',{name:'Evidence',exact:true})).toHaveCount(mode==='graph-only'?0:1);
  }
  expect(await page.evaluate(()=>window.injected)).toBeUndefined();
});
test('invalid compositions leave the existing surface intact',async({page})=>{
  await page.goto(base+'/composition-test');
  const results=await page.evaluate(async()=>{
    const {mountComposition,compose}=await import('/test-modules/a2ui.js');
    const graph=await fetch('/view',{method:'POST',headers:{Authorization:'Bearer synthetic-browser-token','Content-Type':'application/json'},body:JSON.stringify({query:'hifi',project_id:'demo'})}).then(r=>r.json());
    const root=document.getElementById('labweb');mountComposition(root,compose(graph));
    const original=root.firstChild;
    const edits=[
      m=>m[1].updateComponents.components[1].component='Script',
      m=>m[1].updateComponents.components[0].children=['graph','graph'],
      m=>m[1].updateComponents.components.push({id:'orphan',component:'EvidencePanel'}),
      m=>m[1].updateComponents.components[1].graph.path='/untrusted',
      m=>m[1].updateComponents.surfaceId='other',
      m=>m[2].updateDataModel.value.graph.edges[0].subject='missing',
    ];
    return edits.map(edit=>{const messages=compose(graph);edit(messages);try{mountComposition(root,messages);return false;}catch{return root.firstChild===original;}});
  });
  expect(results).toEqual(Array(6).fill(true));
  await expect(page.locator('.node-choice')).toHaveCount(2);
});
