from PySide6.QtCharts import (
    QBarCategoryAxis,
    QBarSet,
    QChart,
    QChartView,
    QPieSeries,
    QStackedBarSeries,
    QValueAxis,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from financeguru import reporting
from financeguru.repositories import categories as category_repo

_WINDOW = 12


class ChartsView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._months: list[dict] = []

        layout = QVBoxLayout(self)

        # --- Control bar -----------------------------------------------------
        controls = QHBoxLayout()
        controls.addStretch()

        controls.addWidget(QLabel("Pie month:"))
        self._month_picker = QComboBox()
        controls.addWidget(self._month_picker)

        layout.addLayout(controls)

        # --- Over-time chart -------------------------------------------------
        self._time_chart = QChart()
        self._time_view = QChartView(self._time_chart)
        self._time_view.setRenderHint(QPainter.Antialiasing)
        layout.addWidget(self._time_view)

        # --- Pie chart -------------------------------------------------------
        self._pie_chart = QChart()
        self._pie_view = QChartView(self._pie_chart)
        self._pie_view.setRenderHint(QPainter.Antialiasing)
        layout.addWidget(self._pie_view)

        # Signals — connect after building widgets so initial refresh is clean.
        self._month_picker.currentIndexChanged.connect(self._rebuild_pie_chart)

        self.refresh()

    # -- Public API -----------------------------------------------------------
    def refresh(self) -> None:
        """Re-query reporting and rebuild both charts and the month picker."""
        self._months = reporting.monthly_spending(_WINDOW)

        # Repopulate the month picker, preserving the current selection if the
        # same label is still present; otherwise default to the last (current) month.
        previous = self._month_picker.currentText()
        labels = [entry["label"] for entry in self._months]

        self._month_picker.blockSignals(True)
        self._month_picker.clear()
        self._month_picker.addItems(labels)
        if labels:
            if previous in labels:
                self._month_picker.setCurrentIndex(labels.index(previous))
            else:
                self._month_picker.setCurrentIndex(len(labels) - 1)
        self._month_picker.blockSignals(False)

        self._rebuild_time_chart()
        self._rebuild_pie_chart()

    # -- Over-time chart ------------------------------------------------------
    def _rebuild_time_chart(self) -> None:
        chart = self._time_chart
        chart.removeAllSeries()
        for axis in list(chart.axes()):
            # removeAxis hands ownership back to us; delete it so repeated
            # refreshes don't leak the old axis objects (removeAllSeries already
            # deletes the series side).
            chart.removeAxis(axis)
            axis.deleteLater()

        labels = [entry["label"] for entry in self._months]

        if not self._months:
            chart.setTitle("Spending over time (no data)")
            return

        chart.setTitle("Monthly spending — By category")
        series = QStackedBarSeries()
        for cat in category_repo.names():
            values = [entry["by_category"].get(cat, 0.0) for entry in self._months]
            if not any(values):
                continue  # skip categories with no activity to avoid legend noise
            bar_set = QBarSet(cat)
            for v in values:
                bar_set.append(v)
            series.append(bar_set)

        chart.addSeries(series)

        axis_x = QBarCategoryAxis()
        axis_x.append(labels)
        chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        series.attachAxis(axis_x)

        axis_y = QValueAxis()
        axis_y.setLabelFormat("%.0f")
        max_y = self._time_max()
        axis_y.setRange(0, max_y if max_y > 0 else 1)
        chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(axis_y)

        chart.legend().setVisible(True)
        chart.legend().setAlignment(Qt.AlignmentFlag.AlignBottom)

    def _time_max(self) -> float:
        # Stacked: the tallest bar is the largest per-month category sum.
        return max(
            (sum(entry["by_category"].values()) for entry in self._months),
            default=0.0,
        )

    # -- Pie chart ------------------------------------------------------------
    def _rebuild_pie_chart(self) -> None:
        chart = self._pie_chart
        chart.removeAllSeries()

        label = self._month_picker.currentText()
        if not label:
            chart.setTitle("Category breakdown (no data)")
            return

        try:
            year_s, month_s = label.split("-")
            year, month = int(year_s), int(month_s)
        except ValueError:
            chart.setTitle("Category breakdown (no data)")
            return

        breakdown = reporting.category_breakdown(year, month)

        series = QPieSeries()
        # Iterate the category list for a stable slice order; fall back to any
        # extras (e.g. a category since deleted but still on old records).
        category_names = category_repo.names()
        ordered = [c for c in category_names if c in breakdown]
        ordered += [c for c in breakdown if c not in category_names]
        for cat in ordered:
            amt = breakdown[cat]
            if amt <= 0:
                continue
            slice_ = series.append(f"{cat}: ${amt:,.2f}", amt)
            slice_.setLabelVisible(True)

        chart.addSeries(series)
        if series.count() == 0:
            chart.setTitle(f"Category breakdown — {label} (no spending)")
        else:
            chart.setTitle(f"Category breakdown — {label}")
        chart.legend().setVisible(True)
        chart.legend().setAlignment(Qt.AlignmentFlag.AlignRight)
