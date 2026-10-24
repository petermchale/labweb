import hmac
import os
import json
from pathlib import Path
from typing import Any, Literal
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field
from .core import Store
from .initialize import ReadSourceRequest,InitializeRequest,AssessmentRequest

class Ingest(BaseModel):
    source: str
    kind: Literal['text','ped','manifest','claims','file_contract','workflow']='text'
    content: Any
    study: str='non-longitudinal'
    evidence_status: Literal['source','user-example','synthetic','agent-report']='agent-report'

class Recall(BaseModel):
    query: str=Field(min_length=1,max_length=1000)
    limit: int=Field(default=8,ge=1,le=30)

def create_app(db_path=None,tokens=None):
    store=Store(db_path or os.environ.get('LABKG_DB','labkg.sqlite'))
    # token -> actor. The server, not client content, determines attribution.
    if tokens is None:
        token_file=os.environ.get('LABKG_TOKENS_FILE')
        tokens=json.loads(Path(token_file).read_text()) if token_file else json.loads(os.environ.get('LABKG_TOKENS','{}'))
    if not tokens or any(len(t)<16 for t in tokens):
        raise ValueError('LABKG_TOKENS must map tokens (>=16 characters) to actor names')
    principals={token:({'actor':value,'role':'writer'} if isinstance(value,str) else value) for token,value in tokens.items()}
    if any(p.get('role') not in {'reader','writer'} or not p.get('actor') for p in principals.values()):
        raise ValueError('Every principal needs an actor and reader/writer role')
    app=FastAPI(title='LabKG',version='0.1.0')
    def authenticate(authorization: str=Header(default='')):
        supplied=authorization.removeprefix('Bearer ')
        for token,principal in principals.items():
            if hmac.compare_digest(token,supplied): return principal
        raise HTTPException(401,'Bearer token required')
    @app.get('/health')
    def health(): return {'status':'ok'}
    @app.post('/ingest')
    def ingest(payload:Ingest,actor=Depends(authenticate)):
        if actor['role']!='writer': raise HTTPException(403,'Writer role required')
        try: return store.ingest(**payload.model_dump(),actor=actor['actor'])
        except (ValueError,KeyError,TypeError) as e: raise HTTPException(422,str(e)) from e
    @app.get('/initialization/contract')
    def initialization_contract(actor=Depends(authenticate)):
        from .initialize import contract
        return contract()
    @app.post('/sources/read')
    def source_read(payload:ReadSourceRequest,actor=Depends(authenticate)):
        from .initialize import read_source
        import httpx
        if actor['role']!='writer':raise HTTPException(403,'Writer role required')
        try:return read_source(store,payload.url,payload.filename,actor['actor'])
        except (ValueError,KeyError,TypeError) as e:raise HTTPException(422,str(e)) from e
        except httpx.HTTPError as e:raise HTTPException(502,'Source could not be fetched: '+str(e)) from e
    @app.post('/initialization/assess')
    def assess(payload:AssessmentRequest,actor=Depends(authenticate)):
        from .initialize import assess_initialization
        try:return assess_initialization(store,payload.draft)
        except (ValueError,KeyError,TypeError) as e:raise HTTPException(422,str(e)) from e
    @app.post('/initialize')
    def project_initialize(payload:InitializeRequest,actor=Depends(authenticate)):
        from .initialize import initialize_project
        if actor['role']!='writer':raise HTTPException(403,'Writer role required')
        try:return initialize_project(store,payload.bundle,actor['actor'],payload.validate_only)
        except (ValueError,KeyError,TypeError) as e:raise HTTPException(422,str(e)) from e
    @app.get('/projects/{project_id}')
    def get_project(project_id:str,actor=Depends(authenticate)):
        from .initialize import project_context
        try:return project_context(store,project_id)
        except ValueError as e:raise HTTPException(404,str(e)) from e
    @app.post('/recall')
    def recall(payload:Recall,actor=Depends(authenticate)):
        return store.recall(payload.query,payload.limit)
    @app.post('/view')
    def view(payload:Recall,actor=Depends(authenticate)):
        return store.graph_view(payload.query)
    @app.api_route('/sparql',methods=['GET','POST'])
    async def sparql(request:Request,actor=Depends(authenticate)):
        from .sparql import execute
        from starlette.concurrency import run_in_threadpool
        if request.method=='GET': query=request.query_params.get('query','')
        else:
            body=await request.body()
            if len(body)>10000: raise HTTPException(413,'Query exceeds 10 KB')
            if request.headers.get('content-type','').split(';')[0]!='application/sparql-query':
                raise HTTPException(415,'Use application/sparql-query')
            query=body.decode('utf-8')
        try:
            answer=await run_in_threadpool(execute,store,query)
            return Response(json.dumps(answer),media_type='application/sparql-results+json')
        except TimeoutError as e: raise HTTPException(408,str(e)) from e
        except ValueError as e: raise HTTPException(400,str(e)) from e
    @app.get('/trios')
    def trios(study:str='non-longitudinal',actor=Depends(authenticate)):
        from .trios import eligible_trios
        from rdflib import RDF
        from .core import KG
        if not any(store.dataset().subjects(RDF.type,KG.Person)):
            return {'status':'not_evaluated','trios':None,'reason':'Only file paths and schemas are retained; evaluate trio membership against the source data where it resides.'}
        try: return {'status':'evaluated','trios':eligible_trios(store,study)}
        except ValueError as e: raise HTTPException(409,str(e)) from e
    @app.get('/export')
    def export(history:bool=False,actor=Depends(authenticate)):
        return Response(store.dataset(history).serialize(format='trig'),media_type='application/trig')
    return app
