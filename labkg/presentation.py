"""A2UI composition adapter; graph data remains independent of UI layout."""
CATALOG_ID = 'urn:labweb:a2ui:catalog:v1'

def composition(graph):
    surface = 'labweb-evidence'
    return [
        {'version':'v0.9.1','createSurface':{'surfaceId':surface,'catalogId':CATALOG_ID}},
        {'version':'v0.9.1','updateComponents':{'surfaceId':surface,'components':[
            {'id':'root','component':'Column','children':['graph','evidence']},
            {'id':'graph','component':'EvidenceGraph','graph':{'path':'/graph'},'selection':{'path':'/selection'}},
            {'id':'evidence','component':'EvidencePanel','graph':{'path':'/graph'},'selection':{'path':'/selection'}}]}},
        {'version':'v0.9.1','updateDataModel':{'surfaceId':surface,'value':{'graph':graph,'selection':None}}}
    ]
