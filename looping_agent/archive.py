"""Low-level reader/writer for Looping ``.loo`` files.

A ``.loo`` file is an MFC ``CArchive`` stream written by ``CLoopingDoc::Serialize``.
The layout below was recovered from Looping.exe (x64, 2025-03-06 build) with Ghidra.

Every field is read and written by the *same* schema function (see ``IO``), so a
file that is read and written back without changes is byte-identical.
Unknown or unused fields are kept as raw values, so they survive a round trip.

Stream layout (document version >= 42):

    header        fixed fields + 0x88c-byte settings blob (version = first int32)
    vues          CTypedPtrList<CObList, CUneVueUrbanisme*>   (version > 43)
    89 CStrings   SQL/DBMS settings
    objects       CObList of CDrawObj subclasses (MFC class tags)
    link pass     for each object: 6 object ids (+ CRattach for arcs)
"""
from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import Any

MIN_VERSION = 42
LATEST_VERSION = 51

ARC_CLASSES = {
    "CDrawArc", "CDrawArcCif", "CDrawArcContrainte", "CDrawArcHeritage",
    "CDrawArcHeritageUML", "CDrawArcObjetLibre", "CDrawArcRegle",
}
SUPPORTED_CLASSES = ARC_CLASSES | {
    "CDrawTexte", "CDrawEntite", "CDrawEntiteUML", "CDrawRelation", "CDrawHeritage",
}


class LooError(Exception):
    pass


class IO:
    """Symmetric serializer: the same calls read (mode 'r') or write (mode 'w')."""

    def __init__(self, mode: str, data: bytes = b"", version: int = 0):
        self.mode = mode
        self.data = data
        self.pos = 0
        self.out = bytearray()
        self.version = version

    # -- primitives -------------------------------------------------------
    def _fmt(self, f: dict, k: str, fmt: str):
        if self.mode == "r":
            size = struct.calcsize(fmt)
            if self.pos + size > len(self.data):
                raise LooError(f"unexpected end of file reading {k!r} at {self.pos:#x}")
            f[k] = struct.unpack_from(fmt, self.data, self.pos)[0]
            self.pos += size
        else:
            self.out += struct.pack(fmt, f[k])
        return f[k]

    def i32(self, f, k):
        return self._fmt(f, k, "<i")

    def u16(self, f, k):
        return self._fmt(f, k, "<H")

    def i64(self, f, k):
        return self._fmt(f, k, "<q")

    def raw(self, f, k, n):
        if self.mode == "r":
            if self.pos + n > len(self.data):
                raise LooError(f"unexpected end of file reading {k!r} at {self.pos:#x}")
            f[k] = bytes(self.data[self.pos:self.pos + n])
            self.pos += n
        else:
            v = f[k]
            if len(v) != n:
                raise LooError(f"field {k!r} must be {n} bytes, got {len(v)}")
            self.out += v
        return f[k]

    def count(self, f, k):
        """MFC CArchive::ReadCount / WriteCount."""
        if self.mode == "r":
            n = self._u16()
            if n == 0xFFFF:
                n = self._u32()
            f[k] = n
        else:
            n = f[k]
            if n < 0xFFFF:
                self.out += struct.pack("<H", n)
            else:
                self.out += struct.pack("<HI", 0xFFFF, n)
        return f[k]

    def str(self, f, k):
        """MFC CString (AfxReadStringLength / WriteStringLength), always written as Unicode."""
        if self.mode == "r":
            f[k] = self._read_cstring()
        else:
            self._write_cstring(f[k])
        return f[k]

    def strlist(self, f, k):
        """CStringList::Serialize: count + strings."""
        if self.mode == "r":
            tmp = {}
            n = self.count(tmp, "n")
            f[k] = [self._read_cstring() for _ in range(n)]
        else:
            self.count({"n": len(f[k])}, "n")
            for s in f[k]:
                self._write_cstring(s)
        return f[k]

    # -- helpers ----------------------------------------------------------
    def _u8(self):
        v = self.data[self.pos]
        self.pos += 1
        return v

    def _u16(self):
        v = struct.unpack_from("<H", self.data, self.pos)[0]
        self.pos += 2
        return v

    def _u32(self):
        v = struct.unpack_from("<I", self.data, self.pos)[0]
        self.pos += 4
        return v

    def _read_cstring(self) -> str:
        unicode = False
        n = self._u8()
        if n == 0xFF:
            n = self._u16()
            if n == 0xFFFE:
                unicode = True
                n = self._u8()
                if n == 0xFF:
                    n = self._u16()
                    if n == 0xFFFF:
                        n = self._u32()
            elif n == 0xFFFF:
                n = self._u32()
        if unicode:
            raw = self.data[self.pos:self.pos + 2 * n]
            self.pos += 2 * n
            return raw.decode("utf-16-le")
        raw = self.data[self.pos:self.pos + n]
        self.pos += n
        return raw.decode("cp1252")

    def _write_cstring(self, s: str):
        b = s.encode("utf-16-le")
        n = len(b) // 2
        self.out += b"\xff\xfe\xff"
        if n < 0xFF:
            self.out += struct.pack("<B", n)
        elif n < 0xFFFE:
            self.out += struct.pack("<BH", 0xFF, n)
        else:
            self.out += struct.pack("<BHI", 0xFF, 0xFFFF, n)
        self.out += b


