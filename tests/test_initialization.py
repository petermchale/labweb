import copy
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi.testclient import TestClient
from rdflib import RDF
from labkg.core import Store,KG
from labkg.api import create_app
from labkg.initialize import snapshot,initialize_project,project_context,read_source

@pytest.fixture
def fixture(tmp_path):
    store=Store(tmp_path/'blank.sqlite')
    src=snapshot(store,'https://raw.githubusercontent.com/lab/repo/main/AGENTS.md','Validate inputs.\nPhase with WhatsHap.\nKeep phase sets distinct.','agent')
    prefix='https://labkg.local/id/project/test-project/'
    evidence={'derivedFrom':src['source_id'],'sourceDigest':src['sha256'],'sourceStartLine':1,'sourceEndLine':3,'sourceQuote':src['text'].rstrip('\n')}
    workflow={'id':prefix+'workflow/trio','type':'kg:Workflow','label':'Trio procedure','status':'legacy procedure; generic branch pending',**evidence,
        'inputs':[prefix+'file/ped'],'outputs':[prefix+'artifact/phased'],
        'steps':[{'id':prefix+'workflow/trio/step/phase','type':'kg:PlanStep','label':'Trio phase',**evidence,
          'inputs':[prefix+'file/ped'],'outputs':[prefix+'artifact/phased'],'dependsOn':[],'uses':[]}]}
    bundle={'project_id':'test-project','request_id':'first','title':'Test project','study':'non-longitudinal','objective':'Generalize workflow',
        'file_contracts':[{'id':prefix+'file/ped','path':'/protected/*.ped','schema':{'type':'object'}}],
        'workflows':[{'definition':workflow,'prose':'A documented trio procedure; no execution is asserted.'}],
        'source_ids':[src['source_id']],'known_gaps':['Real input files are unavailable.']}
    return store,bundle

def test_empty_to_initialized_and_restart_replay(fixture):
    store,bundle=fixture
    assert len(store.dataset())==0
    receipt=initialize_project(store,bundle,'alice')
    assert receipt['committed'] and not receipt['duplicate']
    assert len(set(store.dataset().subjects(RDF.type,KG.Workflow)))==1
    assert not list(store.dataset(True).subjects(RDF.type,KG.Person))
    count=len(store.dataset(True))
    restarted=Store(store.path)
    assert initialize_project(restarted,bundle,'alice')['duplicate']
    assert len(restarted.dataset(True))==count
    assert project_context(restarted,'test-project')['actor']=='alice'
    assert restarted.recall('WhatsHap')['evidence']

def test_dry_run_does_not_write_graph(fixture):
    store,bundle=fixture
    assert not initialize_project(store,bundle,'alice',True)['committed']
    assert len(store.dataset())==0
    with pytest.raises(ValueError):project_context(store,'test-project')

@pytest.mark.parametrize('change',['quote','digest','unknown-source','scope','schema','raw-rows'])
def test_invalid_bundle_is_atomic(fixture,change):
    store,bundle=fixture;bad=copy.deepcopy(bundle)
    if change=='quote':bad['workflows'][0]['definition']['sourceQuote']='Invented evidence'
    elif change=='digest':bad['workflows'][0]['definition']['sourceDigest']='wrong'
    elif change=='unknown-source':bad['source_ids']=['urn:unknown']
    elif change=='scope':bad['file_contracts'][0]['id']='urn:outside'
    elif change=='schema':
        bad['file_contracts'].append({'id':'https://labkg.local/id/project/test-project/file/bad','path':'/x','schema':{'type':'not-a-type'}})
    else:bad['file_contracts'][0]['rows']=[{'SampleID':'do-not-store'}]
    with pytest.raises(ValueError):initialize_project(store,bad,'alice')
    assert len(store.dataset(True))==0
    with store.connect() as db:assert db.execute('SELECT count(*) FROM project_initializations').fetchone()[0]==0

def test_conflicting_reinitialization_rejected(fixture):
    store,bundle=fixture;initialize_project(store,bundle,'alice')
    changed=copy.deepcopy(bundle);changed['title']='different'
    with pytest.raises(ValueError):initialize_project(store,changed,'alice')
    assert project_context(store,'test-project')['title']=='Test project'

