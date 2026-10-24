"""Read-only, local-dataset SPARQL with a hard worker deadline."""
import itertools
import json
import multiprocessing
from rdflib import Dataset,Literal,URIRef,BNode
from rdflib.plugins.sparql.parser import parseQuery
from pyparsing import ParseResults

def _check(node):
    if getattr(node,'name',None) in {'ServiceGraphPattern','DatasetClause'}:
        raise ValueError('Federation and external datasets are disabled')
    if isinstance(node,dict):
        for value in node.values(): _check(value)
    elif isinstance(node,(list,tuple,ParseResults)):
        for value in node: _check(value)

def validate_query(query):
    if len(query)>10000: raise ValueError('Query exceeds 10 KB')
    parsed=parseQuery(query)
    if parsed[1].name not in {'SelectQuery','AskQuery'}: raise ValueError('Only SELECT and ASK are supported')
    _check(parsed)

def _term(term):
    if isinstance(term,URIRef): return {'type':'uri','value':str(term)}
    if isinstance(term,BNode): return {'type':'bnode','value':str(term)}
    value={'type':'literal','value':str(term)}
    if term.language: value['xml:lang']=term.language
    elif term.datatype: value['datatype']=str(term.datatype)
    return value

def _worker(data,query,connection):
    try:
        validate_query(query)
        ds=Dataset(default_union=True);ds.parse(data=data,format='nquads')
        result=ds.query(query)
        if result.type=='ASK': output={'head':{},'boolean':bool(result.askAnswer)}
        else:
            rows=list(itertools.islice(result,1001))
            if len(rows)>1000: raise ValueError('More than 1000 results; add a LIMIT')
            output={'head':{'vars':[str(x) for x in result.vars]},'results':{'bindings':[{str(k):_term(v) for k,v in row.asdict().items()} for row in rows]}}
        encoded=json.dumps(output)
        if len(encoded)>2_000_000: raise ValueError('Result exceeds 2 MB')
        connection.send({'ok':output})
    except Exception as e: connection.send({'error':str(e)})
    finally: connection.close()

def execute(store,query,timeout=5):
    # Child handles parsing and evaluation; neither may block the server indefinitely.
    data=store.dataset().serialize(format='nquads')
    ctx=multiprocessing.get_context('spawn');parent,child=ctx.Pipe(duplex=False)
    process=ctx.Process(target=_worker,args=(data,query,child));process.start();child.close()
    try:
        if not parent.poll(timeout): raise TimeoutError('SPARQL deadline exceeded')
        result=parent.recv()
        if 'error' in result: raise ValueError(result['error'])
        return result['ok']
    finally:
        if process.is_alive(): process.terminate()
        process.join();parent.close()
