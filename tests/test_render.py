import json
import pytest
from labkg.core import Store
from labkg.render import render

def test_untrusted_source_is_not_executable(tmp_path):
    data=Store(tmp_path/'graph.sqlite').graph_view('')
    data['nodes']=[{'id':'urn:hostile','label':'</script><script>alert(1)</script>','properties':[]}]
    path=tmp_path/'view.html';render(data,path)
    html=path.read_text()
    assert '</script><script>alert(1)' not in html
    assert '\\u003c/script' in html
    embedded=html.split('<script type="application/json" id="labkg-data">',1)[1].split('</script>',1)[0]
    assert json.loads(embedded)==data

def test_v1_contract_is_rejected(tmp_path):
    with pytest.raises(ValueError,match='expected labkg.graph/v2'):
        render({'contract':'labkg.ui/v1'},tmp_path/'view.html')
    assert not (tmp_path/'view.html').exists()
