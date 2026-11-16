"""Operations shared by the CLI and the MCP server.

Each operation opens a .loo file, does one change and saves it.
Before the first overwrite of a file, a copy is kept as ``<file>.bak``.
"""
from __future__ import annotations

import json
import os
import shutil

from . import sql
from .model import Model

ATTR_SCHEMA = {
    "type": "array",
    "description": 'Attributes: "name" strings or {"name", "type" (e.g. INT, VARCHAR(50), '
                   'DECIMAL(10,2), DATE, TEXT, or any SQL type), "pk" (bool)}',
    "items": {"anyOf": [{"type": "string"}, {"type": "object", "properties": {
        "name": {"type": "string"}, "type": {"type": "string"}, "pk": {"type": "boolean"}},
        "required": ["name"]}]},
}
P = {"type": "string", "description": "Path to the .loo file"}


def _open(path: str) -> Model:
    return Model.open(path)


def _save(m: Model, path: str):
    if os.path.exists(path) and not os.path.exists(path + ".bak"):
        shutil.copy2(path, path + ".bak")
    m.save(path)


def _edit(fn):
    def run(path: str, **kw):
        m = _open(path)
        res = fn(m, **kw)
        _save(m, path)
        return res if res is not None else {"ok": True, "summary": summary(m)}
    run.__doc__ = fn.__doc__
    return run


def summary(m: Model) -> str:
    d = m.to_dict()
    return (f"{len(d['entities'])} entities, {len(d['associations'])} associations, "
            f"{len(d['links'])} links")


def read(path: str):
    """Read a .loo file and return entities, associations, links as JSON."""
    return _open(path).to_dict()


def new(path: str, spec: dict | None = None, overwrite: bool = False):
    """Create a new .loo file, optionally filled from a spec
    {entities:[{name, attributes, x?, y?}], associations:[...], links:[{entity, association, card}]}."""
    if os.path.exists(path) and not overwrite:
        raise FileExistsError(f"{path} exists (pass overwrite=true)")
    m = Model.new()
    if spec:
        m.apply_spec(spec)
    _save(m, path)
    return {"ok": True, "path": path, "summary": summary(m)}


@_edit
def apply_spec(m: Model, spec: dict):
    """Add every object of a spec (same shape as `new`) to an existing file."""
    m.apply_spec(spec)


@_edit
def add_entity(m: Model, name: str, attributes: list | None = None, x: int | None = None,
               y: int | None = None):
    """Add an entity."""
    m.add_entity(name, attributes or [], x, y)


@_edit
def add_association(m: Model, name: str, attributes: list | None = None, x: int | None = None,
                    y: int | None = None):
    """Add an association (relation)."""
    m.add_association(name, attributes or [], x, y)


@_edit
def add_link(m: Model, entity: str, association: str, card: str = "1,n"):
    """Link an entity to an association with a cardinality (0,1 / 1,1 / 0,n / 1,n)."""
    m.add_link(entity, association, card)


@_edit
def set_card(m: Model, entity: str, association: str, card: str):
    """Change the cardinality of an existing link."""
    m.set_card(entity, association, card)


@_edit
def remove_link(m: Model, entity: str, association: str):
    """Remove the link between an entity and an association."""
    m.remove_link(entity, association)


@_edit
def add_attribute(m: Model, owner: str, name: str, type: str = "VARCHAR(50)", pk: bool = False,
                  position: int | None = None):
    """Add an attribute to an entity or association."""
    m.add_attribute(owner, name, type, pk, position)


@_edit
def update_attribute(m: Model, owner: str, name: str, new_name: str | None = None,
                     type: str | None = None, pk: bool | None = None):
    """Rename an attribute or change its type / primary key flag."""
    m.update_attribute(owner, name, new_name, type, pk)


@_edit
def remove_attribute(m: Model, owner: str, name: str):
    """Remove an attribute."""
    m.remove_attribute(owner, name)


