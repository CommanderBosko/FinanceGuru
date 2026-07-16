from datetime import date

from PySide6.QtCharts import (
    QBarCategoryAxis,
    QBarSet,
    QChart,
    QChartView,
    QDateTimeAxis,
    QLineSeries,
    QPieSeries,
    QScatterSeries,
    QStackedBarSeries,
    QValueAxis,
)
from PySide6.QtCore import QDate, QDateTime, Qt, QTime
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from financeguru import reporting
from financeguru.repositories import categories as category_repo
from financeguru.repositories import snapshots as snapshot_repo
from financeguru.views._table import money

_WINDOW = 12

# One metric, one colour — per-segment lines must read as a single broken
# series, not as distinct series (Qt would otherwise cycle theme colours).
_TREND_COLOR = QColor("#2d7dd2")


class ChartsView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._months: list[dict] = []

        layout = QVBoxLayout(self)

        # Spending (stacked bars + pie) and Net Worth (trend line) share the
        # tab; a third chart stacked vertically would crowd all of them.
        self._subtabs = QTabWidget()
        layout.addWidget(self._subtabs)

        # --- Spending page ---------------------------------------------------
        spending_page = QWidget()
        spending_layout = QVBoxLayout(spending_page)

        controls = QHBoxLayout()
        controls.addStretch()

        controls.addWidget(QLabel("Pie month:"))
        self._month_picker = QComboBox()
        controls.addWidget(self._month_picker)

        spending_layout.addLayout(controls)

        self._time_chart = QChart()
        self._time_view = QChartView(self._time_chart)
        self._time_view.setRenderHint(QPainter.Antialiasing)
        spending_layout.addWidget(self._time_view)

        self._pie_chart = QChart()
        self._pie_view = QChartView(self._pie_chart)
        self._pie_view.setRenderHint(QPainter.Antialiasing)
        spending_layout.addWidget(self._pie_view)

        self._subtabs.addTab(spending_page, "Spending")

        # --- Net Worth page --------------------------------------------------
        networth_page = QWidget()
        networth_layout = QVBoxLayout(networth_page)

        self._trend_chart = QChart()
        self._trend_view = QChartView(self._trend_chart)
        self._trend_view.setRenderHint(QPainter.Antialiasing)
        networth_layout.addWidget(self._trend_view)

        self._subtabs.addTab(networth_page, "Net Worth")

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
        self._rebuild_trend_chart()

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

    # -- Net-worth trend chart --------------------------------------------------
    def _rebuild_trend_chart(self) -> None:
        chart = self._trend_chart
        chart.removeAllSeries()
        for axis in list(chart.axes()):
            # Same leak avoidance as the time chart: removeAxis returns
            # ownership, so delete the old axis explicitly.
            chart.removeAxis(axis)
            axis.deleteLater()
        chart.legend().setVisible(False)

        snaps = snapshot_repo.get_all()
        if not snaps:
            chart.setTitle(
                "Tracked net worth (no snapshots yet — one accrues each day the app runs)"
            )
            return
        chart.setTitle("Tracked net worth — stocks − debts + goal savings")

        # The series only has points for days the app launched. Draw each
        # contiguous run as its own line and mark every snapshot with a dot, so
        # gaps show as breaks instead of a line pretending the value was known.
        def to_msecs(snap) -> float:
            d = date.fromisoformat(snap.snap_date)
            return float(
                QDateTime(QDate(d.year, d.month, d.day), QTime(12, 0)).toMSecsSinceEpoch()
            )

        dots = QScatterSeries()
        dots.setColor(_TREND_COLOR)
        dots.setBorderColor(_TREND_COLOR)
        dots.setMarkerSize(7.0)
        all_series = [dots]
        for segment in snapshot_repo.trend_segments(snaps):
            line = QLineSeries()
            line.setColor(_TREND_COLOR)
            for snap in segment:
                point = (to_msecs(snap), float(snap.net_worth))
                line.append(*point)
                dots.append(*point)
            if len(segment) > 1:
                all_series.append(line)
        for series in all_series:
            chart.addSeries(series)

        axis_x = QDateTimeAxis()
        axis_x.setFormat("MMM d yyyy")
        first = QDateTime.fromMSecsSinceEpoch(int(to_msecs(snaps[0])))
        last = QDateTime.fromMSecsSinceEpoch(int(to_msecs(snaps[-1])))
        # A day of padding keeps edge points (and a single-snapshot series,
        # which would otherwise produce a degenerate zero-width axis) visible.
        axis_x.setRange(first.addDays(-1), last.addDays(1))
        chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)

        axis_y = QValueAxis()
        axis_y.setLabelFormat("$%.0f")
        values = [float(s.net_worth) for s in snaps]
        low, high = min(values), max(values)
        # Net worth can be negative (debts outweigh stocks), so pad around the
        # actual range rather than anchoring at zero.
        pad = max((high - low) * 0.05, 1.0)
        axis_y.setRange(low - pad, high + pad)
        chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)

        for series in all_series:
            series.attachAxis(axis_x)
            series.attachAxis(axis_y)

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
            slice_ = series.append(f"{cat}: {money(amt)}", amt)
            slice_.setLabelVisible(True)

        chart.addSeries(series)
        if series.count() == 0:
            chart.setTitle(f"Category breakdown — {label} (no spending)")
        else:
            chart.setTitle(f"Category breakdown — {label}")
        chart.legend().setVisible(True)
        chart.legend().setAlignment(Qt.AlignmentFlag.AlignRight)
