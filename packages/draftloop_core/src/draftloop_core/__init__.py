"""DraftLoop core — shared types, errors, config, LLM shim, storage protocols.

Submodules: ``types``, ``errors``, ``config``, ``obs``, ``llm``, ``storage``.
Each is imported lazily via Python's normal submodule loading
(``from draftloop_core.errors import IngestError`` etc.).
"""

__version__ = "0.1.0"
