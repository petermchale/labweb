"""Bounded A2UI compositions; graph data remains independent of UI layout."""
CATALOG_ID = 'urn:labweb:a2ui:catalog:v1'
DEFAULT_COMPONENTS = ['EvidenceGraph', 'EvidencePanel']


def component_choices(components=None):
    choices = list(DEFAULT_COMPONENTS if components is None else components)
    if (not choices or len(choices) > 2 or
            any(c not in DEFAULT_COMPONENTS for c in choices) or
            len(set(choices)) != len(choices)):
        raise ValueError('Choose EvidenceGraph, EvidencePanel, or both, once each in display order')
    return choices


def composition(graph, components=None):
    choices = component_choices(components)
    ids = {'EvidenceGraph': 'graph', 'EvidencePanel': 'evidence'}
    surface = 'labweb-evidence'
    return [
        {'version':'v0.9.1','createSurface':{'surfaceId':surface,'catalogId':CATALOG_ID}},
        {'version':'v0.9.1','updateComponents':{'surfaceId':surface,'components':[
            {'id':'root','component':'Column','children':[ids[c] for c in choices]},
            *[{'id':ids[c],'component':c,'graph':{'path':'/graph'},'selection':{'path':'/selection'}}
              for c in choices]]}},
        {'version':'v0.9.1','updateDataModel':{'surfaceId':surface,'value':{'graph':graph,'selection':None}}}
    ]


def view_result(graph, components=None):
    """Keep the data contract intact inside a presentation envelope."""
    return {'contract':'labkg.view/v1', 'graph':graph, 'a2ui':composition(graph, components)}
