"""Exercise two independent MCP clients against a running shared server."""
import asyncio,json,os,sys
from pathlib import Path
from mcp.client.stdio import StdioServerParameters,stdio_client
from mcp.client.session import ClientSession

async def run(token,write=False):
    params=StdioServerParameters(command=sys.executable,args=['-m','labkg.mcp_server'],env={'PYTHONPATH':str(Path(__file__).resolve().parents[1]),'LABKG_TOKEN':token,'LABKG_URL':os.environ.get('LABKG_URL','http://127.0.0.1:8765')})
    async with stdio_client(params) as streams:
        async with ClientSession(*streams) as client:
            await client.initialize()
            tools=await client.list_tools()
            assert {t.name for t in tools.tools}=={'recall','record_work','graph_view','initialization_contract','read_source','initialize_project','project_context','assess_initialization'}
            if write:
                result=await client.call_tool('record_work',{'event_id':'utility:nested-regression','summary':'Utility experiment: tests/test_recombination_dedup.py ran 4 tests successfully. Preserve per-sample PS identity when extending the generic Nextflow workflow to trios; nested phase-set spans must not multiply SNVs.'})
                assert not result.is_error
            result=await client.call_tool('recall',{'query':'Utility experiment regression','limit':3})
            assert not result.is_error
            payload=json.loads(result.content[0].text)
            assert any('utility%3Anested-regression' in e['source'] and e['actor']=='utility-agent' for e in payload['evidence'])
            return result.model_dump(mode='json')

async def main():
    tokens=list(json.loads(Path(sys.argv[1]).read_text()))
    await run(tokens[0],write=True)
    result=await run(tokens[1])
    print(json.dumps(result,indent=2))
if __name__=='__main__': asyncio.run(main())