# ---------------------------------------------------------------------------
# Object schemas (mirror of the Serialize methods in Looping.exe)
# ---------------------------------------------------------------------------

def ser_drawobj(io: IO, f: dict):
    """CDrawObj::Serialize (FUN_1400b2980)."""
    io.i32(f, "kind")            # +0x140 object kind: 1 relation, 4 entity, 0x20 arc, 0x40 text ...
    for k in ("w_d8", "w_e4", "w_dc", "w_ec", "w_e0", "w_f4"):
        io.u16(f, k)
    io.raw(f, "pen1", 16)
    io.raw(f, "brush1", 12)
    io.raw(f, "pen2", 16)
    io.raw(f, "brush2", 12)
    io.raw(f, "pen3", 16)
    io.raw(f, "brush3", 12)
    io.i32(f, "id")              # +0x10 object id (used by link pass)
    for k in ("i_308", "i_30c", "i_310", "i_314", "i_318"):
        io.i32(f, k)
    for k in ("w_e8", "w_f0", "w_f8"):
        io.u16(f, k)
    io.raw(f, "brush4", 12)
    io.raw(f, "brush5", 12)
    io.raw(f, "brush6", 12)
    if io.version >= 0x2D:
        io.i32(f, "i_338")


def ser_param(io: IO, f: dict):
    """CUnParametre slot 0 (FUN_1400a6800): one attribute / one text line."""
    v = io.version
    io.i32(f, "i_08")
    io.str(f, "name")
    for k in ("i_20", "i_24", "i_28"):
        io.i32(f, k)
    for k in ("s_48", "s_50", "s_58"):
        io.str(f, k)
    io.i32(f, "i_60")
    for k in ("s_18", "s_118", "s_138"):
        io.str(f, k)
    for k in ("i_140", "i_144", "i_14c", "i_148",
              "i_2c", "i_30", "i_34", "i_38",
              "i_84", "i_88", "i_8c", "i_90"):
        io.i32(f, k)
    io.str(f, "s_98")
    io.i64(f, "q_a0")
    io.i32(f, "i_a8")
    io.i32(f, "dt1_status")
    io.i64(f, "dt1_value")
    io.i32(f, "dt2_status")
    io.i64(f, "dt2_value")
    for k in ("i_d0", "i_64", "i_68", "i_6c", "i_70", "i_74", "i_78",
              "i_7c", "i_80", "i_d4", "i_d8"):
        io.i32(f, k)
    for k in ("s_e0", "s_e8", "s_f0"):
        io.str(f, k)
    if v >= 0x11:
        io.i32(f, "i_12c")
    if v > 0x11:
        io.i32(f, "i_130")
    if v >= 0x1F:
        io.i32(f, "i_134")
    io.str(f, "s_f8")
    io.str(f, "s_100")
    for k in ("i_108", "i_10c", "i_110", "i_114"):
        io.i32(f, k)
    io.str(f, "s_120")
    io.str(f, "s_40")
    io.i32(f, "i_128")


