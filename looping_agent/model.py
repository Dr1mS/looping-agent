"""High-level MCD (Merise conceptual model) view and editing on top of ``archive``.

Object graph inside a .loo file (recovered from Looping.exe):

* Entity      = CDrawEntite + 3 CDrawTexte (t1 name, t2 attributes, t3 extra)
* Association = CDrawRelation + 3 CDrawTexte (t1 name, t2 attributes, t3 extra)
* Link        = 2 CDrawArc segments (A.next -> B, B.prev -> A); each segment's
                ``owner`` is one end (entity or association). A has 3 CDrawTexte:
                t1 hidden label "Lien N", t2 cardinality (params[0]), t3 extra.
* Attribute   = CUnParametre inside the t2 text of its owner.

Text and arc geometry is recomputed by Looping. Only entity rectangles and
association centre points are stored.
"""
from __future__ import annotations

import base64
import copy
import datetime as _dt
import json
import os
import re
import struct
from dataclasses import dataclass

from . import archive as A

_TPL_PATH = os.path.join(os.path.dirname(__file__), "templates.json")
_TPL = None

ENTITY_W, ENTITY_H = 202, 200


def _templates():
    global _TPL
    if _TPL is None:
        with open(_TPL_PATH, encoding="utf-8") as fh:
            _TPL = json.load(fh)
    return _TPL


def _dec(x):
    if isinstance(x, dict):
        if "__b64__" in x:
            return base64.b64decode(x["__b64__"])
        return {k: _dec(v) for k, v in x.items()}
    if isinstance(x, list):
        return [_dec(v) for v in x]
    return x


def _tpl_obj(key) -> A.Obj:
    t = _templates()[key]
    return A.Obj(t["cls"], _dec(copy.deepcopy(t["f"])), _dec(copy.deepcopy(t["links"])))


class ModelError(Exception):
    pass


# ---------------------------------------------------------------------------
# Attribute types
# ---------------------------------------------------------------------------

_INT_BITS = {0: "TINYINT", 1: "SMALLINT", 2: "INT", 3: "BIGINT"}


def decode_type(p: dict) -> str:
    cat = p["i_20"]
    if cat == 0:  # text
        if p["i_24"] == 1:
            return f"VARCHAR({p['i_70']})"
        if p["i_24"] == 2:
            return "TEXT"
        return f"TEXT_KIND_{p['i_24']}"
    if cat == 1:  # numeric
        if p["i_2c"] == 0:
            return _INT_BITS.get(p["i_30"], "INT")
        if p["i_2c"] == 1:
            return f"DECIMAL({p['i_7c']},{p['i_80']})"
        return f"NUMERIC_KIND_{p['i_2c']}"
    if cat == 2:  # date / time
        if p["i_34"] == 1:
            return "DATE"
        return f"DATETIME_KIND_{p['i_34']}"
    if cat == 4:  # free type: literal text
        return p["s_40"] or "?"
    return f"TYPE_CAT_{cat}"


def encode_type(p: dict, sqltype: str):
    """Set the type fields of a CUnParametre.

    Only the encodings observed in real files are written natively
    (VARCHAR(n), TEXT, INT, DECIMAL(p,s), DATE). Any other type is written as a
    Looping "free type" (literal SQL text), which Looping shows and exports as is.
    """
    t = sqltype.strip()
    u = t.upper().replace(" ", "")
    m_var = re.fullmatch(r"VARCHAR\((\d+)\)", u)
    m_dec = re.fullmatch(r"(?:DECIMAL|NUMERIC)\((\d+),(\d+)\)", u)
    p["s_40"] = ""
    if m_var:
        p.update(i_20=0, i_24=1, i_2c=0, i_70=int(m_var.group(1)))
    elif u == "TEXT":
        p.update(i_20=0, i_24=2, i_2c=0)
    elif u in ("INT", "INTEGER"):
        p.update(i_20=1, i_24=1, i_2c=0, i_30=2)
    elif m_dec:
        p.update(i_20=1, i_24=1, i_2c=1, i_7c=int(m_dec.group(1)), i_80=int(m_dec.group(2)))
    elif u == "DATE":
        p.update(i_20=2, i_24=1, i_2c=0, i_34=1)
    else:
        p.update(i_20=4, i_24=1, i_2c=0, s_40=t)


# ---------------------------------------------------------------------------
# Cardinalities
# ---------------------------------------------------------------------------

# CUnParametre of a link: i_d4 = 1 marks "cardinality", i_d8 = code
# (from the link context menu handler FUN_1400a06b0 in Looping.exe)
_CARD = {0: "0,1", 1: "1,1", 2: "0,n", 3: "1,n"}
_CARD_INV = {v: k for k, v in _CARD.items()}


