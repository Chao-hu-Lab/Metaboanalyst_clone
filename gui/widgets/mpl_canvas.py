"""
Matplotlib 嵌入 PySide6 的 Widget
"""

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
from PySide6.QtWidgets import QVBoxLayout, QWidget


class MplCanvas(FigureCanvasQTAgg):
    """可嵌入 PySide6 的 Matplotlib 畫布"""

    def __init__(self, fig=None, parent=None, figsize=(8, 5), dpi=100):
        if fig is None:
            fig = Figure(figsize=figsize, dpi=dpi)
        self.axes = fig.add_subplot(111) if len(fig.axes) == 0 else fig.axes[0]
        super().__init__(fig)


class MplWidget(QWidget):
    """含導航列的 Matplotlib Widget"""

    def __init__(self, parent=None, figsize=(8, 5)):
        super().__init__(parent)
        self.canvas = MplCanvas(figsize=figsize)
        self.toolbar = NavigationToolbar2QT(self.canvas, self)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        self.setLayout(layout)

    @property
    def figure(self):
        return self.canvas.figure

    @property
    def axes(self):
        return self.canvas.axes

    def clear(self):
        self.canvas.figure.clear()
        self.canvas.axes = self.canvas.figure.add_subplot(111)

    def draw(self):
        self.canvas.draw()
