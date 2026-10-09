"""Shared test bootstrap: expose the Quantumult package as importable modules."""
import importlib.util
from pathlib import Path
import sys

TESTS = Path(__file__).resolve().parent
QX = TESTS.parent           # .../Quantumult
REPO = QX.parent            # repository root

if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))


def load(relative_path, name=None):
    """Import a module by file path, registering it so sibling imports resolve."""
    path = REPO / relative_path
    mod_name = name or path.stem
    spec = importlib.util.spec_from_file_location(mod_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = module
    spec.loader.exec_module(module)
    return module
