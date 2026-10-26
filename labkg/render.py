"""Validated graph data and fixed, remotely distributable viewer assets."""
import json
from pathlib import Path
import jsonschema

ROOT = Path(__file__).parent

def validate_contract(contract):
    if contract.get('contract') != 'labkg.graph/v2':
        raise ValueError('Unsupported graph contract; expected labkg.graph/v2')
    jsonschema.validate(contract,json.loads((ROOT/'graph.schema.json').read_text()))

def app_html():
    return (ROOT/'app.html').read_text().replace('__DATA__','null')

def render(contract,destination):
    validate_contract(contract)
    data=json.dumps(contract).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    Path(destination).write_text((ROOT/'app.html').read_text().replace('__DATA__',data))
