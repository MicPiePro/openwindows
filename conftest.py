"""Root pytest bootstrap: make the repo root importable for pure-module tests.

OpenWindows' pure modules (psychro, engine, zones) are tested with plain
pytest. At this stage custom_components/openwindows has no __init__.py, so it
resolves as a PEP 420 namespace package; adding the repo root to sys.path lets
`from custom_components.openwindows.psychro import dew_point` work.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
