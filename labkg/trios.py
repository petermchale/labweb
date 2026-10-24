"""A tested implementation slice for a future generic Nextflow trio channel.

This selects input contracts; it does not run scientific phasing or claim
HiPhase model BEDs remain compatible with WhatsHap haplotype assignments.
"""
from rdflib import Literal
from .core import KG,uid

def eligible_trios(store,study='non-longitudinal'):
    ds=store.dataset()
    # Use RDF joins, not text search, to traverse PED -> parents -> sequence membership.
    rows=ds.query('''
    PREFIX kg: <https://labkg.local/vocab/>
    SELECT DISTINCT ?child ?father ?mother WHERE {
      ?child kg:study ?study; kg:sequenced true; kg:father ?father; kg:mother ?mother.
      ?father kg:sequenced true; kg:study ?study.
      ?mother kg:sequenced true; kg:study ?study.
    }''',initBindings={'study':uid('study',study)})
    result=[]
    for child,father,mother in sorted(rows,key=lambda r:tuple(map(str,r))):
        if len({child,father,mother})!=3: continue
        if len(set(ds.objects(child,KG.father)))!=1 or len(set(ds.objects(child,KG.mother)))!=1:
            raise ValueError('Conflicting parent assertions; resolve source revisions first')
        families=[set(ds.objects(p,KG.family)) for p in (child,father,mother)]
        if not set.intersection(*families): continue
        members={}
        for role,person in [('child',child),('father',father),('mother',mother)]:
            centers=set(ds.objects(person,KG['center']))
            bams=sorted(str(b) for b in ds.subjects(KG.sample,person) if centers.intersection(ds.objects(b,KG['center'])))
            members[role]={'person':str(person),'unaligned_bams':bams}
        missing=[role for role,v in members.items() if not v['unaligned_bams']]
        result.append({'trio_id':str(child),'members':members,'missing_bams':missing,
                       'ready_for_wdl_input':not missing,'ready_for_tapestry':False,
                       'required_phase_source':'WhatsHap/pedMEC',
                       'methylation_action':'Regenerate haplotype-specific methylation after trio haplotagging or validate an explicit relabeling transform.'})
    return result
