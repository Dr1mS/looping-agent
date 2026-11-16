"""looping_agent: read, edit and generate Looping (.loo) MCD files without Looping.

Layers:
    archive  byte-exact .loo reader/writer (MFC CArchive format)
    model    entities / associations / links / attributes
    sql      MCD -> MLD -> SQL DDL
    ops      one-shot operations (shared by CLI and MCP)
"""
from .model import Model, ModelError  # noqa: F401
from .archive import LooError  # noqa: F401
