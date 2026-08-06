"""Makes the protoc-generated *_pb2 modules importable.

protoc's Python codegen emits flat, unqualified imports between generated files
(e.g. envelope_pb2.py does `import device_pb2`), which only resolves if the generated
directory itself is on sys.path - it cannot be imported as a dotted submodule package.
This is a known protoc/Python limitation, not a bug in our setup.
"""

from __future__ import annotations

import sys
from pathlib import Path

_generated_dir = Path(__file__).resolve().parent / "generated"
if str(_generated_dir) not in sys.path:
    sys.path.insert(0, str(_generated_dir))
