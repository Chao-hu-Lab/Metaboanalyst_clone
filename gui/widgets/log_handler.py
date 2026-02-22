"""
QLogHandler — 將 Python logging 導向 QPlainTextEdit
"""

import logging
from PySide6.QtCore import Signal, QObject


class QLogHandler(logging.Handler, QObject):
    """將 Python logging 導向 Qt widget (透過 signal)"""
    log_signal = Signal(str)

    def __init__(self):
        logging.Handler.__init__(self)
        QObject.__init__(self)
        self.setFormatter(logging.Formatter(
            '[%(asctime)s] %(message)s', '%H:%M:%S'
        ))

    def emit(self, record):
        msg = self.format(record)
        self.log_signal.emit(msg)
