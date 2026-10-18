"""Disposable synthetic-only CRUD proof. No owner DB or original-site claims."""
from __future__ import annotations
import sqlite3
import tempfile
from pathlib import Path
from typing import Literal
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field

class Item(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    id: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,39}$")
    title: str = Field(min_length=1, max_length=100)
    category: str = Field(min_length=1, max_length=60)
    score: int = Field(ge=0, le=10000)

class Patch(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    title: str | None = Field(default=None, min_length=1, max_length=100)
    category: str | None = Field(default=None, min_length=1, max_length=60)
    score: int | None = Field(default=None, ge=0, le=10000)

def create_app(db_path: Path, *, synthetic_only: Literal[True] = True) -> FastAPI:
    """Only a new database inside a private system-temp folder is permitted."""
    root = Path(tempfile.gettempdir()).resolve()
    path = Path(db_path)
    if path.is_symlink() or not path.is_absolute() or path.exists():
        raise ValueError("CRUD requires a fresh, nonexistent temp DB")
    parent = path.parent
    if parent.is_symlink() or parent.resolve().parent != root or not parent.name.startswith("astra-synth-crud-"):
        raise ValueError("CRUD path must be a direct astra-synth-crud-* system-temp directory")
    if not parent.is_dir():
        raise ValueError("CRUD temp directory absent")
    if synthetic_only is not True:
        raise ValueError("real data is forbidden")
    app = FastAPI(title="ASTRA fictional CRUD")
    def connect():
        db = sqlite3.connect(path)
        db.row_factory = sqlite3.Row
        return db
    with connect() as db:
        db.execute("CREATE TABLE items (id TEXT PRIMARY KEY, title TEXT NOT NULL, category TEXT NOT NULL, score INTEGER NOT NULL)")
    def get(id: str):
        with connect() as db:
            row = db.execute("SELECT * FROM items WHERE id=?", (id,)).fetchone()
            if row is None:
                raise HTTPException(404, "not found")
            return dict(row)
    @app.get("/api/items")
    def listing():
        with connect() as db:
            return [dict(r) for r in db.execute("SELECT * FROM items ORDER BY id")]
    @app.get("/api/items/{id}")
    def detail(id: str):
        return get(id)
    @app.post("/api/items", status_code=201)
    def create(item: Item):
        with connect() as db:
            try:
                db.execute("INSERT INTO items VALUES (?,?,?,?)", (item.id, item.title, item.category, item.score))
            except sqlite3.IntegrityError:
                raise HTTPException(409, "duplicate id")
        return item.model_dump()
    @app.patch("/api/items/{id}")
    def update(id: str, patch: Patch):
        values = patch.model_dump(exclude_unset=True)
        if not values or any(v is None for v in values.values()):
            raise HTTPException(422, "empty or null patch")
        get(id)
        with connect() as db:
            for field, value in values.items():
                db.execute(f"UPDATE items SET {field}=? WHERE id=?", (value, id))
        return get(id)
    @app.delete("/api/items/{id}", status_code=204)
    def delete(id: str):
        get(id)
        with connect() as db:
            db.execute("DELETE FROM items WHERE id=?", (id,))
    return app
