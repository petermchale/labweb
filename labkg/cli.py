import argparse
import json
import os
from pathlib import Path
from .core import Store

def main():
    p=argparse.ArgumentParser(description='LabKG local server and explicit ingestion')
    p.add_argument('--db',default=os.environ.get('LABKG_DB','labkg.sqlite'))
    s=p.add_subparsers(dest='command',required=True)
    serve=s.add_parser('serve'); serve.add_argument('--port',type=int,default=8765); serve.add_argument('--host',default='127.0.0.1')
    imp=s.add_parser('ingest'); imp.add_argument('path'); imp.add_argument('--source'); imp.add_argument('--kind',default='text',choices=['text','ped','manifest','claims','file_contract','workflow']); imp.add_argument('--study',default='non-longitudinal'); imp.add_argument('--status',default='source')
    url=s.add_parser('url'); url.add_argument('url')
    rec=s.add_parser('recall'); rec.add_argument('query')
    view=s.add_parser('view'); view.add_argument('query')
    exp=s.add_parser('export'); exp.add_argument('--history',action='store_true')
    watch=s.add_parser('watch'); watch.add_argument('journal'); watch.add_argument('--once',action='store_true'); watch.add_argument('--url',help='Forward to shared server, using LABKG_TOKEN; --db stores the local cursor')
    args=p.parse_args(); store=Store(args.db)
    if args.command=='serve':
        import uvicorn
        from .api import create_app
        uvicorn.run(create_app(args.db),host=args.host,port=args.port)
        return
    if args.command=='ingest':
        path=Path(args.path).resolve()
        out=store.ingest(args.source or path.as_uri(),args.kind,path.read_text(),study=args.study,evidence_status=args.status)
    elif args.command=='url':
        from .connectors import ingest_url
        out=ingest_url(store,args.url)
    elif args.command=='recall': out=store.recall(args.query)
    elif args.command=='view': out=store.graph_view(args.query)
    elif args.command=='export':
        print(store.dataset(args.history).serialize(format='trig')); return
    else:
        from .connectors import watch,drain_journal,RemoteSink
        if args.url: store=RemoteSink(store,args.url,os.environ['LABKG_TOKEN'])
        out=drain_journal(store,args.journal) if args.once else watch(store,args.journal)
    print(json.dumps(out,indent=2))
if __name__=='__main__': main()
