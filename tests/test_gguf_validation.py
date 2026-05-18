import struct
import tempfile
from pathlib import Path

from app.tasks import validate_gguf_header


def _make_gguf(version: int = 3, tensor_count: int = 0, kv_count: int = 0) -> bytes:
    header = b"GGUF"
    header += struct.pack("<I", version)
    header += struct.pack("<Q", tensor_count)
    header += struct.pack("<Q", kv_count)
    return header.ljust(64, b"\x00")


def test_valid_gguf():
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(_make_gguf(version=3, tensor_count=10, kv_count=5))
        p = Path(f.name)
    try:
        valid, msg = validate_gguf_header(p)
        assert valid
        assert "GGUF v3" in msg
    finally:
        p.unlink(missing_ok=True)


def test_invalid_magic():
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(b"NOTG" + b"\x00" * 60)
        p = Path(f.name)
    try:
        valid, msg = validate_gguf_header(p)
        assert not valid
        assert "Magic number" in msg
    finally:
        p.unlink(missing_ok=True)


def test_unsupported_version():
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(_make_gguf(version=99, tensor_count=0, kv_count=0))
        p = Path(f.name)
    try:
        valid, msg = validate_gguf_header(p)
        assert not valid
        assert "no soportada" in msg
    finally:
        p.unlink(missing_ok=True)


def test_empty_file():
    with tempfile.NamedTemporaryFile(delete=False) as f:
        p = Path(f.name)
    try:
        valid, msg = validate_gguf_header(p)
        assert not valid
        assert "demasiado pequeño" in msg
    finally:
        p.unlink(missing_ok=True)
