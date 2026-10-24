"""Explicit-source importers. Never execute source content."""
import json
import time
from pathlib import Path
from urllib.parse import urlparse
import httpx

ALLOWED_HOSTS={'raw.githubusercontent.com','api.github.com','gist.githubusercontent.com'}

def fetch_text(url):
    parsed=urlparse(url)
    if parsed.scheme!='https' or parsed.hostname not in ALLOWED_HOSTS or parsed.port not in {None,443} or parsed.username:
        raise ValueError('Only HTTPS GitHub raw/API/gist sources are enabled')
    # No redirects: destinations must pass the same policy explicitly.
    with httpx.stream('GET',url,timeout=30,follow_redirects=False) as r:
        r.raise_for_status()
        if r.is_redirect: raise ValueError('Redirects are disabled; use the raw URL')
        chunks=[]; size=0
        for chunk in r.iter_bytes():
            size+=len(chunk)
            if size>2_000_000: raise ValueError('Remote source exceeds 2 MB')
            chunks.append(chunk)
        return b''.join(chunks).decode('utf-8')

def ingest_url(store,url):
    text=fetch_text(url)
    if urlparse(url).hostname=='api.github.com' and '/gists/' in url:
        data=json.loads(text)
        results=[]
        for name,item in data['files'].items():
            if item.get('truncated'): raise ValueError('Truncated gist; explicitly fetch its raw URL')
            results.append(store.ingest(url+'#'+name,'text',item['content'],actor='github-connector'))
        return results
    return store.ingest(url,'text',text,actor='github-connector')

def drain_journal(store,path):
    """At least once delivery. Partial final lines wait; bad lines stop visibly.

    Durable offset advances AFTER successful ingest. Replay is idempotent.
    The journal is append-only: rotation/truncation requires a new filename.
    """
    path=Path(path).resolve()
    with store.connect() as db:
        row=db.execute('SELECT offset FROM cursors WHERE path=?',(str(path),)).fetchone()
    offset=row[0] if row else 0
    if path.stat().st_size<offset: raise ValueError('Journal was truncated; use a new filename')
    count=0
    with path.open('rb') as f:
        f.seek(offset)
        while True:
            line=f.readline(2_000_001)
            if not line: break
            if len(line)>2_000_000: raise ValueError('Journal record exceeds 2 MB')
            if not line.endswith(b'\n'): break
            event=json.loads(line)
            event['actor']='journal:'+path.name
            event['evidence_status']='agent-report'
            store.ingest(**event)
            with store.connect() as db:
                db.execute('INSERT INTO cursors VALUES(?,?) ON CONFLICT(path) DO UPDATE SET offset=excluded.offset',(str(path),f.tell()))
            count+=1
    return count

def watch(store,path,interval=1):
    while True:
        drain_journal(store,path)
        time.sleep(interval)

class RemoteSink:
    """Local durable journal cursor, shared remote graph; token never goes in events."""
    def __init__(self,cursor_store,url,token,client=None):
        self.cursor_store=cursor_store
        self.client=client or httpx.Client(base_url=url,headers={'Authorization':'Bearer '+token},timeout=60)
    def connect(self): return self.cursor_store.connect()
    def ingest(self,**event):
        event.pop('actor',None)
        result=self.client.post('/ingest',json=event)
        result.raise_for_status()
        return result.json()
