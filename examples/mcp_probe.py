"""Exercise two independent MCP clients against a running shared server."""
import asyncio,json,os,sys,uuid
from pathlib import Path
from mcp.client.stdio import StdioServerParameters,stdio_client
from mcp.client.session import ClientSession

async def run(token,event_id,write=False):
    params=StdioServerParameters(command=sys.executable,args=['-m','labkg.mcp_server'],env={'PYTHONPATH':str(Path(__file__).resolve().parents[1]),'LABKG_TOKEN':token,'LABKG_URL':os.environ.get('LABKG_URL','http://127.0.0.1:8766')})
    async with stdio_client(params) as streams:
        async with ClientSession(*streams) as client:
            await client.initialize()
            tools=await client.list_tools()
            assert {'recall','record_work','graph_view','initialization_contract','read_source','initialize_project','project_context','assess_initialization'}<={t.name for t in tools.tools}
            if write:
                result=await client.call_tool('record_work',{'event_id':event_id,'study':'synthetic-mcp-probe','summary':f'Result: synthetic MCP connectivity marker {event_id}; written by the first client for retrieval by the second client. This is a transport demonstration.'})
                assert not result.is_error
            result=await client.call_tool('recall',{'query':event_id,'limit':3})
            assert not result.is_error
            payload=json.loads(result.content[0].text)
            assert any(event_id in e['text'] for e in payload['evidence'])
            return result.model_dump(mode='json')

async def main():
    tokens=list(json.loads(Path(sys.argv[1]).read_text()))
    if len(tokens)<2:raise ValueError('Provide two test credentials')
    event_id='mcp-probe-'+uuid.uuid4().hex
    await run(tokens[0],event_id,write=True)
    result=await run(tokens[1],event_id)
    print(json.dumps(result,indent=2))
if __name__=='__main__': asyncio.run(main())
