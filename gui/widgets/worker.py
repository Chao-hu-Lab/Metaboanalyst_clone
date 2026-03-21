"""
PipelineWorker — QRunnable 背景運算，避免阻塞 GUI
"""

from PySide6.QtCore import QRunnable, Signal, QObject
import traceback


class CancelledError(Exception):
    """Raised when a worker is cancelled."""


class WorkerSignals(QObject):
    """Worker 信號集"""
    progress = Signal(int, str)    # (percentage, message)
    result = Signal(object)        # 計算結果
    error = Signal(str)            # 錯誤訊息
    finished = Signal()


class PipelineWorker(QRunnable):
    """
    在 QThreadPool 中執行任意函式。

    用法：
        worker = PipelineWorker(some_function, arg1, arg2, kwarg1=val)
        worker.signals.result.connect(on_result)
        worker.signals.error.connect(on_error)
        QThreadPool.globalInstance().start(worker)

    取消：
        worker.cancel()  # 設定取消旗標
        # 長時間作業可透過 worker.is_cancelled() 主動檢查
    """

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()
        self._cancelled = False
        self.setAutoDelete(True)

    def cancel(self):
        """Request cancellation. The running function must check is_cancelled()."""
        self._cancelled = True

    def is_cancelled(self) -> bool:
        """Return True if cancellation has been requested."""
        return self._cancelled

    def run(self):
        try:
            result = self.fn(*self.args, **self.kwargs)
            if self._cancelled:
                self.signals.error.emit("Cancelled")
            else:
                self.signals.result.emit(result)
        except CancelledError:
            self.signals.error.emit("Cancelled")
        except Exception:
            if not self._cancelled:
                self.signals.error.emit(traceback.format_exc())
        finally:
            self.signals.finished.emit()
