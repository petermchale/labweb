"""Opt-in capture adapter for an agent CLI that emits text to stdout/stderr.

Run: python examples/capture.py JOURNAL SOURCE_IRI -- agent-command ...
The watcher distills completed runs automatically. Use a dedicated transcript
stream if agent output can contain secrets; this adapter does not redact them.
"""
import json,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path

def main():
    journal,source,*command=sys.argv[1:]
    if command and command[0]=='--': command=command[1:]
    if not command: raise SystemExit('Expected a command after --')
    proc=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    chunk=[]; size=0; index=0
    def flush():
        nonlocal chunk,size,index
        event={'source':source+':'+str(index),'kind':'text','content':''.join(chunk),'study':'non-longitudinal'}
        with Path(journal).open('a') as f: f.write(json.dumps(event)+'\n')
        chunk=[];size=0;index+=1
    for line in proc.stdout:
        print(line,end='',flush=True)
        # Emit bounded records throughout the run, not just on final exit.
        for start in range(0,len(line),100_000):
            piece=line[start:start+100_000];chunk.append(piece);size+=len(piece)
            if size>=100_000: flush()
        if chunk: flush()
    code=proc.wait()
    chunk=[f'Result: agent command exited with status {code} at {datetime.now(timezone.utc).isoformat()}'];flush()
    raise SystemExit(code if code>=0 else 128-code)
if __name__=='__main__': main()
