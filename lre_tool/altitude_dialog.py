"""Thrust-versus-altitude chart for the existing-nozzle analysis."""

from PyQt5.QtGui import QPalette
from PyQt5.QtWidgets import QDialog, QLabel, QPushButton, QVBoxLayout

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from .inverse import calculate_altitude_thrust_curve


class AltitudeThrustDialog(QDialog):
    def __init__(self, owner, result):
        super().__init__(owner)
        self.owner = owner
        parent_window = getattr(owner, "window", None)
        self.window = owner if parent_window is None or callable(parent_window) else parent_window
        self.result = result
        self.curve = calculate_altitude_thrust_curve(result)
        self.setModal(False)
        self.resize(820, 560)
        self.setMinimumSize(620, 420)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(8)

        self.summary = QLabel()
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)

        self.figure = Figure(figsize=(8, 5), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas, 1)

        self.btn_close = QPushButton()
        self.btn_close.setMinimumWidth(100)
        self.btn_close.clicked.connect(self.close)
        layout.addWidget(self.btn_close, 0)

        self.retranslate_ui()

    def update_result(self, result):
        self.result = result
        self.curve = calculate_altitude_thrust_curve(result)
        self.retranslate_ui()

    def set_theme(self, _mode):
        self.draw_chart()

    def retranslate_ui(self):
        tr = self.window._tr
        self.setWindowTitle(tr(
            "Thrust versus Altitude",
            "График тяги по высоте",
        ))
        matched = self.curve.matched_altitude_km
        matched_text = tr(
            "Matched-expansion altitude is outside the 0–100 km range.",
            "Высота расчетного режима находится вне диапазона 0–100 км.",
        )
        if matched is not None:
            matched_text = tr(
                f"Matched-expansion altitude: {matched:.2f} km.",
                f"Высота расчетного режима: {matched:.2f} км.",
            )
        self.summary.setText(tr(
            f"Total thrust for {self.result.chamber_count} chamber(s). {matched_text}",
            f"Суммарная тяга для камер: {self.result.chamber_count}. {matched_text}",
        ))
        self.btn_close.setText(tr("Close", "Закрыть"))
        self.draw_chart()

    def draw_chart(self):
        tr = self.window._tr
        dark = self.palette().color(QPalette.Base).lightness() < 128
        background = "#1b1f26" if dark else "#ffffff"
        foreground = "#f4f4f4" if dark else "#111827"
        grid = "#596273" if dark else "#d1d5db"
        curve_color = "#bb86fc" if dark else "#6200ee"
        sea_level_color = "#64b5f6" if dark else "#2563eb"
        design_thrust_color = "#ef9a9a" if dark else "#dc2626"
        vacuum_color = "#63d6a3" if dark else "#14815d"
        design_color = "#ffb74d" if dark else "#d97706"

        self.figure.clear()
        self.figure.set_facecolor(background)
        axis = self.figure.add_subplot(111)
        axis.set_facecolor(background)
        for spine in axis.spines.values():
            spine.set_color(foreground)
        axis.tick_params(colors=foreground)
        axis.xaxis.label.set_color(foreground)
        axis.yaxis.label.set_color(foreground)
        axis.title.set_color(foreground)

        thrust_kn = [value / 1000.0 for value in self.curve.thrust]
        vacuum_kn = self.result.P_vac / 1000.0
        sea_level_kn = self.result.P_SL / 1000.0
        design_thrust_kn = (
            self.result.total_mass_flow * self.result.J_r_ud / 1000.0
        )
        force_unit = tr("kN", "кН")
        axis.plot(
            self.curve.altitude_km,
            thrust_kn,
            color=curve_color,
            linewidth=2.2,
            label=tr("Thrust versus altitude", "Тяга по высоте"),
        )
        axis.axhline(
            sea_level_kn,
            color=sea_level_color,
            linestyle=":",
            linewidth=1.6,
            label=tr(
                f"Sea-level thrust: {sea_level_kn:.3f} {force_unit}",
                f"Тяга на уровне Земли: {sea_level_kn:.3f} {force_unit}",
            ),
        )
        axis.axhline(
            vacuum_kn,
            color=vacuum_color,
            linestyle="--",
            linewidth=1.4,
            label=tr(
                f"Vacuum thrust: {vacuum_kn:.3f} {force_unit}",
                f"Тяга в вакууме: {vacuum_kn:.3f} {force_unit}",
            ),
        )
        axis.axhline(
            design_thrust_kn,
            color=design_thrust_color,
            linestyle=(0, (5, 2)),
            linewidth=1.5,
            label=tr(
                f"Design thrust: {design_thrust_kn:.3f} {force_unit}",
                f"Расчетная тяга: {design_thrust_kn:.3f} {force_unit}",
            ),
        )
        axis.scatter([0.0], [sea_level_kn], color=curve_color, s=36, zorder=3)
        if self.curve.matched_altitude_km is not None:
            matched = self.curve.matched_altitude_km
            axis.axvline(
                matched,
                color=design_color,
                linestyle="-.",
                linewidth=1.8,
                label=tr(
                    f"Design altitude: {matched:.1f} km",
                    f"Расчетная высота: {matched:.1f} км",
                ),
            )

        axis.set_xlim(0.0, 100.0)
        thrust_span = max(vacuum_kn - sea_level_kn, abs(vacuum_kn) * 0.01, 1e-6)
        axis.set_ylim(
            min(min(thrust_kn), design_thrust_kn) - 0.05 * thrust_span,
            max(vacuum_kn, max(thrust_kn), design_thrust_kn) + 0.08 * thrust_span,
        )
        axis.set_xlabel(tr("Altitude [km]", "Высота [км]"))
        axis.set_ylabel(tr("Thrust [kN]", "Тяга [кН]"))
        axis.set_title(tr(
            "Engine thrust versus altitude",
            "Изменение тяги двигателя по высоте",
        ))
        axis.grid(True, color=grid, alpha=0.55, linewidth=0.7)
        legend = axis.legend(loc="lower right")
        legend.get_frame().set_facecolor(background)
        legend.get_frame().set_edgecolor(grid)
        for text_item in legend.get_texts():
            text_item.set_color(foreground)
        self.figure.subplots_adjust(left=0.12, right=0.97, bottom=0.13, top=0.91)
        self.canvas.draw_idle()
