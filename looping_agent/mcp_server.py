"""Minimal MCP server (stdio, JSON-RPC 2.0, no dependency).

Register in Claude Code:
    claude mcp add looping -- python3 -m looping_agent.mcp_server
(run from the folder that holds ``looping_agent``, or set PYTHONPATH).
"""
from __future__ import annotations

import json
import sys
import traceback

from . import ops

PROTOCOL = "2025-06-18"


def _tools():
    out = []
    for name, (fn, props, req) in ops.TOOLS.items():
        schema = {"type": "object", "properties": {"path": ops.P, **props},
                  "required": ["path", *req]}
        out.append({"name": f"loo_{name}", "description": (fn.__doc__ or name).strip(),
                    "inputSchema": schema})
    return out


def handle(msg: dict):
    method = msg.get("method")
    if method == "initialize":
        return {"protocolVersion": msg.get("params", {}).get("protocolVersion", PROTOCOL),
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "looping", "version": "0.1.0"},
                "instructions": "Read and edit Looping (.loo) MCD files: entities, associations, "
                                "links, attributes; export MLD, MPD and SQL. Edits keep <file>.bak. "
                                "Paths: absolute, ~/..., or relative to the working folder "
                                f"{ops.work_dir()} (set LOOPING_DIR to change it). Results "
                                "give the full path of the file to open in Looping."}
    if method == "ping":
        return {}
    if method == "tools/list":
        return {"tools": _tools()}
    if method == "tools/call":
        p = msg.get("params", {})
        name = p.get("name", "")
        args = dict(p.get("arguments") or {})
        if not name.startswith("loo_") or name[4:] not in ops.TOOLS:
            raise KeyError(f"unknown tool {name}")
        try:
            res = ops.call(name[4:], args, use_work_dir=True)
            return {"content": [{"type": "text", "text": ops.to_text(res)}], "isError": False}
        except Exception as e:  # tool errors go back to the model, not as protocol errors
            return {"content": [{"type": "text", "text": f"{type(e).__name__}: {e}"}],
                    "isError": True}
    raise NotImplementedError(method)


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        if "id" not in msg:  # notification
            continue
        try:
            reply = {"jsonrpc": "2.0", "id": msg["id"], "result": handle(msg)}
        except NotImplementedError as e:
            reply = {"jsonrpc": "2.0", "id": msg["id"],
                     "error": {"code": -32601, "message": f"method not found: {e}"}}
        except Exception as e:
            traceback.print_exc(file=sys.stderr)
            reply = {"jsonrpc": "2.0", "id": msg["id"],
                     "error": {"code": -32603, "message": str(e)}}
        sys.stdout.write(json.dumps(reply, ensure_ascii=False) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
