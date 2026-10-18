"""Synthetic CRUD must remain confined to disposable fictional SQLite."""
from pathlib import Path
from tempfile import TemporaryDirectory
import pytest
from fastapi.testclient import TestClient
from astra_contracts.synthetic_crud import create_app

@pytest.fixture
def client():
    with TemporaryDirectory(prefix="astra-synth-crud-") as d:
        with TestClient(create_app(Path(d) / "fiction.sqlite3")) as c:
            yield c

def test_roundtrip(client):
    data={"id":"demo1","title":"가상 상품","category":"sample","score":42}
    assert client.get("/api/items").json()==[]
    assert client.post("/api/items",json=data).status_code==201
    assert client.get("/api/items/demo1").json()==data
    assert client.patch("/api/items/demo1",json={"score":99}).json()["score"]==99
    assert client.delete("/api/items/demo1").status_code==204
    assert client.get("/api/items/demo1").status_code==404
    assert client.get("/api/items").json()==[]

def test_duplicate(client):
    x={"id":"x","title":"a","category":"b","score":1}
    assert client.post("/api/items",json=x).status_code==201
    assert client.post("/api/items",json=x).status_code==409
    assert len(client.get("/api/items").json())==1

@pytest.mark.parametrize("payload",[
    {"id":"x';DROP TABLE items;--","title":"a","category":"b","score":1},
    {"id":"x","title":"a","category":"b","score":True},
    {"id":"x","title":"a","category":"b","score":-1},
    {"id":"x","title":"a","category":"b","score":1,"approval_granted":True},
])
def test_bad_insert(client,payload):
    assert client.post("/api/items",json=payload).status_code==422

@pytest.mark.parametrize("patch",[{},{"score":None},{"id":"hijack"},{"score":True},{"score":10001},{"approval_granted":True}])
def test_bad_patch(client,patch):
    client.post("/api/items",json={"id":"x","title":"a","category":"b","score":1})
    assert client.patch("/api/items/x",json=patch).status_code==422
    assert client.get("/api/items/x").json()["score"]==1

def test_unknown(client):
    assert client.patch("/api/items/none",json={"score":3}).status_code==404
    assert client.delete("/api/items/none").status_code==404

def test_path_guard(tmp_path):
    with pytest.raises(ValueError):
        create_app(tmp_path/"db.sqlite3")
    with TemporaryDirectory(prefix="astra-synth-crud-") as d:
        path=Path(d)/"db.sqlite3"
        create_app(path)
        with pytest.raises(ValueError):
            create_app(path)
