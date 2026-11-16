"""Command line: python3 -m looping_agent <command> <file.loo> [options]

Examples:
  python3 -m looping_agent read  modele.loo
  python3 -m looping_agent new   modele.loo --spec spec.json
  python3 -m looping_agent add_entity modele.loo --name Client \
      --attributes '[{"name":"idClient","type":"INT","pk":true},"nom"]'
  python3 -m looping_agent add_link modele.loo --entity Client --association passer --card 1,n
  python3 -m looping_agent sql   modele.loo --dialect postgresql --out schema.sql
  python3 -m looping_agent mcp   (start the MCP server on stdio)
"""
from __future__ import annotations

import argparse
import json
import sys

from . import ops


def _value(s: str, typ: dict):
    t = typ.get("type")
    if t == "integer":
        return int(s)
    if t == "boolean":
        return s.lower() in ("1", "true", "yes", "oui")
    if t in ("array", "object") or "anyOf" in typ:
        if t == "object" and not s.lstrip().startswith("{"):
            with open(s, encoding="utf-8") as fh:  # a path to a JSON file
                return json.load(fh)
        return json.loads(s)
    return s


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] == "mcp":
        from .mcp_server import main as serve
        return serve()
    ap = argparse.ArgumentParser(prog="looping_agent", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, (fn, props, req) in ops.TOOLS.items():
        sp = sub.add_parser(name, help=(fn.__doc__ or "").strip().splitlines()[0])
        sp.add_argument("path")
        for k, typ in props.items():
            sp.add_argument(f"--{k}", required=k in req, help=typ.get("description"))
    a = ap.parse_args(argv)
    props = ops.TOOLS[a.cmd][1]
    args = {k: _value(v, props[k]) for k, v in vars(a).items()
            if k in props and v is not None}
    try:
        res = ops.call(a.cmd, {"path": a.path, **args})
    except Exception as e:
        print(f"error: {type(e).__name__}: {e}", file=sys.stderr)
        return 1
    print(ops.to_text(res))
    return 0


if __name__ == "__main__":
    sys.exit(main())
