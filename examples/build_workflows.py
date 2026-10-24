"""Author-curated workflow abstractions; source quotes are extracted, not invented."""
import argparse,hashlib,json,subprocess
from pathlib import Path
import yaml
from labkg.workflows import CONTEXT,parse_note

ROOT=Path(__file__).resolve().parents[1]
BASE='https://labkg.local/id/'
def artifact(name):return BASE+'artifact-contract/'+name

def build(repo,gist):
    repo=Path(repo); gist=json.loads(Path(gist).read_text())
    commit=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()
    version=gist['history'][0]['version']
    agents=(repo/'AGENTS.md').read_text(); readme=gist['files']['README.md']['content']
    docs={'agents':(f'https://github.com/quinlan-lab/tapestry/blob/{commit}/AGENTS.md',agents),
          'gist':(f'https://gist.github.com/brentp/e5d08d13c23aed4064b54dec9154a2a4/{version}#file-readme-md',readme)}
    def evidence(doc,start,end=None):
        url,text=docs[doc]; lines=text.splitlines(); a=next(i for i,l in enumerate(lines) if start in l)
        b=next((i for i in range(a,len(lines)) if end and end in lines[i]),a)
        return {'derivedFrom':url,'sourceDigest':hashlib.sha256(text.encode()).hexdigest(),'sourceStartLine':a+1,'sourceEndLine':b+1,'sourceQuote':'\n'.join(lines[a:b+1])}
    def step(key,label,inputs,outputs,deps,doc,start,end=None,tools=(),constraints=()):
        return {'key':key,'type':'kg:PlanStep','label':label,'inputs':[artifact(x) for x in inputs],'outputs':[artifact(x) for x in outputs],'dependsOn':list(deps),'uses':list(tools),'constraints':list(constraints),**evidence(doc,start,end)}
    def script(name): return f'https://github.com/quinlan-lab/tapestry/blob/{commit}/{name}'
    notes=[]
    def workflow(key,label,status,inputs,outputs,steps,doc,start,end,prose,constraints=()):
        wid=BASE+'workflow/'+key
        for s in steps:
            s['id']=wid+'/step/'+s.pop('key'); s['dependsOn']=[wid+'/step/'+d for d in s['dependsOn']]
        data={'id':wid,'type':'kg:Workflow','label':label,'status':status,'inputs':[artifact(x) for x in inputs],'outputs':[artifact(x) for x in outputs],'constraints':list(constraints),**evidence(doc,start,end),'steps':steps}
        if key=='hifi-wdl':
            data['supportingSources']=[docs['agents'][0]]
            steps[-1]['supportingSources']=[docs['agents'][0]]
        readable='\n\n## Steps\n\n'+'\n'.join(f"{i}. **{item['label']}** — inputs: {', '.join(x.rsplit('/',1)[-1] for x in item['inputs'])}; outputs: {', '.join(x.rsplit('/',1)[-1] for x in item['outputs'])}." for i,item in enumerate(steps,1))
        if constraints: readable+='\n\n## Constraints\n\n'+'\n'.join('- '+x for x in constraints)
        readable+='\n\nSource: '+data['derivedFrom']+'\n'
        text='---\n'+yaml.safe_dump(data,sort_keys=False,allow_unicode=True,width=100)+'---\n\n# '+label+'\n\n'+prose+readable+'\n'
        parse_note(text)
        dest=ROOT/'knowledge/workflows'/f'{key}.md';dest.write_text(text);notes.append(dest)
    workflow('hifi-wdl','Prepare and run the PacBio HiFi family WDL','documented site-specific workflow',
      ['raw-bam-manifest','sequenced-members-ped'],['wdl-family-results','miniwdl-outputs-json'],[
        step('prepare','Build per-family WDL input JSON',['raw-bam-manifest','sequenced-members-ped'],['family-wdl-input-json'],[],'gist','## 1. Create Hifi inputs','scripts is in this gist.',tools=[f'https://gist.github.com/brentp/e5d08d13c23aed4064b54dec9154a2a4/{version}#file-make_hifi_family_inputs-py']),
        step('stage','Stage generated input JSON for the WDL run',['family-wdl-input-json'],['staged-family-inputs'],['prepare'],'gist','## 2. Copy','/wdl-jsons'),
        step('run','Run family.wdl with miniwdl',['staged-family-inputs'],['wdl-family-results','miniwdl-outputs-json'],['stage'],'gist','## 3. Run the WDL workflow','miniwdl run',tools=['https://github.com/quinlan-lab/HiFi-human-WGS-WDL/tree/quinlan-dna-methylation'])
      ],'gist','# Running the Pipeline','miniwdl run',
      'The gist describes converting the BAM manifest and PED files to family input JSON, staging those inputs, and running family.wdl with miniwdl. It records a site-specific deployment, not an executed run in this KG. The downstream Tapestry handoff uses miniwdl outputs.json as documented in AGENTS.md. Individual records and BAM paths are not stored here.',
      ['Input metadata stays at its declared filesystem location; only paths and schemas are retained in the KG.'])
    workflow('somalier-qc','Somalier family relatedness QC','documented site-specific workflow',
      ['wdl-family-results','sequenced-members-ped','grch38-reference','somalier-sites'],['somalier-relatedness-report'],[
        step('extract','Extract Somalier signatures from haplotagged WDL BAMs',['wdl-family-results','grch38-reference','somalier-sites'],['somalier-signatures'],[],'gist','bams=','xargs -0 -r -n 1 -P 20 somalier extract'),
        step('relate','Compare signatures using family PED',['somalier-signatures','sequenced-members-ped'],['somalier-relatedness-report'],['extract'],'gist','# run somalier relate','somalier relate -s')
      ],'gist','## Somalier','done',
      'The gist describes extraction followed by family relatedness comparison. This is a QC branch over WDL results; the sources do not establish it as a required gate before Tapestry.')
    workflow('blammo-qc','Run the documented blammo diagnostic','documented invocation; internal steps unspecified',
      ['wdl-family-results'],['blammo-report'],[
        step('run','Invoke blammo.sh in the WDL results directory',['wdl-family-results'],['blammo-report'],[],'gist','# blammo','bash blammo.sh')
      ],'gist','# blammo','bash blammo.sh',
      'Only the invocation and report location are documented in the gist. The KG does not invent the script’s internal operations or assert this diagnostic is a pipeline prerequisite.')
    workflow('pedigree-legacy','Legacy pedigree-wise methylation workflow','legacy shell/Python path',
      ['aligned-bams','family-variants','grch38-reference'],['founder-labeled-bed-bigwig-qc'],[
        step('hiphase','Read-backed phase and haplotag per sample',['aligned-bams','family-variants'],['hiphase-haplotagged-bams'],[],'agents','1. `run-hiphase.sh`',tools=[script('run-hiphase.sh')]),
        step('inheritance','Infer pedigree inheritance blocks and phased variants',['family-variants'],['inheritance-phased-vcf'],[],'agents','2. `build-iht','inheritance-phased VCF.',tools=[script('build-iht-based-haplotype-map-and-phase-variants.sh')]),
        step('methylation','Score count and model methylation',['hiphase-haplotagged-bams'],['pedigree-count-model-methylation'],['hiphase'],'agents','3. `aligned_bam_to_cpg_scores.sh`','haplotagged BAMs.',tools=[script('aligned_bam_to_cpg_scores.sh')]),
        step('reconcile','Reconcile phase and attach founder labels',['inheritance-phased-vcf','pedigree-count-model-methylation'],['founder-phased-methylation'],['inheritance','methylation'],'agents','4. `phase_meth_to_founder_haps.sh`','parental and founder haplotypes.',tools=[script('src/phase_meth_to_founder_haps.py')]),
        step('expand','Expand to all CpGs and publish tracks/QC',['founder-phased-methylation','grch38-reference'],['founder-labeled-bed-bigwig-qc'],['reconcile'],'agents','5. `expand_to_all_cpgs.sh`','variants, computes QC',tools=[script('src/expand_to_all_cpgs.py')])
      ],'agents','### Pedigree-wise','variants, computes QC',
      'This is the legacy pedigree procedure in AGENTS.md. The dependency links are a curated abstraction of the described inputs and outputs, not a Nextflow execution trace. HiPhase read-backed labels require reconciliation with inheritance before founder assignment.')
    workflow('pedigree-nextflow','Generic pedigree/model-only Nextflow workflow','implemented generic Nextflow path',
      ['miniwdl-outputs-json','sequenced-members-ped','grch38-reference'],['all-cpg-tables-bigwig-qc-provenance-manifest'],[
        step('validate','Validate WDL outputs, PED and reference',['miniwdl-outputs-json','sequenced-members-ped','grch38-reference'],['validated-run-contract'],[],'agents','driven directly by miniwdl','run as pipeline records.',tools=[script('src/tapestry_validate.py')]),
        step('normalize','Normalize the family VCF',['validated-run-contract'],['normalized-family-vcf'],['validate'],'agents','`main.nf` validates','`gtg-ped-map`/`gtg-concordance`',tools=[script('src/normalize_joint_vcf.py')]),
        step('inheritance','Derive pedigree inheritance phase',['normalized-family-vcf'],['generic-inheritance-phase'],['normalize'],'agents','`main.nf` validates','inheritance phase per selected sample',tools=[script('src/run_gtg_inheritance.py')]),
        step('filter','Filter WDL model methylation BEDs',['validated-run-contract'],['filtered-model-beds'],['validate'],'agents','`gtg-ped-map`/`gtg-concordance`','inheritance phase per selected sample',tools=[script('src/filter_model_beds.py')]),
        step('reference','Generate reference-autosome CpGs',['grch38-reference','validated-run-contract'],['reference-autosome-cpgs'],['validate'],'agents','inheritance phase per selected sample','publishes all-CpG tables',tools=[script('src/generate_reference_cpgs.py')]),
        step('phase','Reconcile HiPhase with inheritance for model methylation',['generic-inheritance-phase','filtered-model-beds'],['generic-founder-methylation'],['inheritance','filter'],'agents','`gtg-ped-map`/`gtg-concordance`','inheritance phase per selected sample',tools=[script('src/phase_meth_to_founder_haps.py')]),
        step('publish','Publish all-CpG tables, tracks, QC and provenance',['generic-founder-methylation','reference-autosome-cpgs'],['all-cpg-tables-bigwig-qc-provenance-manifest'],['phase','reference'],'agents','publishes all-CpG tables','default. Other releases',tools=[script('src/expand_model_to_all_cpgs.py')])
      ],'agents','### Generic pedigree/model-only path','default. Other releases',
      'The generic Nextflow path is pedigree-wise and model-only. Its miniwdl outputs.json input must not be confused with the raw-BAM manifest. This note expresses conceptual dependencies, not a complete process-by-process transcription of main.nf.',
      ['GRCh38 chr1–chr22 only.','WDL v3.3.0/v3.3.1 supported by default; other releases require audit.','Generic trio Nextflow support is not established by this source.'])
    workflow('trio-legacy','Legacy trio-wise methylation workflow','legacy shell/Python path; not generic trio Nextflow',
      ['aligned-bams','family-variants','trio-ped','grch38-reference'],['parent-labeled-all-cpg-tracks-qc'],[
        step('whatshap','Pedigree-aware phase and haplotag child and parents',['aligned-bams','family-variants','trio-ped'],['trio-haplotagged-bams','trio-phased-vcf'],[],'agents','1. `run-whatshap.sh`','child, father, mother BAMs.',tools=[script('run-whatshap.sh')]),
        step('methylation','Score count/model methylation for all trio members',['trio-haplotagged-bams'],['trio-count-model-methylation'],['whatshap'],'agents','2. `aligned_bam_to_cpg_scores.sh -t','samples.',tools=[script('aligned_bam_to_cpg_scores.sh')]),
        step('parent-map','Build paternal/maternal maps and assign methylation',['trio-phased-vcf','trio-count-model-methylation'],['parent-phased-methylation'],['whatshap','methylation'],'agents','3. `phase_meth_to_parent_haps.sh`','haplotype maps, assigns methylation',tools=[script('src/phase_meth_to_parent_haps.py')]),
        step('expand','Add all CpGs, annotations, QC and visualization tracks',['parent-phased-methylation','grch38-reference'],['parent-labeled-all-cpg-tracks-qc'],['parent-map'],'agents','4. `expand_to_all_cpgs.trio.sh`','annotations, QC, visualization tracks.',tools=[script('src/expand_to_all_cpgs_trio.py')])
      ],'agents','### Trio-wise','conflate them.',
      'WhatsHap/pedMEC supplies trio phase; the legacy scripts then score methylation, map it to parent haplotypes, and expand all CpGs. This is documented legacy functionality, not a claim that the generic Nextflow workflow supports trios. Scientific constraints below are summarized from the Data contracts and invariants section of AGENTS.md.',
      ['Use per-sample FORMAT/PS identity, not interval overlap alone, for nested phase sets.','Child hap1=paternal, hap2=maternal; dad A/B and mom C/D are fixed parental haplotypes.','Preserve unphased/uncovered nulls and separate paternal/maternal mismatch tracks.','Keep count and model methylation distinct.'])
    (ROOT/'knowledge/workflows/context.jsonld').write_text(json.dumps({'@context':CONTEXT},indent=2))
    return notes

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--repo',required=True);p.add_argument('--gist',required=True);a=p.parse_args()
    print('\n'.join(map(str,build(a.repo,a.gist))))
