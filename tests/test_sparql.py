import pytest
from labkg.core import Store
from labkg.sparql import execute,validate_query

@pytest.mark.parametrize('query',[
 'SELECT * WHERE { SERVICE <https://example.com> { ?s ?p ?o } }',
 'SELECT * FROM <file:///etc/passwd> WHERE { ?s ?p ?o }',
 'INSERT DATA { <urn:a> <urn:b> <urn:c> }',
 'SELECT * WHERE { { SELECT * WHERE { SERVICE SILENT <https://example.com> { ?s ?p ?o } } } }'
])
def test_reject_external_and_writes(query):
    with pytest.raises(Exception): validate_query(query)

def test_standard_select_ask(tmp_path):
    store=Store(tmp_path/'query.sqlite');store.ingest('urn:q','ped','F A 0 0 1 UW',evidence_status='synthetic')
    answer=execute(store,'SELECT ?p WHERE { ?p a <https://labkg.local/vocab/Person> }')
    assert len(answer['results']['bindings'])==1
    assert answer['results']['bindings'][0]['p']['type']=='uri'
    assert execute(store,'ASK { ?s ?p ?o }')['boolean']
    with pytest.raises(TimeoutError): execute(store,'SELECT * WHERE {?s ?p ?o}',timeout=0)
