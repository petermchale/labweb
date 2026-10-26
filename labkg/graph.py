"""Host-independent, bounded projections of active RDF assertions."""
import re
from urllib.parse import unquote
from rdflib import Literal, RDF, RDFS, URIRef
from .core import KG, PROV

DEFAULT_RELATIONS = ('input', 'output', 'dependsOn', 'hasStep', 'uses', 'mentions',
                     'imports', 'defines', 'father', 'mother', 'sample', 'family')

def short(value):
    return unquote(str(value).rsplit('/', 1)[-1].rsplit('#', 1)[-1])

def subgraph(store, query, project_id=None, focus=None, depth=1, max_nodes=50,
             max_edges=80, predicates=None):
    if project_id and not re.fullmatch(r'[a-z][a-z0-9-]{0,63}', project_id):
        raise ValueError('Invalid project_id')
    if not 0 <= depth <= 3 or not 1 <= max_nodes <= 100 or not 1 <= max_edges <= 200:
        raise ValueError('Invalid graph bounds')
    predicates = list(DEFAULT_RELATIONS if predicates is None else predicates)
    if len(predicates) > 30 or any(p not in DEFAULT_RELATIONS for p in predicates):
        raise ValueError('Unsupported relationship filter')
    prefix = f'https://labkg.local/id/project/{project_id}/' if project_id else None
    ds = store.dataset()
    # One immutable active dataset snapshot per request. Never consult old revisions.
    relations, properties = [], {}
    for g in sorted(ds.graphs(), key=lambda g: str(g.identifier)):
        revision = str(g.identifier)
        for a in sorted(g.subjects(RDF.type, RDF.Statement), key=str):
            s, p, o = (g.value(a, term) for term in (RDF.subject, RDF.predicate, RDF.object))
            if not isinstance(s, URIRef) or (prefix and not str(s).startswith(prefix)):
                continue
            entry = dict(subject=str(s), predicate=str(p), object=str(o), revision=revision,
                         line=int(g.value(a, KG.line) or 1), evidence=str(g.value(a, KG.evidence) or ''),
                         method=str(g.value(a, KG.method) or ''),
                         status=str(g.value(URIRef(revision), KG.evidenceStatus) or 'unknown'))
            entry['id'] = str(a)
            entry['source'] = str(g.value(URIRef(revision), PROV.wasDerivedFrom) or '')
            if isinstance(o, Literal) or p == RDF.type or p == PROV.wasDerivedFrom:
                properties.setdefault(str(s), []).append(entry)
            elif isinstance(o, URIRef) and short(p) in predicates:
                relations.append(entry)
    # Project filtering is a retrieval scope, not an authorization boundary.
    # Authentication currently grants access to the whole store.
    known = set(properties) | {e[k] for e in relations for k in ('subject', 'object')}
    if focus:
        if focus not in known or (prefix and not focus.startswith(prefix)):
            raise ValueError('Focus node not found in requested scope')
        seeds = {focus}
    else:
        terms = re.findall(r'[\w-]+', query.lower())
        meaningful = [t for t in terms if t != project_id and t not in {'the','and','of','to'}]
        scored = []
        for node in sorted(known):
            if prefix and not node.startswith(prefix):
                continue
            labels = [x['object'] for x in properties.get(node, []) if x['predicate'] == str(RDFS.label)]
            haystack = ' '.join([node, *labels]).lower()
            score = sum(t in haystack for t in meaningful)
            if score:
                scored.append((-score, node))
        seeds = {n for _, n in sorted(scored)[:8]}
        if not seeds and prefix and not meaningful:
            seeds = {n for n in sorted(known) if n.startswith(prefix) and '/workflow/' in n and '/step/' not in n}
    reached = set(seeds)
    for _ in range(depth):
        reached |= {e[k] for e in relations if e['subject'] in reached or e['object'] in reached
                    for k in ('subject', 'object')}
    candidates = [e for e in relations if e['subject'] in reached and e['object'] in reached]
    order = {str(KG[x]): i for i, x in enumerate(DEFAULT_RELATIONS)}
    candidates.sort(key=lambda e: (order.get(e['predicate'], 99), e['subject'], e['object'], e['revision']))
    chosen_nodes = set(sorted(seeds)[:max_nodes])
    edges = []
    for e in candidates:
        pair = {e['subject'], e['object']}
        if len(edges) < max_edges and len(chosen_nodes | pair) <= max_nodes:
            chosen_nodes |= pair
            edges.append(e)
    nodes = []
    for node in sorted(chosen_nodes):
        props = properties.get(node, [])
        labels = sorted({e['object'] for e in props if e['predicate'] == str(RDFS.label)})
        nodes.append(dict(id=node, label=labels[0] if labels else short(node), properties=props))
    return dict(contract='labkg.graph/v2', component='EvidenceGraph', nodes=nodes, edges=edges,
                evidence=[], scope=dict(query=query, project_id=project_id, focus=focus, depth=depth,
                    predicates=predicates, max_nodes=max_nodes, max_edges=max_edges,
                    seed_ids=sorted(seeds), candidate_nodes=len(reached), candidate_edges=len(candidates),
                    omitted_nodes=len(reached-chosen_nodes), omitted_edges=len(candidates)-len(edges),
                    truncated=len(reached-chosen_nodes)>0 or len(candidates)>len(edges),
                    selection='Lexical node/label seeds (up to 8), then undirected neighborhood; active revisions only'))
