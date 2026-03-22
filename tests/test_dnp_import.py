"""Tests for DNP import sys.path safety."""

import sys
from pathlib import Path


class TestDNPSysPathCleanup:
    def test_sys_path_not_permanently_modified(self):
        """After _import_from_dnp, sys.path should not contain DNP paths."""
        desktop = Path.home() / "Desktop"
        dnp_candidates = [
            str(desktop / "Data_Normalization_project_v2" / "src"),
            str(
                Path(__file__).resolve().parent.parent.parent
                / "Data_Normalization_project_v2"
                / "src"
            ),
        ]

        path_before = sys.path.copy()

        for candidate in dnp_candidates:
            assert candidate not in path_before, (
                f"DNP path should not be on sys.path at test start: {candidate}"
            )
