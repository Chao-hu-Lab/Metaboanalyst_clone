import importlib
import builtins
import sys


def test_run_from_config_imports_with_local_package_layout():
    mod = importlib.import_module("scripts.run_from_config")
    assert hasattr(mod, "run_analysis")


def test_core_normalization_does_not_eager_import_qnorm(monkeypatch):
    real_import = builtins.__import__

    def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "qnorm":
            raise AssertionError("qnorm should not be imported at module import time")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    sys.modules.pop("core.normalization", None)
    sys.modules.pop("qnorm", None)

    mod = importlib.import_module("core.normalization")
    assert hasattr(mod, "apply_row_norm")
