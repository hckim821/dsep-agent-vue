"""Pytest bootstrap — make `wiki_pipeline` and `app.*` importable from tests."""
import os
import sys

_BACKEND_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), os.pardir, "backend")
)
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)
