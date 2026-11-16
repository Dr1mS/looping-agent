"""MCD -> MLD -> SQL DDL, following the usual Merise rules.

* Each entity becomes a table; its identifier attributes become the primary key.
* A binary association with a (0,1) or (1,1) side moves into that entity:
  the other entity's key becomes a foreign key, plus the association's attributes.
* Any other association becomes a table whose primary key is the union of the
  keys of the linked entities (each also a foreign key), plus its attributes.
"""
from __future__ import annotations

import re

DIALECTS = ("generic", "mysql", "postgresql", "sqlite")


def _quote(name: str, dialect: str) -> str:
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        return name
    if dialect == "mysql":
        return f"`{name}`"
    return f'"{name}"'


def build_mld(model_dict: dict) -> list[dict]:
    ents = {e["name"]: e for e in model_dict["entities"]}
    tables: dict[str, dict] = {}
    for e in model_dict["entities"]:
        cols = [{"name": a["name"], "type": a["type"], "pk": a["pk"], "null": not a["pk"], "fk": None}
                for a in e["attributes"]]
        tables[e["name"]] = {"name": e["name"], "columns": cols}

    def pk_cols(ent):
        return [c for c in tables[ent]["columns"] if c["pk"]]

    links_by_assoc: dict[str, list[dict]] = {}
    for l in model_dict["links"]:
        if l["entity"] and l["association"]:
            links_by_assoc.setdefault(l["association"], []).append(l)

    for r in model_dict["associations"]:
        ls = links_by_assoc.get(r["name"], [])
        ones = [l for l in ls if l["card"].endswith(",1")]
        if len(ls) == 2 and ones:
            child = ones[0]
            parent = next(l for l in ls if l is not child)
            t = tables[child["entity"]]
            mandatory = child["card"].startswith("1")
            for c in pk_cols(parent["entity"]):
                cname = c["name"]
                if any(x["name"] == cname for x in t["columns"]):
                    cname = f"{cname}_{r['name']}"
                t["columns"].append({"name": cname, "type": c["type"], "pk": False,
                                     "null": not mandatory,
                                     "fk": (parent["entity"], c["name"]), "via": r["name"]})
            for a in r["attributes"]:
                t["columns"].append({"name": a["name"], "type": a["type"], "pk": False,
                                     "null": True, "fk": None})
        else:
            cols = []
            seen = set()
            for l in ls:
                for c in pk_cols(l["entity"]):
                    cname = c["name"]
                    while cname in seen:
                        cname = f"{cname}_{l['entity']}"
                    seen.add(cname)
                    cols.append({"name": cname, "type": c["type"], "pk": True, "null": False,
                                 "fk": (l["entity"], c["name"])})
            for a in r["attributes"]:
                cols.append({"name": a["name"], "type": a["type"], "pk": bool(a["pk"]),
                             "null": not a["pk"], "fk": None})
            tables[r["name"]] = {"name": r["name"], "columns": cols}
    return list(tables.values())


def mld_text(model_dict: dict) -> str:
    """Textual MLD: Table(#pk, attr, fk#)."""
    lines = []
    for t in build_mld(model_dict):
        parts = []
        for c in t["columns"]:
            n = c["name"]
            if c["pk"] and c["fk"]:
                parts.append(f"#{n}*")
            elif c["pk"]:
                parts.append(f"#{n}")
            elif c["fk"]:
                parts.append(f"{n}*")
            else:
                parts.append(n)
        lines.append(f"{t['name']}({', '.join(parts)})")
    lines.append("")
    lines.append("# = primary key, * = foreign key")
    return "\n".join(lines)


def mpd_text(model_dict: dict, dialect: str = "generic") -> str:
    """Physical model (MPD) as Markdown: one table per relation with types and constraints."""
    out = [f"# MPD ({dialect})", ""]
    for t in _topo(build_mld(model_dict)):
        out.append(f"## {t['name']}")
        out.append("")
        out.append("| Colonne | Type | NULL | Clé | Référence |")
        out.append("|---|---|---|---|---|")
        for c in t["columns"]:
            key = "PK" + (", FK" if c["fk"] else "") if c["pk"] else ("FK" if c["fk"] else "")
            ref = f"{c['fk'][0]}({c['fk'][1]})" if c["fk"] else ""
            out.append(f"| {c['name']} | {_sqltype(c['type'], dialect)} | "
                       f"{'oui' if c['null'] else 'non'} | {key} | {ref} |")
        fks = [c for c in t["columns"] if c["fk"] and not c["pk"]]
        if fks:
            out.append("")
            out.append("Index conseillés : " + ", ".join(f"`{c['name']}`" for c in fks))
        out.append("")
    return "\n".join(out)


def _sqltype(t: str, dialect: str) -> str:
    u = t.upper()
    if dialect == "sqlite":
        if u.startswith(("INT", "TINYINT", "SMALLINT", "BIGINT")):
            return "INTEGER"
    if dialect == "postgresql":
        if u == "TINYINT":
            return "SMALLINT"
        if u in ("DATETIME",):
            return "TIMESTAMP"
        if u in ("LOGICAL",):
            return "BOOLEAN"
    return t


def _topo(tables: list[dict]) -> list[dict]:
    """Order tables so referenced tables are created first (cycles keep input order)."""
    done: list[dict] = []
    names: set[str] = set()
    pending = list(tables)
    while pending:
        progress = False
        for t in list(pending):
            deps = {c["fk"][0] for c in t["columns"] if c["fk"]} - {t["name"]}
            if deps <= names:
                done.append(t)
                names.add(t["name"])
                pending.remove(t)
                progress = True
        if not progress:
            done += pending
            break
    return done


def sql_ddl(model_dict: dict, dialect: str = "generic") -> str:
    if dialect not in DIALECTS:
        raise ValueError(f"dialect must be one of {DIALECTS}")
    q = lambda n: _quote(n, dialect)
    tables = _topo(build_mld(model_dict))
    out = []
    created: set[str] = set()
    deferred: list[str] = []
    for t in tables:
        created.add(t["name"])
        if not t["columns"]:
            out.append(f"-- {t['name']}: no attribute, table skipped (add an identifier)")
            continue
        rows = []
        for c in t["columns"]:
            rows.append(f"   {q(c['name'])} {_sqltype(c['type'], dialect)}"
                        + ("" if c["null"] else " NOT NULL"))
        pks = [q(c["name"]) for c in t["columns"] if c["pk"]]
        if pks:
            rows.append(f"   PRIMARY KEY({', '.join(pks)})")
        for c in t["columns"]:
            if not c["fk"]:
                continue
            ref = f"FOREIGN KEY({q(c['name'])}) REFERENCES {q(c['fk'][0])}({q(c['fk'][1])})"
            # a reference to a table not created yet (cycle): add it after all tables.
            # SQLite cannot ALTER TABLE ADD CONSTRAINT but accepts forward references.
            if c["fk"][0] in created or dialect == "sqlite":
                rows.append(f"   {ref}")
            else:
                deferred.append(f"ALTER TABLE {q(t['name'])} ADD {ref};")
        out.append(f"CREATE TABLE {q(t['name'])}(\n" + ",\n".join(rows) + "\n);")
    if deferred:
        out.append("\n".join(deferred))
    return "\n\n".join(out) + "\n"
