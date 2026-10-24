"""Bounded retrieval comparison, NOT a blinded agent productivity experiment."""
import argparse,json,re,subprocess,time
from pathlib import Path
import httpx
from seed import FILES

CASES=[
 ('What guards nested phase sets?', 'nested phase PS', ['src/phasing_trio.py','tests/test_recombination_dedup.py']),
 ('Where is the generic pedigree-only mode fixed?', 'mode pedigree', ['src/tapestry_validate.py','main.nf']),
 ('How are trio haplotypes named?', 'kid_pat dad_A mom_C', ['src/phase_meth_to_parent_haps.py']),
 ('What phasing tool does the trio use?', 'whatshap pedMEC', ['run-whatshap.sh']),
 ('How is methylation null-preserved?', 'unphased null methylation', ['src/phase_meth_to_parent_haps.py']),
 ('What does the WDL handoff require?', 'miniwdl outputs.json', ['src/tapestry_validate.py','README.md']),
]

def main():
    p=argparse.ArgumentParser();p.add_argument('--repo',required=True);p.add_argument('--credentials',required=True);p.add_argument('--output',required=True);a=p.parse_args()
    token=next(iter(json.loads(Path(a.credentials).read_text())))
    client=httpx.Client(base_url='http://127.0.0.1:8765',headers={'Authorization':'Bearer '+token},timeout=60)
    results=[]
    for question,query,expected in CASES:
        t=time.perf_counter()
        baseline=subprocess.run(['rg','-n','-i','-C','3','|'.join(re.escape(x) for x in query.split()),*[str(Path(a.repo)/name) for name in FILES]],capture_output=True,text=True,check=False)
        rg_ms=(time.perf_counter()-t)*1000
        t=time.perf_counter(); response=client.post('/recall',json={'query':query,'limit':8});response.raise_for_status();answer=response.json();kg_ms=(time.perf_counter()-t)*1000
        retrieved={e['source'].split('/'+json.loads((Path(__file__).resolve().parents[1]/'reports/source-inventory.json').read_text())['commit']+'/')[-1] for e in answer['evidence']}
        results.append({'question':question,'query':query,'expected_any':expected,'kg_hit':bool(set(expected)&retrieved),'rg_hit':any(name in baseline.stdout for name in expected),'rg_ms':round(rg_ms,2),'kg_http_ms':round(kg_ms,2),'rg_output_bytes':len(baseline.stdout.encode()),'kg_evidence_text_bytes':sum(len(e['text'].encode()) for e in answer['evidence']),'kg_payload_bytes':len(response.content),'kg_sources':sorted(retrieved),'kg_evidence':answer['evidence']})
    out={'method':'One run; same 14-file local source corpus for rg. KG additionally has the public gist, provided examples, and agent reports. Regex OR terms with 3 context lines versus FTS5 OR terms, top 8 chunks. Expected files manually chosen by author after source inspection. Not blinded, not causal, no end-to-end coding time measured. Different ranking and output budgets; report text and full payload bytes separately.','results':results}
    Path(a.output).write_text(json.dumps(out,indent=2))
    print(json.dumps([{k:v for k,v in x.items() if k not in {'kg_sources','kg_evidence'}} for x in results],indent=2))
if __name__=='__main__': main()