@_edit
def rename(m: Model, old: str, new: str):
    """Rename an entity or association."""
    m.rename(old, new)


@_edit
def move(m: Model, name: str, x: int, y: int):
    """Move an entity (top-left corner) or association (centre)."""
    m.move(name, x, y)


@_edit
def remove(m: Model, name: str):
    """Delete an entity or association and its links."""
    m.remove(name)


def mld(path: str):
    """Return the logical model (MLD) as text."""
    return sql.mld_text(_open(path).to_dict())


def mpd(path: str, dialect: str = "generic", out: str | None = None):
    """Return the physical model (MPD) as Markdown; also write it to `out` when given."""
    text = sql.mpd_text(_open(path).to_dict(), dialect)
    if out:
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(text)
    return text


def sql_script(path: str, dialect: str = "generic", out: str | None = None):
    """Return the SQL DDL script; also write it to `out` when given."""
    text = sql.sql_ddl(_open(path).to_dict(), dialect)
    if out:
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(text)
    return text


# name -> (function, JSON schema of extra args, required args)
TOOLS = {
    "read": (read, {}, []),
    "new": (new, {"spec": {"type": "object", "description": "Optional model spec"},
                  "overwrite": {"type": "boolean"}}, []),
    "apply_spec": (apply_spec, {"spec": {"type": "object"}}, ["spec"]),
    "add_entity": (add_entity, {"name": {"type": "string"}, "attributes": ATTR_SCHEMA,
                                "x": {"type": "integer"}, "y": {"type": "integer"}}, ["name"]),
    "add_association": (add_association, {"name": {"type": "string"}, "attributes": ATTR_SCHEMA,
                                          "x": {"type": "integer"}, "y": {"type": "integer"}},
                        ["name"]),
    "add_link": (add_link, {"entity": {"type": "string"}, "association": {"type": "string"},
                            "card": {"type": "string", "description": "0,1 / 1,1 / 0,n / 1,n"}},
                 ["entity", "association"]),
    "set_card": (set_card, {"entity": {"type": "string"}, "association": {"type": "string"},
                            "card": {"type": "string"}}, ["entity", "association", "card"]),
    "remove_link": (remove_link, {"entity": {"type": "string"},
                                  "association": {"type": "string"}}, ["entity", "association"]),
    "add_attribute": (add_attribute, {"owner": {"type": "string"}, "name": {"type": "string"},
                                      "type": {"type": "string"}, "pk": {"type": "boolean"},
                                      "position": {"type": "integer"}}, ["owner", "name"]),
    "update_attribute": (update_attribute, {"owner": {"type": "string"}, "name": {"type": "string"},
                                            "new_name": {"type": "string"},
                                            "type": {"type": "string"}, "pk": {"type": "boolean"}},
                         ["owner", "name"]),
    "remove_attribute": (remove_attribute, {"owner": {"type": "string"},
                                            "name": {"type": "string"}}, ["owner", "name"]),
    "rename": (rename, {"old": {"type": "string"}, "new": {"type": "string"}}, ["old", "new"]),
    "move": (move, {"name": {"type": "string"}, "x": {"type": "integer"},
                    "y": {"type": "integer"}}, ["name", "x", "y"]),
    "remove": (remove, {"name": {"type": "string"}}, ["name"]),
    "mld": (mld, {}, []),
    "mpd": (mpd, {"dialect": {"type": "string", "enum": list(sql.DIALECTS)},
                  "out": {"type": "string", "description": "Optional output .md path"}}, []),
    "sql": (sql_script, {"dialect": {"type": "string", "enum": list(sql.DIALECTS)},
                         "out": {"type": "string", "description": "Optional output .sql path"}}, []),
}


def call(name: str, args: dict):
    fn = TOOLS[name][0]
    return fn(**args)


def to_text(res) -> str:
    return res if isinstance(res, str) else json.dumps(res, ensure_ascii=False, indent=2)
