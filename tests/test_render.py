import json
from pathlib import Path
from labkg.render import render

def test_untrusted_source_is_not_executable(tmp_path):
    data={'contract':'labkg.ui/v1','component':'EvidenceGraph','nodes':[], 'edges':[], 'evidence':[{'text':'</script><script>alert(1)</script>'}]}
    path=tmp_path/'view.html';render(data,path)
    html=path.read_text()
    assert '</script><script>alert(1)' not in html
    assert '\\u003c/script' in html
    assert 'innerHTML' not in html
