"""Real MCP transport test using an agent-authored methylation distillation.

This harness does not call an LLM: it submits the proposal authored in this
conversation. It proves connection/source verification/commit/retrieval, not
fresh-model schema inference or automatic server-side synthesis.
"""
import argparse,asyncio,copy,json
from pathlib import Path
from mcp.client.stdio import StdioServerParameters,stdio_client
from mcp.client.session import ClientSession
from labkg.workflows import parse_note
ROOT=Path(__file__).resolve().parents[1]

async def invoke(client,name,arguments):
    result=await client.call_tool(name,arguments)
    if result.is_error:raise RuntimeError(result.content)
    return json.loads(result.content[0].text)

async def main(config_path,output):
    config=json.loads(Path(config_path).read_text())['mcpServers']['labkg']
    params=StdioServerParameters(command=config['command'],args=config['args'],env=config['env'])
    async with stdio_client(params) as streams:
        async with ClientSession(*streams) as client:
            await client.initialize()
            spec=await invoke(client,'initialization_contract',{})
            assert spec['contract']=='labkg.initialize/v1'
            commit=json.loads((ROOT/'reports/source-inventory-current.json').read_text())['commit']
            agents=await invoke(client,'read_source',{'url':f'https://github.com/quinlan-lab/tapestry/blob/{commit}/AGENTS.md'})
            listing=await invoke(client,'read_source',{'url':'https://gist.github.com/brentp/e5d08d13c23aed4064b54dec9154a2a4'})
            assert any(d['filename']=='README.md' for d in listing['documents'])
            gist=await invoke(client,'read_source',{'url':'https://gist.github.com/brentp/e5d08d13c23aed4064b54dec9154a2a4','filename':'README.md'})
            project='methylation-connected';prefix='https://labkg.local/id/project/'+project+'/'
            old='https://labkg.local/id/'
            def resource(value):
                if value==old+'artifact-contract/raw-bam-manifest':return prefix+'file/manifest'
                if value==old+'artifact-contract/sequenced-members-ped':return prefix+'file/ped'
                if value.startswith(old+'artifact-contract/'):return value.replace(old+'artifact-contract/',prefix+'artifact/')
                if value.startswith(old+'workflow/'):return value.replace(old+'workflow/',prefix+'workflow/')
                return value
            workflows=[]
            for note in sorted((ROOT/'knowledge/workflows').glob('*.md')):
                definition,prose,_=parse_note(note.read_text());definition=copy.deepcopy(definition)
                for node in [definition,*definition['steps']]:
                    document=agents if 'tapestry/blob/' in node['derivedFrom'] else gist
                    start,end=node['sourceStartLine'],node['sourceEndLine']
                    assert document['sha256']==node['sourceDigest'],'Source changed; re-distill and recheck rather than silently reuse the old interpretation'
                    assert '\n'.join(document['text'].splitlines()[start-1:end])==node['sourceQuote']
                    node['id']=resource(node['id']);node['derivedFrom']=document['source_id']
                    for field in ['inputs','outputs','dependsOn']:
                        node[field]=[resource(v) for v in node.get(field,[])]
                    if 'supportingSources' in node:node['supportingSources']=[agents['source_id']]
                workflows.append({'definition':definition,'prose':prose})
            # These schema files were authored by the connected agent from the user's
            # example/header, not supplied by the dev server's generic contract API.
            files=[]
            for name in ['manifest','ped']:
                data=json.loads((ROOT/'knowledge/contracts'/f'{name}.json').read_text())
                files.append({'id':prefix+'file/'+name,**data})
            bundle={'project_id':project,'request_id':'initial-metadata-v1','title':'DNA methylation: trio Nextflow generalization',
              'study':'non-longitudinal','objective':'Begin generalizing the pedigree-only generic Tapestry Nextflow workflow to the trio-wise case.',
              'file_contracts':files,'workflows':workflows,'source_ids':[agents['source_id'],gist['source_id']],
              'known_gaps':['Manifest and PED contents intentionally remain outside the KG; trio membership has not been evaluated.',
                'The /scratch source files, real miniwdl outputs and full reference are unavailable on this development machine.',
                'Longitudinal study metadata has not been supplied; do not infer visits or merge identifiers.',
                'The documented trio path is legacy shell/Python; a generic Nextflow trio branch is not established.',
                'The legacy trio path uses count and model methylation; the generic pedigree path is model-only. Choose the trio output contract before wiring processes.',
                'HiPhase-derived methylation must not silently be treated as WhatsHap/pedMEC-derived methylation; regeneration or a tested phase mapping is required.']}
            (ROOT/'examples/methylation-initialization.json').write_text(json.dumps(bundle,indent=2))
            assessment=await invoke(client,'assess_initialization',{'draft':bundle})
            assert assessment['ready_to_submit']
            preview=await invoke(client,'initialize_project',{'bundle':bundle,'validate_only':True})
            assert not preview['committed'] or preview['duplicate']
            receipt=await invoke(client,'initialize_project',{'bundle':bundle})
            assert receipt['committed']
            replay=await invoke(client,'initialize_project',{'bundle':bundle});assert replay['duplicate']
            context=await invoke(client,'project_context',{'project_id':project})
            assert len(context['file_contracts'])==2 and len(context['workflows'])==6
            evidence=await invoke(client,'recall',{'query':'generic trio Nextflow model-only','limit':6})
            assert evidence['evidence']
            report={'method':'Agent-authored proposal submitted through a real MCP client to an initially empty dev KG. Not a fresh-model inference evaluation.',
              'server_contract_returned':True,'source_fetches':2,'source_citations_verified':True,'dry_run_or_already_initialized':not preview['committed'] or preview['duplicate'],'assessment_ready':assessment['ready_to_submit'],
              'committed':receipt['committed'],'duplicate_replay':replay['duplicate'],'project_context':context,
              'retrieval_sources':[e['source'] for e in evidence['evidence']]}
            Path(output).write_text(json.dumps(report,indent=2))
            print(json.dumps({'project_id':project,'file_contracts':2,'workflows':6,'source_documents':2,'committed':True,'replay_idempotent':True},indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--output',required=True);a=p.parse_args()
    asyncio.run(main(a.config,a.output))
