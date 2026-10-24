"""Exercise real MCP clarification routing without inventing a human response."""
import argparse,asyncio,copy,json
from pathlib import Path
from mcp.client.stdio import StdioServerParameters,stdio_client
from mcp.client.session import ClientSession
from connected_initialization_probe import invoke,ROOT

async def main(config_path,output):
    config=json.loads(Path(config_path).read_text())['mcpServers']['labkg']
    params=StdioServerParameters(command=config['command'],args=config['args'],env=config['env'])
    bundle=json.loads((ROOT/'examples/methylation-initialization.json').read_text())
    async with stdio_client(params) as streams:
        async with ClientSession(*streams) as client:
            await client.initialize()
            incomplete=copy.deepcopy(bundle);known_path=incomplete['file_contracts'][0].pop('path')
            response=await invoke(client,'assess_initialization',{'draft':incomplete})
            assert response['status']=='needs_user_input'
            assert any(q['field']=='file_contracts.0.path' for q in response['questions'])
            # The answer is already in the original user message. Restore it; this
            # test does not claim a new interactive human clarification occurred.
            incomplete['file_contracts'][0]['path']=known_path
            complete=await invoke(client,'assess_initialization',{'draft':incomplete})
            assert complete['ready_to_submit']
            needs_work=copy.deepcopy(bundle);del needs_work['workflows']
            repair=await invoke(client,'assess_initialization',{'draft':needs_work})
            assert not repair['questions'] and repair['agent_tasks']
            report={'missing_path_assessment':response,'restored_user_supplied_path_assessment':complete,
                'missing_workflow_assessment':repair,'new_user_answer_requested':False,
                'explanation':'The omitted path was restored from the original user-supplied metadata. The server generates questions; the connected agent must ask genuine unresolved questions and wait.'}
            Path(output).write_text(json.dumps(report,indent=2))
            print(json.dumps({'missing_path':'user question','missing_workflow':'agent task','restored_metadata':'ready','partial_draft_stored':False},indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--output',required=True);a=p.parse_args()
    asyncio.run(main(a.config,a.output))