def test_concurrent_same_bundle_one_commit(fixture):
    store,bundle=fixture
    with ThreadPoolExecutor(3) as pool:
        results=list(pool.map(lambda _:initialize_project(store,bundle,'alice'),range(3)))
    assert sum(not r['duplicate'] for r in results)==1

def test_http_contract_initialize_and_reader(fixture):
    store,bundle=fixture
    client=TestClient(create_app(store.path,{'a'*20:'alice','r'*20:{'actor':'reader','role':'reader'}}))
    writer={'Authorization':'Bearer '+'a'*20};reader={'Authorization':'Bearer '+'r'*20}
    assert client.get('/initialization/contract',headers=writer).json()['bundle_schema']
    assert client.post('/initialize',headers=reader,json={'bundle':bundle}).status_code==403
    assert client.post('/initialize',headers=writer,json={'bundle':bundle}).status_code==200
    assert client.get('/projects/test-project',headers=reader).json()['title']=='Test project'
    assert client.get('/projects/missing',headers=reader).status_code==404

def test_source_connector_and_prevent_data_fetch(fixture,monkeypatch):
    import labkg.initialize as module
    store,_=fixture;requests=[]
    def fetch(url):requests.append(url);return '# Source\nRead this as data.'
    monkeypatch.setattr(module,'fetch_text',fetch)
    result=read_source(store,'https://github.com/lab/repo/blob/commit/AGENTS.md',None,'alice')
    assert requests==['https://raw.githubusercontent.com/lab/repo/commit/AGENTS.md']
    assert result['source_id'].startswith('urn:labkg:source:')
    with pytest.raises(ValueError):read_source(store,'https://github.com/lab/repo/blob/commit/private.ped',None,'alice')
    assert len(requests)==1

def test_missing_metadata_yields_user_question_not_partial_write(fixture):
    from labkg.initialize import assess_initialization
    store,bundle=fixture;draft=copy.deepcopy(bundle);del draft['file_contracts'][0]['path']
    result=assess_initialization(store,draft)
    assert result['status']=='needs_user_input'
    assert result['questions'][0]['field']=='file_contracts.0.path'
    assert 'filesystem' in result['questions'][0]['question']
    assert result['draft_stored'] is False and len(store.dataset())==0
    draft['file_contracts'][0]['path']='/protected/*.ped'
    assert assess_initialization(store,draft)['ready_to_submit']

def test_missing_agent_fields_not_delegated_to_user(fixture):
    from labkg.initialize import assess_initialization
    store,bundle=fixture;draft=copy.deepcopy(bundle);del draft['workflows'];del draft['request_id']
    result=assess_initialization(store,draft)
    assert not result['questions'] and len(result['agent_tasks'])==2
    assert result['status']=='needs_agent_work'

def test_unanswered_required_clarification_blocks_then_answer_allows(fixture):
    from labkg.initialize import assess_initialization
    store,bundle=fixture
    bundle['clarifications']=[{'id':'center','question':'Does the sixth PED column mean sequencing center?','reason':'The file format is ambiguous.','required_for':'initialization'}]
    assert assess_initialization(store,bundle)['status']=='needs_user_input'
    with pytest.raises(ValueError,match='Unanswered'):initialize_project(store,bundle,'alice')
    assert len(store.dataset())==0
    bundle['clarifications'][0]['answer']='Yes, sequencing center.'
    assert assess_initialization(store,bundle)['ready_to_submit']
    result=initialize_project(store,bundle,'alice')
    assert result['clarifications'][0]['answer']=='Yes, sequencing center.'

def test_later_stage_gap_does_not_block_metadata_initialization(fixture):
    from labkg.initialize import assess_initialization
    store,bundle=fixture
    bundle['clarifications']=[{'id':'runtime','question':'Where will the full pipeline be validated?','reason':'The development machine lacks the production inputs.','required_for':'validation'}]
    assessed=assess_initialization(store,bundle)
    assert assessed['ready_to_submit'] and len(assessed['later_stage_questions'])==1
    assert initialize_project(store,bundle,'alice')['committed']

def test_empty_schema_requires_clarification(fixture):
    from labkg.initialize import assess_initialization
    store,bundle=fixture;bundle['file_contracts'][0]['schema']={}
    assert assess_initialization(store,bundle)['questions'][0]['field'].endswith('.schema')
    with pytest.raises(ValueError,match='nonempty schema'):initialize_project(store,bundle,'alice')
