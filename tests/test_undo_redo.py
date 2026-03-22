"""Tests for undo/redo label and stage preservation."""

import pandas as pd


class FakeMainWindow:
    """Minimal stub that mirrors the fields ProcessingStepCommand touches."""

    def __init__(self):
        self.current_data = None
        self.labels = None
        self._stage = 0

    def _on_data_state_changed(self):
        pass


class TestProcessingStepCommandPreservesLabelsAndStage:
    def test_undo_restores_labels_and_stage(self):
        from gui.main_window import ProcessingStepCommand

        mw = FakeMainWindow()
        old_df = pd.DataFrame({"A": [1, 2]}, index=["S1", "S2"])
        old_labels = pd.Series(["G1", "G2"], index=["S1", "S2"])
        mw.current_data = old_df.copy()
        mw.labels = old_labels.copy()
        mw._stage = 2

        new_df = pd.DataFrame({"A": [10]}, index=["S1"])
        new_labels = pd.Series(["G1"], index=["S1"])

        cmd = ProcessingStepCommand(
            mw,
            "filter",
            new_df,
            old_df,
            new_labels=new_labels,
            old_labels=old_labels,
            new_stage=3,
            old_stage=2,
        )
        cmd.redo()

        assert mw.current_data.shape == (1, 1)
        pd.testing.assert_series_equal(mw.labels, new_labels)
        assert mw._stage == 3

        cmd.undo()

        assert mw.current_data.shape == (2, 1)
        pd.testing.assert_series_equal(mw.labels, old_labels)
        assert mw._stage == 2

    def test_undo_with_none_old_df_is_noop(self):
        from gui.main_window import ProcessingStepCommand

        mw = FakeMainWindow()
        new_df = pd.DataFrame({"A": [1]})

        cmd = ProcessingStepCommand(
            mw,
            "import",
            new_df,
            None,
            new_labels=pd.Series(["G1"]),
            old_labels=None,
            new_stage=1,
            old_stage=0,
        )
        cmd.redo()
        assert mw._stage == 1

        cmd.undo()
        # old_df is None; undo is a no-op.
        assert mw._stage == 1
