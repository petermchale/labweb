import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('override', ['home', 'state'])
def test_launchers_share_external_state(tmp_path, override):
    checkout = tmp_path / 'checkout'
    shutil.copytree(ROOT / 'scripts', checkout / 'scripts')
    interpreter = checkout / '.venv/bin/python'
    interpreter.parent.mkdir(parents=True)
    interpreter.write_text(
        f'#!{sys.executable}\nimport json, os, sys\n'
        'print(json.dumps({"args": sys.argv[1:], '
        '"token": os.environ.get("LABKG_TOKEN_FILE")}))\n'
    )
    interpreter.chmod(0o755)
    env = {k: v for k, v in os.environ.items()
           if k not in {'LABKG_STATE', 'LABKG_TOKEN_FILE', 'XDG_STATE_HOME', 'LABKG_PORT'}}
    env['HOME'] = str(tmp_path / 'home')
    expected = Path(env['HOME']) / 'labweb-project-data/runtime'
    env['XDG_STATE_HOME'] = str(tmp_path / 'unused xdg state')
    if override == 'state':
        env['LABKG_STATE'] = str(tmp_path / 'custom state')
        expected = Path(env['LABKG_STATE'])
    expected.mkdir(parents=True)
    (expected / 'agent.token').write_text('synthetic-launcher-token')
    def launch(name):
        return json.loads(subprocess.check_output(
            ['bash', str(checkout / 'scripts' / name)], env=env, text=True))
    assert launch('dev.sh')['args'][1:3] == ['--state', str(expected)]
    assert launch('mcp.sh')['token'] == str(expected / 'agent.token')
    env['LABKG_TOKEN_FILE'] = str(expected / 'explicit.token')
    (expected / 'explicit.token').write_text('synthetic-override-token')
    assert launch('mcp.sh')['token'] == env['LABKG_TOKEN_FILE']


def test_direct_dev_server_uses_external_state(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location('dev_server', ROOT / 'scripts/dev_server.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.delenv('LABKG_STATE', raising=False)
    monkeypatch.setenv('HOME', str(tmp_path))
    monkeypatch.setattr(sys, 'argv', ['dev_server.py'])
    calls = []
    monkeypatch.setattr(module, 'create_app', lambda db, tokens: calls.append(db))
    monkeypatch.setattr(module.uvicorn, 'run', lambda *a, **kw: None)
    module.main()
    state = tmp_path / 'labweb-project-data/runtime'
    assert calls == [state / 'labkg.sqlite']
    config = json.loads((state / 'mcp-config.json').read_text())
    assert config['mcpServers']['labkg']['env']['LABKG_TOKEN_FILE'] == str(state / 'agent.token')
    assert state.stat().st_mode & 0o777 == 0o700
    assert (state / 'agent.token').stat().st_mode & 0o777 == 0o600
