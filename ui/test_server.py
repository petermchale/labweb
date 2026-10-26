"""Synthetic-only browser test server; no production database or token access."""
import tempfile
from pathlib import Path
from fastapi.responses import HTMLResponse
from labkg.api import create_app
from labkg.core import Store, KG
from labkg.render import render
_state=tempfile.TemporaryDirectory(prefix='labweb-ui-test-')
path=Path(_state.name)
store=Store(path/'test.sqlite')
p='https://labkg.local/id/project/demo/'
claims=[dict(subject=p+'workflow/hifi',predicate=str(KG.output),object=p+'artifact/outputs',evidence='Synthetic handoff <script>window.injected=true</script>'),dict(subject=p+'workflow/tapestry',predicate=str(KG.input),object=p+'artifact/outputs',evidence='Synthetic downstream evidence')]
store.ingest('urn:synthetic:ui','claims',claims,evidence_status='synthetic')
app=create_app(store.path,{'synthetic-browser-token':{'actor':'test','role':'reader'}})
render(store.graph_view('hifi',project_id='demo',depth=2),path/'fixture.html')
@app.get('/fixture')
def fixture():return HTMLResponse((path/'fixture.html').read_text())
@app.get('/host')
def host():return HTMLResponse(Path('ui/tests/host.html').read_text())
from fastapi.staticfiles import StaticFiles
app.mount('/test-modules',StaticFiles(directory='ui/.build'),name='test-modules')
@app.get('/composition-test')
def composition_test():return HTMLResponse('<!doctype html><html lang="en"><title>A2UI composition test</title><style>.graph{height:420px}</style><main id="labweb"></main></html>')
