"""A bounded YAML-LD/Markdown workflow profile inspired by Vault-LD.

The context is bundled, local and fixed. No remote contexts, wiki-link
resolution, ontology inference or general Vault-LD round-trip is claimed.
"""
import json
from pathlib import Path
import yaml
from rdflib import Graph,URIRef,RDF

CONTEXT=json.loads(Path(__file__).with_name('workflow-context.jsonld').read_text())['@context']
KG='https://labkg.local/vocab/'

class UniqueLoader(yaml.SafeLoader): pass

def unique_mapping(loader,node,deep=False):
    result={}
    for key,value in node.value:
        k=loader.construct_object(key,deep=deep)
        if k in result: raise ValueError('Duplicate YAML key')
        result[k]=loader.construct_object(value,deep=deep)
    return result
UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,unique_mapping)

def parse_note(text):
    if not text.startswith('---\n') or '\n---\n' not in text[4:]:
        raise ValueError('Workflow note needs YAML frontmatter and Markdown body')
    front,body=text[4:].split('\n---\n',1)
    if any(isinstance(t,(yaml.tokens.AnchorToken,yaml.tokens.AliasToken)) for t in yaml.scan(front)):
        raise ValueError('YAML aliases/anchors are not supported')
    data=yaml.load(front,Loader=UniqueLoader)
    if not isinstance(data,dict): raise ValueError('Expected workflow mapping')
    def check(node,depth=0):
        if depth>10: raise ValueError('Workflow nesting exceeds limit')
        if isinstance(node,dict):
            if set(node)-set(CONTEXT): raise ValueError('Unknown field or external context in workflow')
            for value in node.values():check(value,depth+1)
        elif isinstance(node,list):
            for value in node:check(value,depth+1)
        elif not isinstance(node,(str,int,float,bool)):
            raise ValueError('Use explicit scalar values')
    check(data)
    from .core import iri
    iri(data.get('id'))
    if data.get('type')!='kg:Workflow': raise ValueError('Expected kg:Workflow')
    steps=data.get('steps',[])
    if not isinstance(steps,list) or not steps or len(steps)>50: raise ValueError('Expected 1–50 steps')
    ids=[step.get('id') for step in steps]
    if len(set(ids))!=len(ids): raise ValueError('Duplicate step identity')
    required={'label','derivedFrom','sourceDigest','sourceStartLine','sourceEndLine','sourceQuote'}
    for node in [data,*steps]:
        iri(node.get('id'))
        if not required<=set(node): raise ValueError('Every workflow and step requires source evidence')
        iri(node['derivedFrom'])
        if not isinstance(node['sourceStartLine'],int) or not isinstance(node['sourceEndLine'],int) or not 1<=node['sourceStartLine']<=node['sourceEndLine']:
            raise ValueError('Invalid evidence range')
        if not isinstance(node['sourceQuote'],str) or not node['sourceQuote'].strip(): raise ValueError('Evidence quote is required')
    dependencies={step['id']:step.get('dependsOn',[]) for step in steps}
    visited=set()
    def visit(node,stack):
        if node in stack: raise ValueError('Workflow dependency cycle')
        if node in visited: return
        for dep in dependencies[node]:
            if dep not in dependencies: raise ValueError('Step dependency must be in this workflow')
            visit(dep,stack|{node})
        visited.add(node)
    for step in steps:
        if step.get('type')!='kg:PlanStep': raise ValueError('Expected kg:PlanStep')
        for field in ['inputs','outputs','uses','dependsOn']:
            if not isinstance(step.get(field,[]),list): raise ValueError('Reference fields must be lists')
            for value in step.get(field,[]): iri(value)
        visit(step['id'],set())
    graph=Graph().parse(data=json.dumps({'@context':CONTEXT,**data}),format='json-ld')
    return data,body,graph
