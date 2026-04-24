"""Map legacy ``ms_core.processing`` imports to local ``core`` modules."""

from importlib import import_module
import sys


_ALIASES = {
    "batch_correction": "core.batch_correction",
    "feature_filter": "core.filtering",
    "missing_values": "core.missing_values",
    "normalization": "core.normalization",
    "scaling": "core.scaling",
    "transformation": "core.transformation",
}


for legacy_name, target_name in _ALIASES.items():
    sys.modules[f"{__name__}.{legacy_name}"] = import_module(target_name)