def ser_texte(io: IO, f: dict):
    """CDrawTexte::Serialize (FUN_1400e52c0)."""
    ser_drawobj(io, f)
    io.i32(f, "i_458")
    io.i32(f, "i_45c")
    io.strlist(f, "lines")       # +0x468 visible text (entity / association / link name)
    io.strlist(f, "lines2")      # +0x4a0
    io.i32(f, "i_4d8")
    io.str(f, "s_5f8")
    if io.version > 0x29:
        io.i32(f, "i_460")
        io.i32(f, "x1")
        io.i32(f, "x2")
    io.raw(f, "font1a", 100)
    io.raw(f, "font1b", 92)
    io.raw(f, "font2a", 100)
    io.raw(f, "font2b", 92)
    io.u16(f, "w_4dc")
    if io.mode == "r":
        n = io.i32(f, "_nparams")
        f["params"] = []
        for _ in range(n):
            p: dict = {}
            ser_param(io, p)
            f["params"].append(p)
    else:
        io.i32({"n": len(f["params"])}, "n")
        for p in f["params"]:
            ser_param(io, p)


def ser_entite(io: IO, f: dict):
    """CDrawEntite / CDrawEntiteUML::Serialize (FUN_1400c4210)."""
    ser_drawobj(io, f)
    io.u16(f, "flags")
    io.raw(f, "rect", 16)        # +0x4d0 position (left, top, right, bottom)


def ser_relation(io: IO, f: dict):
    """CDrawRelation::Serialize (FUN_1400ddba0)."""
    ser_drawobj(io, f)
    io.raw(f, "pt", 8)           # +0x390 centre point (x, y)
    io.i32(f, "i_398")
    io.i32(f, "i_3a0")
    io.raw(f, "size", 8)         # +0x3a4
    io.i32(f, "i_3ac")
    io.i32(f, "i_39c")
    io.i32(f, "x1")
    io.i32(f, "x2")
    io.str(f, "s_tmp")


def ser_arc(io: IO, f: dict):
    """CDrawArc::Serialize (FUN_140099af0), shared by every CDrawArc* class."""
    ser_drawobj(io, f)
    io.i32(f, "i_3c8")
    io.i32(f, "i_3cc")
    io.i32(f, "i_3d0")
    io.str(f, "s_3d8")


def ser_heritage(io: IO, f: dict):
    """CDrawHeritage::Serialize (FUN_1400cf940)."""
    ser_drawobj(io, f)
    io.u16(f, "w_heritage")
    io.raw(f, "r_41c", 16)
    io.raw(f, "r_42c", 16)
    if io.version > 0x32:
        io.i32(f, "i_418")


SCHEMAS = {
    "CDrawTexte": ser_texte,
    "CDrawEntite": ser_entite,
    "CDrawEntiteUML": ser_entite,
    "CDrawRelation": ser_relation,
    "CDrawHeritage": ser_heritage,
    **{c: ser_arc for c in ARC_CLASSES},
}

LINK_KEYS = ("t1", "t2", "t3", "prev", "next", "owner")


def ser_links(io: IO, cls: str, f: dict):
    """Second pass, CDrawObj slot 3 (FUN_1400b3840) + CRattach for arcs."""
    for k in LINK_KEYS:
        io.i32(f, k)
    if cls in ARC_CLASSES:
        io.u16(f, "att_w")
        io.raw(f, "att_pt", 8)
        io.i32(f, "att_i")


# ---------------------------------------------------------------------------
# Document
# ---------------------------------------------------------------------------

@dataclass
class Obj:
    cls: str
    f: dict
    links: dict = field(default_factory=dict)

    @property
    def id(self) -> int:
        return self.f["id"]


@dataclass
class Document:
    header: dict
    objects: list[Obj]
    class_schema: dict[str, int] = field(default_factory=dict)

    @property
    def version(self) -> int:
        return self.header["version"]

    def by_id(self) -> dict[int, Obj]:
        return {o.id: o for o in self.objects}

    def next_id(self) -> int:
        return max([o.id for o in self.objects] + [0]) + 1


def _ser_header(io: IO, h: dict):
    io.raw(h, "h_1910", 8)
    io.i32(h, "i_191c")
    io.i32(h, "i_334")
    io.u16(h, "w_338")
    io.u16(h, "w_33c")
    io.raw(h, "r_350", 4)
    io.raw(h, "settings", 0x88C)
    if io.mode == "r":
        h["version"] = struct.unpack_from("<i", h["settings"], 0)[0]
        io.version = h["version"]
        if io.version < MIN_VERSION:
            raise LooError(f"file version {io.version} is too old (need >= {MIN_VERSION}); "
                           "open and save it once with a recent Looping")
        if io.version > LATEST_VERSION:
            raise LooError(f"file version {io.version} is newer than supported ({LATEST_VERSION})")
    io.raw(h, "view1", 8)
    io.raw(h, "view2", 8)
    v = io.version
    if v > 0x1C:
        io.u16(h, "w_340")
    if v > 0x30:
        io.str(h, "s_348")


