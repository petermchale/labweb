"""Render only the fixed, validated EvidenceGraph component; no model-authored JS."""
import json
from pathlib import Path
import jsonschema

def render(contract,destination):
    root=Path(__file__).parent
    jsonschema.validate(contract,json.loads((root/'ui.schema.json').read_text()))
    data=json.dumps(contract).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    Path(destination).write_text((root/'ui.html').read_text().replace('__DATA__',data))