def decode_card(p: dict | None) -> str:
    if not p:
        return "?"
    return _CARD.get(p["i_d8"], f"?{p['i_d8']}")


def encode_card(p: dict, card: str):
    c = re.sub(r"\s", "", card).lower().replace("*", "n")
    if c not in _CARD_INV:
        raise ModelError(f"bad cardinality {card!r}: use 0,1 / 1,1 / 0,n / 1,n")
    p["i_d4"] = 1
    p["i_d8"] = _CARD_INV[c]


def _ole_now() -> int:
    """COleDateTime (days since 1899-12-30, as a double) packed into an int64."""
    days = (_dt.datetime.now() - _dt.datetime(1899, 12, 30)).total_seconds() / 86400.0
    return struct.unpack("<q", struct.pack("<d", days))[0]


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

@dataclass
class Attr:
    name: str
    type: str
    pk: bool

    def as_dict(self):
        return {"name": self.name, "type": self.type, "pk": self.pk}


class Model:
    def __init__(self, doc: A.Document, path: str | None = None):
        self.doc = doc
        self.path = path

    # -- io --------------------------------------------------------------
    @classmethod
    def open(cls, path: str) -> "Model":
        return cls(A.load(path), path)

    @classmethod
    def new(cls) -> "Model":
        data = base64.b64decode(_templates()["blank_loo"])
        return cls(A.read(data))

    def save(self, path: str | None = None):
        path = path or self.path
        if not path:
            raise ModelError("no output path")
        A.save(self.doc, path)
        self.path = path

    # -- lookup ----------------------------------------------------------
    def _ids(self):
        return self.doc.by_id()

    def _text(self, o: A.Obj, key: str) -> A.Obj | None:
        return self._ids().get(o.links.get(key, 0))

    def _name(self, o: A.Obj) -> str:
        t = self._text(o, "t1")
        return (t.f["lines"][0] if t and t.f["lines"] else "") if t else ""

    def _nodes(self, cls_prefix):
        return [o for o in self.doc.objects if o.cls in cls_prefix]

    def _find(self, name: str, kinds=("entity", "association")) -> A.Obj:
        cands = []
        if "entity" in kinds:
            cands += self._nodes(("CDrawEntite", "CDrawEntiteUML"))
        if "association" in kinds:
            cands += self._nodes(("CDrawRelation",))
        hits = [o for o in cands if self._name(o) == name]
        if not hits:
            hits = [o for o in cands if self._name(o).lower() == name.lower()]
        if not hits:
            raise ModelError(f"no {'/'.join(kinds)} named {name!r}")
        if len(hits) > 1:
            raise ModelError(f"several objects named {name!r}")
        return hits[0]

    def _kind(self, o: A.Obj) -> str:
        return "association" if o.cls == "CDrawRelation" else "entity"

    def _attrs(self, o: A.Obj) -> list[Attr]:
        t = self._text(o, "t2")
        if not t:
            return []
        return [Attr(p["name"], decode_type(p), bool(p["i_08"])) for p in t.f["params"]]

    # -- read API --------------------------------------------------------
    def entities(self):
        out = []
        for o in self._nodes(("CDrawEntite", "CDrawEntiteUML")):
            l, t, r, b = struct.unpack("<4i", o.f["rect"])
            out.append({"name": self._name(o), "id": o.id, "x": l, "y": t, "w": r - l, "h": b - t,
                        "attributes": [a.as_dict() for a in self._attrs(o)]})
        return out

    def associations(self):
        out = []
        for o in self._nodes(("CDrawRelation",)):
            x, y = struct.unpack("<2i", o.f["pt"])
            out.append({"name": self._name(o), "id": o.id, "x": x, "y": y,
                        "attributes": [a.as_dict() for a in self._attrs(o)]})
        return out

    def links(self):
        ids = self._ids()
        out = []
        for a in self.doc.objects:
            if a.cls != "CDrawArc" or not a.links.get("next") or a.links.get("prev"):
                continue
            b = ids.get(a.links["next"])
            ends = [ids.get(a.links.get("owner")), ids.get(b.links.get("owner")) if b else None]
            if any(e is None for e in ends):
                continue
            ent = next((e for e in ends if e.cls != "CDrawRelation"), None)
            rel = next((e for e in ends if e.cls == "CDrawRelation"), None)
            t2 = ids.get(a.links.get("t2"))
            card = decode_card(t2.f["params"][0] if t2 and t2.f["params"] else None)
            out.append({"entity": self._name(ent) if ent else None,
                        "association": self._name(rel) if rel else None,
                        "card": card, "id": a.id})
        return sorted(out, key=lambda l: l["id"])  # creation order

    def other_objects(self):
        known = {"CDrawEntite", "CDrawEntiteUML", "CDrawRelation", "CDrawArc", "CDrawTexte"}
        return [{"class": o.cls, "id": o.id} for o in self.doc.objects if o.cls not in known]

    def to_dict(self):
        return {"format_version": self.doc.version,
                "entities": self.entities(), "associations": self.associations(),
                "links": self.links(), "other_objects": self.other_objects()}

    # -- creation helpers --------------------------------------------------
    def _new(self, key, link_map=None) -> A.Obj:
        o = _tpl_obj(key)
        o.f["id"] = self.doc.next_id()
        self.doc.objects.append(o)
        return o

    def _new_texts(self, key, owner: A.Obj, lines_first: str | None):
        ts = []
        for i, t in enumerate(_templates()[key]):
            o = A.Obj(t["cls"], _dec(copy.deepcopy(t["f"])), _dec(copy.deepcopy(t["links"])))
            o.f["id"] = self.doc.next_id()
            self.doc.objects.append(o)
            o.links.update(t1=0, t2=0, t3=0, prev=0, next=0, owner=owner.id)
            ts.append(o)
        owner.links.update(t1=ts[0].id, t2=ts[1].id, t3=ts[2].id)
        if lines_first is not None:
            ts[0].f["lines"] = [lines_first]
        return ts

    def _new_param(self, name: str, sqltype: str, pk: bool) -> dict:
        p = _dec(copy.deepcopy(_templates()["param"]))
        p["name"] = name
        encode_type(p, sqltype)
        p["i_08"] = 1 if pk else 0
        p["i_88"] = 1 if pk else 0
        p["dt1_value"] = p["dt2_value"] = _ole_now()
        return p

    def _check_free(self, name: str):
        for o in self._nodes(("CDrawEntite", "CDrawEntiteUML", "CDrawRelation")):
            if self._name(o) == name:
                raise ModelError(f"name {name!r} already used")

    def _auto_pos(self):
        xs = [e["x"] + e["w"] for e in self.entities()] + [a["x"] + 60 for a in self.associations()]
        ys = [e["y"] for e in self.entities()]
        return (max(xs) + 150 if xs else 100), (min(ys) if ys else 300)

    # -- edit API --------------------------------------------------------
    def add_entity(self, name: str, attributes=(), x: int | None = None, y: int | None = None):
        self._check_free(name)
        if x is None or y is None:
            ax, ay = self._auto_pos()
            x = ax if x is None else x
            y = ay if y is None else y
        e = self._new("entity")
        e.f["rect"] = struct.pack("<4i", x, y, x + ENTITY_W, y + ENTITY_H)
        e.links.update(t1=0, t2=0, t3=0, prev=0, next=0, owner=0)
        self._new_texts("entity_texts", e, name)
        for a in attributes:
            self.add_attribute(name, **_attr_kwargs(a))
        return e.id

    def add_association(self, name: str, attributes=(), x: int | None = None, y: int | None = None):
        self._check_free(name)
        if x is None or y is None:
            ax, ay = self._auto_pos()
            x = ax if x is None else x
            y = (ay + 100) if y is None else y
        r = self._new("relation")
        r.f["pt"] = struct.pack("<2i", x, y)
        r.links.update(t1=0, t2=0, t3=0, prev=0, next=0, owner=0)
        self._new_texts("relation_texts", r, name)
        for a in attributes:
            self.add_attribute(name, **_attr_kwargs(a))
        return r.id

    def add_attribute(self, owner: str, name: str, type: str = "VARCHAR(50)", pk: bool = False,
                      position: int | None = None):
        o = self._find(owner)
        t = self._text(o, "t2")
        if any(p["name"] == name for p in t.f["params"]):
            raise ModelError(f"{owner} already has attribute {name!r}")
        p = self._new_param(name, type, pk)
        if position is None:
            t.f["params"].append(p)
        else:
            t.f["params"].insert(position, p)

    def _param(self, owner: str, name: str) -> tuple[A.Obj, dict]:
        o = self._find(owner)
        t = self._text(o, "t2")
        for p in t.f["params"]:
            if p["name"] == name:
                return t, p
        raise ModelError(f"{owner} has no attribute {name!r}")

    def update_attribute(self, owner: str, name: str, new_name: str | None = None,
                         type: str | None = None, pk: bool | None = None):
        _, p = self._param(owner, name)
        if new_name:
            p["name"] = new_name
        if type:
            encode_type(p, type)
        if pk is not None:
            p["i_08"] = p["i_88"] = 1 if pk else 0

    def remove_attribute(self, owner: str, name: str):
        t, p = self._param(owner, name)
        t.f["params"].remove(p)

    def rename(self, old: str, new: str):
        self._check_free(new)
        o = self._find(old)
        t = self._text(o, "t1")
        t.f["lines"] = [new]

    def move(self, name: str, x: int, y: int):
        o = self._find(name)
        if o.cls == "CDrawRelation":
            o.f["pt"] = struct.pack("<2i", x, y)
        else:
            l, t, r, b = struct.unpack("<4i", o.f["rect"])
            o.f["rect"] = struct.pack("<4i", x, y, x + r - l, y + b - t)

    def _next_link_label(self) -> str:
        n = 0
        for o in self.doc.objects:
            if o.cls == "CDrawTexte" and o.f["lines"]:
                m = re.fullmatch(r"Lien (\d+)", o.f["lines"][0])
                if m:
                    n = max(n, int(m.group(1)))
        return f"Lien {n + 1}"

    def add_link(self, entity: str, association: str, card: str = "1,n"):
        ent = self._find(entity, ("entity",))
        rel = self._find(association, ("association",))
        a = _tpl_obj("arc_a")
        b = _tpl_obj("arc_b")
        a.f["id"] = self.doc.next_id()
        b.f["id"] = a.f["id"] + 1
        # arcs go first in the list so they are drawn under the boxes
        self.doc.objects[0:0] = [a, b]
        a.links.update(t1=0, t2=0, t3=0, prev=0, next=b.id, owner=ent.id)
        b.links.update(t1=0, t2=0, t3=0, prev=a.id, next=0, owner=rel.id)
        ts = self._new_texts("arc_texts", a, self._next_link_label())
        # move the arc texts next to the arcs, like Looping does
        for t in ts:
            self.doc.objects.remove(t)
        self.doc.objects[2:2] = ts
        p = ts[1].f["params"][0]
        encode_card(p, card)
        p["dt1_value"] = p["dt2_value"] = _ole_now()
        return a.id

    def _link_objs(self, arc_a: A.Obj) -> list[A.Obj]:
        ids = self._ids()
        out = [arc_a]
        b = ids.get(arc_a.links.get("next"))
        if b:
            out.append(b)
        for k in ("t1", "t2", "t3"):
            t = ids.get(arc_a.links.get(k))
            if t:
                out.append(t)
        return out

    def _arc_heads(self, end: A.Obj):
        ids = self._ids()
        heads = []
        for a in self.doc.objects:
            if a.cls.startswith("CDrawArc") and not a.links.get("prev"):
                b = ids.get(a.links.get("next"))
                owners = {a.links.get("owner"), b.links.get("owner") if b else None}
                if end.id in owners:
                    heads.append(a)
        return heads

    def set_card(self, entity: str, association: str, card: str):
        ent = self._find(entity, ("entity",))
        rel = self._find(association, ("association",))
        ids = self._ids()
        for a in self._arc_heads(ent):
            b = ids.get(a.links.get("next"))
            if b and rel.id in (a.links.get("owner"), b.links.get("owner")):
                encode_card(ids[a.links["t2"]].f["params"][0], card)
                return
        raise ModelError(f"no link between {entity} and {association}")

    def remove_link(self, entity: str, association: str):
        ent = self._find(entity, ("entity",))
        rel = self._find(association, ("association",))
        ids = self._ids()
        for a in self._arc_heads(ent):
            b = ids.get(a.links.get("next"))
            if b and rel.id in (a.links.get("owner"), b.links.get("owner")):
                for o in self._link_objs(a):
                    self.doc.objects.remove(o)
                return
        raise ModelError(f"no link between {entity} and {association}")

    def remove(self, name: str):
        o = self._find(name)
        doomed = []
        for a in self._arc_heads(o):
            doomed += self._link_objs(a)
        ids = self._ids()
        doomed.append(o)
        for k in ("t1", "t2", "t3"):
            t = ids.get(o.links.get(k))
            if t:
                doomed.append(t)
        keep = {id(x) for x in doomed}
        self.doc.objects = [x for x in self.doc.objects if id(x) not in keep]

    # -- bulk ------------------------------------------------------------
    def apply_spec(self, spec: dict):
        """Create objects from a JSON spec (same shape as ``to_dict``)."""
        for e in spec.get("entities", []):
            self.add_entity(e["name"], e.get("attributes", []), e.get("x"), e.get("y"))
        for r in spec.get("associations", []):
            self.add_association(r["name"], r.get("attributes", []), r.get("x"), r.get("y"))
        for l in spec.get("links", []):
            self.add_link(l["entity"], l["association"], l.get("card", "1,n"))


def _attr_kwargs(a) -> dict:
    if isinstance(a, str):
        return {"name": a}
    return {"name": a["name"], "type": a.get("type", "VARCHAR(50)"), "pk": bool(a.get("pk", False))}
