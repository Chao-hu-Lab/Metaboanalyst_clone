"""
PipelineWorker — QRunnable 背景運算，避免阻塞 GUI
"""

from PySide6.QtCore import QRunnable, Signal, QObject, QThreadPool
import traceback


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
    """

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()
        self.setAutoDelete(True)

    def run(self):
        try:
            result = self.fn(*self.args, **self.kwargs)
            self.signals.result.emit(result)
        except Exception:
            self.signals.error.emit(traceback.format_exc())
        finally:
            self.signals.finished.emit()
