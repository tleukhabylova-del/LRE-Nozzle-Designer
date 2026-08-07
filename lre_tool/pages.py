"""Reusable pages that present graphs and thermal-analysis results."""

import html

import numpy as np

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QDoubleValidator, QPalette
from PyQt5.QtWidgets import (
    QComboBox, QFrame, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QPushButton, QScrollArea, QSizePolicy, QTextEdit, QVBoxLayout, QWidget,
)

from .plotting import PlotWidget


class GraphPage(QWidget):
    def __init__(self, title: str, button_text: str, show_info=False, geometry_state=None):
        super().__init__()

        self.setObjectName("graphPage")

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(12, 12, 12, 12)
        self.layout.setSpacing(8)

        self.plot = PlotWidget(title, geometry_state)
        self.layout.addWidget(self.plot)

        self.info_box = None
        self.points_box = None
        self.hover_label = None
        self.search_value = None
        self.search_param = None
        self.btn_search_point = None
        self.language = "en"

        # =====================================================
        # Geometry-page layout: plot and action button only.
        # =====================================================
        if not show_info:
            bar = QHBoxLayout()
            bar.setContentsMargins(0, 0, 0, 0)
            bar.setSpacing(8)
            self.layout.addLayout(bar)

            self.btn_calc = QPushButton(button_text)
            self.btn_calc.setMinimumHeight(30)
            self.btn_calc.setCursor(Qt.PointingHandCursor)

            bar.addWidget(self.btn_calc)
            bar.addStretch(1)

            return

        # =====================================================
        # Layout used by the Mach, temperature, and pressure pages.
        # =====================================================
        bar = QHBoxLayout()
        bar.setContentsMargins(0, 0, 0, 0)
        bar.setSpacing(8)
        self.layout.addLayout(bar)

        self.btn_calc = QPushButton(button_text)
        self.btn_calc.setMinimumHeight(30)
        self.btn_calc.setCursor(Qt.PointingHandCursor)
        bar.addWidget(self.btn_calc)

        self.hover_label = QLabel("x = -    |    R = -    |    value = -")
        self.hover_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.hover_label.setMinimumHeight(28)
        bar.addWidget(self.hover_label, 1)

        self.search_value = QLineEdit()
        self.search_value.setFixedWidth(110)
        self.search_value.setMinimumHeight(28)
        self.search_value.setPlaceholderText("value")
        bar.addWidget(self.search_value)

        self.search_param = QComboBox()
        self.search_param.setFixedWidth(60)
        self.search_param.setMinimumHeight(28)
        self.search_param.addItems(["x", "M"])
        bar.addWidget(self.search_param)

        self.btn_search_point = QPushButton("⌕")
        self.btn_search_point.setFixedSize(32, 28)
        self.btn_search_point.setToolTip("Find the nearest point")
        bar.addWidget(self.btn_search_point)

        bottom = QHBoxLayout()
        bottom.setContentsMargins(0, 0, 0, 0)
        bottom.setSpacing(10)
        self.layout.addLayout(bottom)

        self.info_box = QTextEdit()
        self.info_box.setReadOnly(True)
        self.info_box.setMinimumHeight(90)
        self.info_box.setMaximumHeight(120)
        bottom.addWidget(self.info_box, 3)

        self.points_box = QTextEdit()
        self.points_box.setReadOnly(False)
        self.points_box.setMinimumHeight(90)
        self.points_box.setMaximumHeight(120)
        bottom.addWidget(self.points_box, 2)

        self.plot.hover_text_changed = self.hover_label.setText
        self.plot.point_clicked = self.add_point_text
        self.btn_search_point.clicked.connect(self.find_point_by_value)

    def set_info(self, text):
        if self.info_box is not None:
            self.info_box.setPlainText(text)

    def add_point_text(self, text):
        if self.points_box is not None:
            self.points_box.append(text)

    def find_point_by_value(self):
        if self.points_box is None:
            return

        if self.plot._hover_x is None or self.plot._hover_val is None:
            self.points_box.append \
                ("Нет данных для поиска." if self.language == "ru" else "No data available for search.")
            return

        try:
            target = float(self.search_value.text().replace(",", "."))
        except ValueError:
            self.points_box.append("Введите числовое значение для поиска." if self.language == "ru"
                                   else "Enter a numeric value to search for.")
            return

        x_arr = np.asarray(self.plot._hover_x, dtype=float)
        y_arr = np.asarray(self.plot._hover_y, dtype=float)
        val_arr = np.asarray(self.plot._hover_val, dtype=float)

        param = self.search_param.currentText()

        if param == "x":
            idx = int(np.argmin(np.abs(x_arr - target)))
        else:
            idx = int(np.argmin(np.abs(val_arr - target)))

        label = self.plot._hover_label if self.plot._hover_label else "value"
        unit = self.plot._hover_unit if hasattr(self.plot, "_hover_unit") else ""
        unit_s = f" {unit}" if unit else ""

        text = (
            f"x={x_arr[idx]:.3f} mm   |   "
            f"R={y_arr[idx]:.3f} mm   |   "
            f"{label}={val_arr[idx]:.6g}{unit_s}"
        )
        self.points_box.append(text)

    def draw_fill(self, *args, **kwargs):
        self.plot.draw_fill(*args, **kwargs)

        if self.search_param is not None:
            label = self.plot._hover_label if self.plot._hover_label else "value"
            self.search_param.clear()
            self.search_param.addItems(["x", label])

    def draw_geometry(self, *args, **kwargs):
        self.plot.draw_geometry(*args, **kwargs)


