"""Reusable Matplotlib widgets for PySide6 views."""

from __future__ import annotations

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
from PySide6.QtWidgets import QVBoxLayout, QWidget


class MplCanvas(FigureCanvasQTAgg):
    """A Qt canvas that wraps a Matplotlib figure."""

    def __init__(self, fig=None, parent=None, figsize=(8, 5), dpi=100):
        if fig is None:
            fig = Figure(figsize=figsize, dpi=dpi)
        self.axes = fig.add_subplot(111) if len(fig.axes) == 0 else fig.axes[0]
        super().__init__(fig)
        if parent is not None:
            self.setParent(parent)


class MplWidget(QWidget):
    """Composite Matplotlib widget with optional toolbars."""

    def __init__(
        self,
        parent=None,
        figsize=(8, 5),
        theme_manager=None,
        use_default_toolbar: bool = True,
        use_plot_toolbar: bool = False,
    ):
        super().__init__(parent)
        self.canvas = MplCanvas(parent=self, figsize=figsize)
        self.navigation_toolbar = NavigationToolbar2QT(self.canvas, self)
        self.toolbar = self.navigation_toolbar
        self.plot_toolbar = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        if use_default_toolbar:
            layout.addWidget(self.navigation_toolbar)
        layout.addWidget(self.canvas, stretch=1)

        if use_plot_toolbar:
            from gui.widgets.plot_toolbar import PlotToolbar

            self.plot_toolbar = PlotToolbar(self, theme_manager)
            layout.addWidget(self.plot_toolbar)

    @property
    def figure(self):
        return self.canvas.figure

    @property
    def axes(self):
        return self.canvas.axes

    def set_figure(self, fig: Figure) -> None:
        """Replace the figure displayed by the canvas."""
        self.canvas.figure = fig
        self.canvas.axes = fig.axes[0] if fig.axes else fig.add_subplot(111)

    def clear(self):
        """Clear the current figure and recreate the default axes."""
        self.canvas.figure.clear()
        self.canvas.axes = self.canvas.figure.add_subplot(111)

    def draw(self):
        """Redraw the canvas."""
        self.canvas.draw()


MatplotlibCanvas = MplWidget
