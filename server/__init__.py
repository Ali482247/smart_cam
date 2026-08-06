"""Importing `server` (or any submodule) always initializes `server.protocol` first,
since Python initializes parent packages before submodules. That guarantees the
protoc-generated modules' sys.path patch (server/protocol/__init__.py) runs before any
submodule tries `import device_pb2` etc., regardless of import order within that
submodule's own file.
"""

from __future__ import annotations

import server.protocol  # noqa: F401
