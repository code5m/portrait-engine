"""Shared source identity: capture, Blender and assessor must agree exactly."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def source_digest():
    h=hashlib.sha256()
    for name in sorted(json.loads((ROOT/'research/sketch/s1-sources.json').read_text())):
        h.update(name.encode()+b'\0'+(ROOT/name).read_bytes()+b'\0')
    return h.hexdigest()
