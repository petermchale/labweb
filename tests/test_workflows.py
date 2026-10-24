import json
from pathlib import Path
import pytest
from rdflib import RDF,URIRef
from labkg.core import Store,KG
from labkg.workflows import parse_note
ROOT=Path(__file__).resolve().parents[1]

@pytest.fixture
def store(tmp_path): return Store(tmp_path/'metadata.sqlite')

def test_metadata_only_contracts(store):
    for name in ['manifest','ped']:
        data=json.loads((ROOT/'knowledge/contracts'/f'{name}.json').read_text())
        store.ingest('urn:contract:'+name,'file_contract',data)
    g=store.dataset()
    assert len(list(g.subjects(RDF.type,KG.FileContract)))==2
    assert not list(g.subjects(RDF.type,KG.Person))
    assert not list(g.subjects(RDF.type,KG.UnalignedBAM))
    assert not list(g.triples((None,KG.sample,None)))
    assert len(list(g.objects(None,KG.path)))==2
    assert len(list(g.objects(None,KG.schema)))==2
    with pytest.raises(ValueError):store.ingest('urn:raw','ped','F A 0 0 1 UW')
    with pytest.raises(ValueError):store.ingest('urn:raw','manifest',{'A,UW':['/a.bam']})
    with pytest.raises(ValueError):store.ingest('urn:bad','file_contract',{'path':'/a','schema':{},'rows':[1]})

def test_purge_removes_history_and_search(store):
    for body in ['F SENSITIVE_OLD 0 0 1 UW','F SENSITIVE_NEW 0 0 1 UW']:
        store.ingest('urn:retire','ped',body,evidence_status='synthetic')
    store.ingest('urn:keep','text','Keep workflow documentation')
    result=store.purge_sources(['urn:retire'])
    assert result['revisions_removed']==2
    assert 'SENSITIVE' not in store.dataset(True).serialize(format='trig')
    assert not store.recall('SENSITIVE_OLD SENSITIVE_NEW')['evidence']
    with store.connect() as db:
        assert db.execute("SELECT count(*) FROM revisions WHERE source='urn:retire'").fetchone()[0]==0
        assert db.execute("SELECT count(*) FROM chunks WHERE source='urn:retire'").fetchone()[0]==0
    assert store.recall('documentation')['evidence']

def test_workflow_graph_and_handoff(store):
    notes=list((ROOT/'knowledge/workflows').glob('*.md'))
    assert len(notes)==6
    for path in notes:
        data,body,g=parse_note(path.read_text())
        assert body.strip()
        store.ingest('urn:note:'+path.name,'workflow',path.read_text())
    ds=store.dataset()
    assert len(set(ds.subjects(RDF.type,KG.Workflow)))==6
    assert len(set(ds.subjects(RDF.type,KG.PlanStep)))==22
    answer=list(ds.query('''PREFIX kg:<https://labkg.local/vocab/>
        SELECT DISTINCT ?upstream ?downstream ?handoff WHERE {
          ?upstream a kg:Workflow; kg:output ?handoff.
          ?downstream a kg:Workflow; kg:input ?handoff.
          FILTER(?upstream != ?downstream)
        }'''))
    assert any(str(a).endswith('/hifi-wdl') and str(b).endswith('/pedigree-nextflow') and str(c).endswith('/miniwdl-outputs-json') for a,b,c in answer)
    trio=URIRef('https://labkg.local/id/workflow/trio-legacy')
    assert 'not generic' in str(ds.value(trio,KG.implementationStatus))
    assert len(list(ds.objects(trio,KG.hasStep)))==4
    assert not list(ds.subjects(RDF.type,KG.Person))

def test_invalid_notes_fail_closed():
    text=(ROOT/'knowledge/workflows/trio-legacy.md').read_text()
    with pytest.raises(ValueError):parse_note(text.replace('type: kg:Workflow','type: kg:Workflow\n"@context": https://evil.example/context'))
    with pytest.raises(ValueError):parse_note(text.replace('type: kg:Workflow','type: kg:Workflow\ntype: kg:Workflow'))
    import yaml
    front,body=text[4:].split('\n---\n',1);data=yaml.safe_load(front)
    data['steps'][0]['dependsOn']=[data['steps'][-1]['id']]
    with pytest.raises(ValueError):parse_note('---\n'+yaml.safe_dump(data)+'---\n'+body)
