"""Seed explicit sources, metadata-only file contracts, and curated workflow notes."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from labkg.core import Store

FILES=['AGENTS.md','README.md','main.nf','nextflow.config','run-whatshap.sh','aligned_bam_to_cpg_scores.sh','phase_meth_to_parent_haps.sh','expand_to_all_cpgs.trio.sh','src/tapestry_validate.py','src/phasing_trio.py','src/hap_map_trio.py','src/phase_meth_to_parent_haps.py','src/expand_to_all_cpgs_trio.py','tests/test_recombination_dedup.py']
ROOT=Path(__file__).resolve().parents[1]

def seed(db,repo,gist):
    store=Store(db); repo=Path(repo)
    commit=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()
    inventory=[]
    for name in FILES:
        text=(repo/name).read_text()
        source=f'https://github.com/quinlan-lab/tapestry/blob/{commit}/{name}'
        result=store.ingest(source,'text',text,actor='repository-import')
        inventory.append({'path':name,'sha256':hashlib.sha256(text.encode()).hexdigest(),'source':source,**result})
    data=json.loads(Path(gist).read_text())
    for name,f in data['files'].items():
        store.ingest('https://gist.github.com/brentp/e5d08d13c23aed4064b54dec9154a2a4#'+name,'text',f['content'],actor='github-connector')
    for name in ['manifest','ped']:
        contract=json.loads((ROOT/'knowledge/contracts'/f'{name}.json').read_text())
        store.ingest('https://labkg.local/id/artifact-contract/'+('raw-bam-manifest' if name=='manifest' else 'sequenced-members-ped'),'file_contract',contract,actor='user-supplied')
    store.ingest('urn:availability:project','text','Project manifest and PED contents are intentionally not retained. Only their filesystem paths and schemas are catalogued. The /scratch mount is unavailable here. Longitudinal metadata was not supplied. Workflow definitions describe procedures, not completed executions.',actor='input-audit')
    from rdflib import Graph,Literal
    vocabulary=Graph().parse(ROOT/'labkg/workflow-vocabulary.ttl',format='turtle')
    claims=[{'subject':str(s),'predicate':str(p),'object':str(o),'literal':isinstance(o,Literal),'evidence':'Definition in the bundled workflow-vocabulary.ttl.'} for s,p,o in sorted(vocabulary,key=lambda t:tuple(map(str,t)))]
    store.ingest('https://labkg.local/ontology/workflows','claims',claims,actor='vocabulary-import')
    from build_workflows import build
    for path in build(repo,gist):
        store.ingest('https://labkg.local/notes/'+path.name,'workflow',path.read_text(),actor='workflow-curator',evidence_status='agent-report')
    (ROOT/'reports'/'source-inventory-current.json').write_text(json.dumps({'commit':commit,'files':inventory},indent=2))
    return inventory

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--db',required=True);p.add_argument('--repo',required=True);p.add_argument('--gist',required=True)
    a=p.parse_args(); print(json.dumps(seed(a.db,a.repo,a.gist),indent=2))