def _ser_strings(io: IO, h: dict):
    if io.mode == "r":
        h["strings"] = []
    n = 33 + (51 if io.version > 0x12 else 0) + (3 if io.version > 0x12 else 0) \
        + (2 if io.version > 0x23 else 0)
    if io.mode == "r":
        tmp: dict = {}
        for _ in range(n):
            h["strings"].append(io.str(tmp, "s"))
    else:
        if len(h["strings"]) != n:
            raise LooError("bad settings string count")
        for s in h["strings"]:
            io.str({"s": s}, "s")


def read(data: bytes) -> Document:
    io = IO("r", data)
    h: dict = {}
    _ser_header(io, h)
    classes: dict[int, str] = {}
    schema: dict[str, int] = {}
    map_count = 1

    def read_tag():
        nonlocal map_count
        tag = io._u16()
        if tag == 0x7FFF:
            big = io._u32()
            is_class = bool(big & 0x80000000)
            idx = big & 0x7FFFFFFF
        elif tag == 0xFFFF:
            sch = io._u16()
            ln = io._u16()
            name = io.data[io.pos:io.pos + ln].decode("ascii")
            io.pos += ln
            classes[map_count] = name
            schema[name] = sch
            map_count += 1
            map_count += 1  # the object itself
            return name
        else:
            is_class = bool(tag & 0x8000)
            idx = tag & 0x7FFF
        if not is_class:
            if idx == 0:
                return None
            raise LooError(f"object back-reference {idx} not supported at {io.pos:#x}")
        if idx not in classes:
            raise LooError(f"unknown class index {idx} at {io.pos:#x}")
        map_count += 1
        return classes[idx]

    # vues d'urbanisation (CUneVueUrbanisme), stored with object tags
    h["vues"] = []
    if io.version > 0x2B:
        n = io.count({}, "n")
        for _ in range(n):
            cls = read_tag()
            if cls != "CUneVueUrbanisme":
                raise LooError(f"unexpected class {cls} in view list")
            vf: dict = {}
            io.i32(vf, "num")
            io.str(vf, "name")
            h["vues"].append(vf)
    _ser_strings(io, h)

    n = io.count({}, "n")
    objects: list[Obj] = []
    for _ in range(n):
        at = io.pos
        cls = read_tag()
        if cls is None:
            raise LooError(f"NULL object in object list at {at:#x}")
        if cls not in SCHEMAS:
            raise LooError(f"object class {cls} is not supported yet (at {at:#x})")
        f: dict = {}
        SCHEMAS[cls](io, f)
        objects.append(Obj(cls, f))
    for o in objects:
        ser_links(io, o.cls, o.links)
    if io.pos != len(data):
        raise LooError(f"{len(data) - io.pos} trailing bytes after link pass")
    return Document(h, objects, schema)


def write(doc: Document) -> bytes:
    io = IO("w", version=doc.version)
    h = doc.header
    _ser_header(io, h)
    class_idx: dict[str, int] = {}
    map_count = 1

    def write_tag(cls: str):
        nonlocal map_count
        if cls in class_idx:
            idx = class_idx[cls]
            if idx < 0x7FFF:
                io.out += struct.pack("<H", 0x8000 | idx)
            else:
                io.out += struct.pack("<HI", 0x7FFF, 0x80000000 | idx)
        else:
            name = cls.encode("ascii")
            io.out += struct.pack("<HHH", 0xFFFF, doc.class_schema.get(cls, 0), len(name)) + name
            class_idx[cls] = map_count
            map_count += 1
        map_count += 1

    if io.version > 0x2B:
        io.count({"n": len(h["vues"])}, "n")
        for vf in h["vues"]:
            write_tag("CUneVueUrbanisme")
            io.i32(vf, "num")
            io.str(vf, "name")
    _ser_strings(io, h)
    io.count({"n": len(doc.objects)}, "n")
    for o in doc.objects:
        write_tag(o.cls)
        SCHEMAS[o.cls](io, o.f)
    for o in doc.objects:
        ser_links(io, o.cls, o.links)
    return bytes(io.out)


def load(path: str) -> Document:
    with open(path, "rb") as fh:
        return read(fh.read())


def save(doc: Document, path: str):
    data = write(doc)
    read(data)  # self-check: never write a file we cannot read back
    with open(path, "wb") as fh:
        fh.write(data)
