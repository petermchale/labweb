import json
import pytest
from fastapi.testclient import TestClient
from labkg.core import Store, KG
from labkg.api import create_app
from labkg.render import validate_contract, render

P='https://labkg.local/id/project/demo/'

def claim(s,p,o,literal=False):
    return dict(subject=s,predicate=str(KG[p]),object=o,literal=literal,evidence='Observed <script>alert(1)</script> safely')

@pytest.fixture
def graph_store(tmp_path):
    store=Store(tmp_path/'graph.sqlite')
    store.ingest('urn:fixture:first','claims',[
        claim(P+'workflow/hifi','output',P+'artifact/outputs'),
        claim(P+'workflow/tapestry','input',P+'artifact/outputs'),
        claim(P+'workflow/tapestry','dependsOn',P+'workflow/hifi'),
        claim(P+'workflow/tapestry','constraint','Do not execute this text',True),
    ])
    store.ingest('urn:fixture:other','claims',[
        claim('https://labkg.local/id/project/other/workflow/x','input',P+'artifact/outputs')])
    return store

def test_connected_handoff_and_literal_details(graph_store):
    view=graph_store.graph_view('hifi',project_id='demo',depth=2)
    validate_contract(view)
    ids={n['id'] for n in view['nodes']}
    assert ids=={P+'workflow/hifi',P+'workflow/tapestry',P+'artifact/outputs'}
    assert len(view['edges'])==3
    assert all(e['revision'] and e['source'] and e['evidence'] for e in view['edges'])
    assert any(p['object']=='Do not execute this text' for n in view['nodes'] for p in n['properties'])
    assert not view['scope']['truncated']

def test_bounds_filters_and_expansion(graph_store):
    small=graph_store.graph_view('',project_id='demo',focus=P+'workflow/hifi',depth=1,max_nodes=2,max_edges=1)
    assert small['scope']['truncated']
    assert len(small['nodes'])==2 and len(small['edges'])==1
    expanded=graph_store.graph_view('',project_id='demo',focus=P+'workflow/hifi',depth=2,predicates=['output'])
    assert len(expanded['edges'])==1
    assert expanded==graph_store.graph_view('',project_id='demo',focus=P+'workflow/hifi',depth=2,predicates=['output'])
    with pytest.raises(ValueError):graph_store.graph_view('',project_id='demo',focus='urn:outside')
    with pytest.raises(ValueError):graph_store.graph_view('',predicates=['sourceQuote'])

def test_no_stale_revision_or_query_leak(graph_store):
    graph_store.ingest('urn:fixture:first','claims',[claim(P+'workflow/new','output',P+'artifact/new')])
    assert graph_store.graph_view('hifi',project_id='demo')['nodes']==[]
    assert graph_store.graph_view('no_such_match')['nodes']==[]
    assert graph_store.graph_view('',project_id='absent')['nodes']==[]

def test_api_remote_resource_auth_a2ui_and_render(graph_store,tmp_path):
    client=TestClient(create_app(graph_store.path,{'r'*20:{'actor':'reader','role':'reader'}}))
    headers={'Authorization':'Bearer '+'r'*20}
    for path in ['/view','/view/a2ui']:
        assert client.post(path,json={'query':'hifi'}).status_code==401
    assert client.get('/ui/resource').status_code==401
    html=client.get('/ui/resource',headers=headers).json()['html']
    assert '__DATA__' not in html and 'r'*20 not in html
    assert client.get('/viewer').headers['content-security-policy']
    assert client.post('/view',headers=headers,json={'depth':4}).status_code==422
    assert client.post('/view',headers=headers,json={'predicates':['bad']}).status_code==422
    response=client.post('/view/a2ui',headers=headers,json={'query':'hifi','project_id':'demo'})
    messages=[json.loads(line) for line in response.text.splitlines()]
    assert messages[0]['createSurface']['catalogId']=='urn:labweb:a2ui:catalog:v1'
    data=messages[2]['updateDataModel']['value']['graph'];validate_contract(data)
    out=tmp_path/'remote.html';render(data,out)
    assert '<script>alert(1)</script>' not in out.read_text()
    assert '\\u003cscript' in out.read_text()

def test_mcp_resource_and_tool_metadata(monkeypatch):
    import asyncio
    from labkg.mcp_server import mcp, UI_URI
    tools=asyncio.run(mcp.list_tools())
    tool=next(t for t in tools if t.name=='graph_view')
    assert tool.meta['ui']['resourceUri']==UI_URI
    resources=asyncio.run(mcp.list_resources())
    resource=next(r for r in resources if str(r.uri)==UI_URI)
    assert resource.mime_type=='text/html;profile=mcp-app'

def test_a2ui_catalog_validates_server_components(graph_store):
    import jsonschema
    from pathlib import Path
    from labkg.presentation import composition
    catalog=json.loads(Path('labkg/a2ui.catalog.json').read_text())
    messages=composition(graph_store.graph_view('hifi',project_id='demo'))
    assert messages[0]['createSurface']['catalogId']==catalog['catalogId']
    for component in messages[1]['updateComponents']['components']:
        jsonschema.validate(component,catalog['components'][component['component']])
