"""One-command development server with private credentials and an agent config."""
import argparse,json,os,secrets,sys
from pathlib import Path
import uvicorn
from labkg.api import create_app

def main():
    default_state=os.environ.get('LABKG_STATE') or str(Path.home()/'labweb-project-data/runtime')
    p=argparse.ArgumentParser();p.add_argument('--state',default=default_state);p.add_argument('--port',type=int,default=8766)
    a=p.parse_args();state=Path(a.state).resolve();state.mkdir(parents=True,exist_ok=True);state.chmod(0o700)
    token_file=state/'agent.token'
    if not token_file.exists():token_file.write_text(secrets.token_urlsafe(32))
    token_file.chmod(0o600)
    config={'mcpServers':{'labkg':{'command':sys.executable,'args':['-m','labkg.mcp_server'],
      'env':{'PYTHONPATH':str(Path(__file__).resolve().parents[1]),'LABKG_URL':f'http://127.0.0.1:{a.port}','LABKG_TOKEN_FILE':str(token_file)}}}}
    (state/'mcp-config.json').write_text(json.dumps(config,indent=2))
    print('Dev URL: http://127.0.0.1:'+str(a.port),flush=True)
    print('Agent connection config: '+str(state/'mcp-config.json'),flush=True)
    uvicorn.run(create_app(state/'labkg.sqlite',{token_file.read_text().strip():'connected-dev-agent'}),host='127.0.0.1',port=a.port)
if __name__=='__main__':main()