class ThermalPage(QWidget):
    # Presents thermal-analysis inputs, results, and tabular wall data.
    def __init__(self, geometry_state=None):
        super().__init__()
        self.setObjectName("graphPage")

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        outer_layout.addWidget(self.scroll_area)

        self.scroll_content = QWidget()
        self.scroll_content.setObjectName("graphPage")
        self.scroll_area.setWidget(self.scroll_content)

        layout = QVBoxLayout(self.scroll_content)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(16)

        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        top.setSpacing(8)
        layout.addLayout(top)

        controls_widget = QWidget()
        controls_widget.setMinimumWidth(300)
        controls_widget.setMaximumWidth(300)
        controls = QVBoxLayout(controls_widget)
        controls.setContentsMargins(0, 0, 8, 0)
        controls.setSpacing(8)

        self.lbl_T_wall_material_max = QLabel("Maximum allowable combustion-wall material temperature")
        self.lbl_T_wall_material_max.setWordWrap(True)
        controls.addWidget(self.lbl_T_wall_material_max)

        input_row = QHBoxLayout()
        input_row.setContentsMargins(0, 0, 0, 0)
        input_row.setSpacing(8)
        controls.addLayout(input_row)

        self.ed_T_wall_material_max = QLineEdit()
        self.ed_T_wall_material_max.setFixedWidth(130)
        self.ed_T_wall_material_max.setValidator(QDoubleValidator(0.0, 10000.0, 6, self))
        input_row.addWidget(self.ed_T_wall_material_max)

        self.lbl_T_unit = QLabel("K")
        input_row.addWidget(self.lbl_T_unit)

        self.btn_temperature_help = QPushButton("?")
        self.btn_temperature_help.setObjectName("helpButton")
        self.btn_temperature_help.setCursor(Qt.PointingHandCursor)
        self.btn_temperature_help.setFixedSize(18, 18)
        self.btn_temperature_help.clicked.connect(self._show_temperature_help)
        input_row.addWidget(self.btn_temperature_help)
        input_row.addStretch(1)

        self.btn_calc = QPushButton("Calculate")
        self.btn_calc.setFixedWidth(130)
        self.btn_calc.setMinimumHeight(30)
        self.btn_calc.setCursor(Qt.PointingHandCursor)
        controls.addWidget(self.btn_calc)
        controls.addStretch(1)
        top.addWidget(controls_widget)

        self.max_temperature_caption = "Maximum allowable combustion-wall material temperature"
        self.gas_wall_temperature_caption = "Gas-wall temperature"
        self.s_caption = "Thermodynamic coefficient"
        self.q_caption = "Total thermal load"
        self.temperature_unit = "K"
        self.heat_load_unit = "W"
        self.temperature_help_title = "Temperature input"
        self.temperature_help_text = (
            "Enter the maximum allowable temperature of the combustion-wall material in kelvins. "
            "This value is used for the thermal-load calculation."
        )
        self.temperature_range_provider = None
        self._last_max_temperature = None
        self._last_gas_wall_temperature = None
        self._last_s_value = None
        self._last_q_value = None
        self._last_table_frame = None
        self._table_point_caption = "Point"
        self._table_parameter_caption = "Parameter"
        self._table_maximum_caption = "maximum total heat flux"
        self._table_section_names = {
            "convergent": "Convergent section",
            "throat": "Throat",
            "divergent": "Divergent section",
        }
        self._table_parameter_labels = {
            "R/R_t [-]": "Relative radius R/R_t [-]",
            "x [mm]": "Axial coordinate [mm]",
            "q_k [W/m^2]": "Specific convective\nheat flux q_k [W/m²]",
            "q_l [W/m^2]": "Specific radiative\nheat flux q_l [W/m²]",
            "q_sum [W/m^2]": "Total specific\nheat flux q_sum [W/m²]",
            "dA_wall [m^2]": "Wall-segment area [m²]",
            "dQ [W]": "Heat load on segment [W]",
            "Q_cum [W]": "Cumulative heat load [W]",
        }

        self.results_box = QTextEdit()
        self.results_box.setReadOnly(True)
        self.results_box.setAcceptRichText(False)
        self.results_box.setMinimumHeight(120)
        self.results_box.setMaximumHeight(120)
        self.results_box.setLineWrapMode(QTextEdit.WidgetWidth)
        top.addWidget(self.results_box, 1)
        self._refresh_result_labels()

        self.table = QTextEdit()
        self.table.setReadOnly(True)
        self.table.setMinimumHeight(280)
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.table.setLineWrapMode(QTextEdit.NoWrap)
        layout.addWidget(self.table)

        self.plot = PlotWidget("Specific heat flux along the combustion wall", geometry_state)
        self.plot.setMinimumHeight(340)
        self.plot.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.plot)

        self.contour_plot = PlotWidget("Nozzle contour", geometry_state)
        self.contour_plot.setMinimumHeight(220)
        self.contour_plot.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.contour_plot)

    def set_language(self, tr):
        self.lbl_T_wall_material_max.setText(tr(
            "Maximum allowable combustion-wall material temperature",
            "Предельно допустимая температура материала огневой стенки"
        ))
        self.lbl_T_unit.setText(tr("K", "К"))
        self.btn_temperature_help.setToolTip(tr("Input parameter help", "Справка о вводимом параметре"))
        self.btn_calc.setText(tr("Calculate", "Рассчитать"))
        self.contour_plot.title = tr(
            "Nozzle contour",
            "\u041a\u043e\u043d\u0442\u0443\u0440 \u0441\u043e\u043f\u043b\u0430"
        )
        self.plot.title = tr(
            "Specific heat flux along the combustion wall",
            "Удельный тепловой поток вдоль огневой стенки"
        )
        self.max_temperature_caption = tr(
            "Maximum allowable combustion-wall material temperature",
            "Предельно допустимая температура материала огневой стенки"
        )
        self.gas_wall_temperature_caption = tr("Gas-wall temperature", "Температура газовой стенки")
        self.s_caption = tr("Thermodynamic coefficient", "Термодинамический коэффициент")
        self.q_caption = tr("Total thermal load", "Суммарная тепловая нагрузка")
        self.temperature_unit = tr("K", "К")
        self.heat_load_unit = tr("W", "Вт")
        self.temperature_help_title = tr("Temperature input", "Ввод температуры")
        self.temperature_help_text = tr(
            "Enter the maximum allowable temperature of the combustion-wall material in kelvins. "
            "The gas-wall temperature used to select the thermodynamic coefficient is 50 K lower "
            "than the entered material temperature.",
            "Введите предельно допустимую температуру материала огневой стенки в кельвинах. "
            "Температура газа у стенки, по которой выбирается термодинамический коэффициент, "
            "принимается на 50 К ниже введённой температуры материала."
        )
        self._table_point_caption = tr("Point", "Точка")
        self._table_parameter_caption = tr("Parameter", "Параметр")
        self._table_maximum_caption = tr(
            "maximum total heat flux",
            "максимальная суммарная плотность теплового потока"
        )
        self._table_section_names = {
            "convergent": tr("Convergent section", "Сужающаяся часть"),
            "throat": tr("Throat", "Критическое сечение"),
            "divergent": tr("Divergent section", "Расширяющаяся часть"),
        }
        self._table_parameter_labels = {
            "R/R_t [-]": tr("Relative radius R/R_t [-]", "Относительный радиус R/Rкр [-]"),
            "x [mm]": tr("Axial coordinate [mm]", "Координата вдоль сопла [мм]"),
            "q_k [W/m^2]": tr("Specific convective\nheat flux q_k [W/m²]", "Удельный конвективный\nтепловой поток q_k [Вт/м²]"),
            "q_l [W/m^2]": tr("Specific radiative\nheat flux q_l [W/m²]", "Удельный лучистый\nтепловой поток q_l [Вт/м²]"),
            "q_sum [W/m^2]": tr("Total specific\nheat flux q_sum [W/m²]", "Суммарный удельный\nтепловой поток q_sum [Вт/м²]"),
            "dA_wall [m^2]": tr("Wall-segment area [m²]", "Площадь участка огневой стенки [м²]"),
            "dQ [W]": tr("Heat load on segment [W]", "Тепловая нагрузка участка [Вт]"),
            "Q_cum [W]": tr("Cumulative heat load [W]", "Накопленная тепловая нагрузка [Вт]"),
        }
        self._refresh_result_labels()
        self._render_transposed_table()

    def _show_temperature_help(self):
        text = self.temperature_help_text
        if callable(self.temperature_range_provider):
            range_data = self.temperature_range_provider()
            if range_data is not None:
                pair_name, minimum, maximum = range_data
                single_temperature = abs(maximum - minimum) < 1e-9
                if self.temperature_unit == "К" and single_temperature:
                    text += (
                        f"\n\nВыбранная топливная пара: {pair_name}."
                        f"\nДля этой пары доступна только одна расчётная температура материала "
                        f"стенки: {minimum:g} К. Если ввести другое значение, программа "
                        f"автоматически установит {minimum:g} К и покажет пояснение."
                    )
                elif self.temperature_unit == "К":
                    text += (
                        f"\n\nВыбранная топливная пара: {pair_name}."
                        f"\nДоступный расчётный диапазон вводимой температуры: "
                        f"{minimum:g}–{maximum:g} К."
                    )
                elif single_temperature:
                    text += (
                        f"\n\nSelected propellant pair: {pair_name}."
                        f"\nOnly one wall-material calculation temperature is available for this pair: "
                        f"{minimum:g} K. If another value is entered, the application will "
                        f"automatically set {minimum:g} K and display an explanation."
                    )
                else:
                    text += (
                        f"\n\nSelected propellant pair: {pair_name}."
                        f"\nAvailable calculation range for the input temperature: "
                        f"{minimum:g}–{maximum:g} K."
                    )
            else:
                text += (
                    "\n\nДля выбранной топливной пары не найдены температурные данные."
                    if self.temperature_unit == "К" else
                    "\n\nNo temperature data were found for the selected propellant pair."
                )
        QMessageBox.information(self, self.temperature_help_title, text)

    def _refresh_result_labels(self):
        max_text = "-" if self._last_max_temperature is None else f"{self._last_max_temperature:.6g} {self.temperature_unit}"
        gas_text = "-" if self._last_gas_wall_temperature is None else f"{self._last_gas_wall_temperature:.6g} {self.temperature_unit}"
        s_text = "-" if self._last_s_value is None else f"{self._last_s_value:.6g}"
        q_text = "-" if self._last_q_value is None else f"{self._last_q_value:.6g} {self.heat_load_unit}"
        self.results_box.setPlainText("\n".join((
            f"{self.max_temperature_caption}: {max_text}",
            f"{self.gas_wall_temperature_caption}: {gas_text}",
            f"{self.s_caption}: {s_text}",
            f"{self.q_caption}: {q_text}",
        )))

    def set_results(self, T_gas_wall, S_gas_wall, Q_loss_W, frame):
        try:
            self._last_max_temperature = float(self.ed_T_wall_material_max.text().replace(",", "."))
        except ValueError:
            self._last_max_temperature = None
        self._last_gas_wall_temperature = float(T_gas_wall)
        self._last_s_value = float(S_gas_wall)
        self._last_q_value = float(Q_loss_W)
        self._refresh_result_labels()
        self._last_table_frame = frame
        self._render_transposed_table()

    def _render_transposed_table(self):
        frame = self._last_table_frame
        if frame is None:
            self.table.clear()
            return

        dark_mode = self.palette().color(QPalette.Base).lightness() < 128
        if dark_mode:
            table_bg = "#1E1E1E"
            header_bg = "#2A2238"
            label_bg = "#25212D"
            cell_bg = "#1A1A1D"
            max_bg = "#3D2C78"
            border = "#4B3D63"
            text = "#F4F4F4"
            label_text = "#FFFFFF"
            self.table.setStyleSheet(
                "QTextEdit { background:#1E1E1E; color:#F4F4F4; "
                "border:1px solid rgba(255,255,255,0.12); border-radius:9px; }"
            )
        else:
            table_bg = "#ffffff"
            header_bg = "#d9eef3"
            label_bg = "#eef6f8"
            cell_bg = "#ffffff"
            max_bg = "#fff0b3"
            border = "#777777"
            text = "#111827"
            label_text = "#111827"
            self.table.setStyleSheet("")

        columns = [name for name in self._table_parameter_labels if name in frame.columns]
        point_count = len(frame.index)
        maximum_index = None
        total_column = "q_sum [W/m^2]"
        if total_column in frame.columns and point_count:
            try:
                maximum_index = int(np.nanargmax(np.asarray(frame[total_column], dtype=float)))
            except Exception:
                maximum_index = None

        def cell_style(point_index):
            if point_index == maximum_index:
                return f"background:{max_bg}; color:{text};"
            return f"background:{cell_bg}; color:{text};"

        header_cells = [
            f"<th style='border:1px solid {border}; padding:5px 8px; background:{header_bg}; "
            f"color:{label_text}; text-align:left; white-space:nowrap;'>" +
            html.escape(self._table_parameter_caption) + "</th>"
        ]
        for point_index in range(point_count):
            caption = f"{self._table_point_caption} {point_index + 1}"
            if point_index == maximum_index:
                caption += " ★"
            header_cells.append(
                "<th title='" + html.escape(self._table_maximum_caption if point_index == maximum_index else "") +
                f"' style='border:1px solid {border}; padding:5px 8px; text-align:center; white-space:nowrap; " +
                cell_style(point_index) + "'>" + html.escape(caption) + "</th>"
            )

        body_rows = []
        for column_name in columns:
            values = frame[column_name].tolist()
            parameter_label = self._table_parameter_labels[column_name]
            parameter_html = html.escape(parameter_label).replace("\n", "<br>")
            cells = [
                f"<td style='border:1px solid {border}; padding:4px 8px; background:{label_bg}; "
                f"color:{label_text}; font-weight:600; white-space:normal; width:161px;'>" +
                parameter_html + "</td>"
            ]
            for point_index, value in enumerate(values):
                if isinstance(value, (int, float, np.number)):
                    value_text = f"{float(value):.9g}"
                else:
                    value_text = str(value)
                cells.append(
                    f"<td style='border:1px solid {border}; padding:4px 8px; text-align:right; "
                    "white-space:nowrap; " + cell_style(point_index) + "'>" +
                    html.escape(value_text) + "</td>"
                )
            body_rows.append("<tr>" + "".join(cells) + "</tr>")

        self.table.setHtml(
            f"<body style='background:{table_bg}; color:{text}; margin:0;'>"
            f"<div style='background:{table_bg}; color:{text}; padding:4px;'>"
            f"<table cellspacing='0' cellpadding='0' style='border-collapse:collapse; background:{table_bg}; color:{text};'>" +
            "<thead><tr>" + "".join(header_cells) + "</tr></thead><tbody>" +
            "".join(body_rows) + "</tbody></table></div></body>"
        )
        self.table.document().adjustSize()
        table_width = int(np.ceil(self.table.document().idealWidth())) + 30
        self.table.document().setTextWidth(table_width)
        self.table.document().adjustSize()
        table_height = int(np.ceil(self.table.document().size().height())) + 24
        self.table.setMinimumWidth(max(900, table_width))
        self.table.setMinimumHeight(max(280, table_height))
        self.table.setMaximumHeight(max(280, table_height))

    def clear_results(self):
        self._last_max_temperature = None
        self._last_gas_wall_temperature = None
        self._last_s_value = None
        self._last_q_value = None
        self._last_table_frame = None
        self._refresh_result_labels()
        self.table.clear()
        self.plot.clear()
        self.contour_plot.clear()

    def _rows_to_html(self, rows):
        headers = [
            "R_ratio_geometry [-]",
            "position [-]",
            "q0_recognized [W/m^2]",
            "q_conv [W/m^2]",
            "q_rad [W/m^2]",
            "q_sum [W/m^2]",
            "dQ [W]",
            "Q_cum [W]",
        ]
        html_rows = [
            "<tr>" + "".join(
                f"<th style='border:1px solid #555; padding:4px; background:#d9eef3;'>{html.escape(h)}</th>"
                for h in headers
            ) + "</tr>"
        ]
        for row in rows:
            values = [
                f"{row.get('required_R_ratio', row['R_ratio_geometry']):.1f}",
                row["position"],
                f"{row['q0_recognized_W_m2']:.6g}",
                f"{row['q_k_W_m2']:.6g}",
                f"{row['q_l_W_m2']:.6g}",
                f"{row['q_sum_W_m2']:.6g}",
                f"{row['Q_loss_segment_W']:.6g}",
                f"{row['Q_loss_cumulative_W']:.6g}",
            ]
            html_rows.append(
                "<tr>" + "".join(
                    f"<td style='border:1px solid #555; padding:4px;'>{html.escape(str(v))}</td>"
                    for v in values
                ) + "</tr>"
            )
        return (
                "<div style='font-family:Segoe UI, Arial; font-size:12px;'>"
                "<table style='border-collapse:collapse; width:100%;'>"
                + "".join(html_rows) +
                "</table></div>"
        )
