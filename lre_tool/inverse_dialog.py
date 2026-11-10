"""Draft dialog for evaluating an existing nozzle."""

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIntValidator
from PyQt5.QtWidgets import (
    QComboBox, QDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit,
    QListView, QMessageBox, QPushButton, QTextEdit, QVBoxLayout,
)

from .constants import COEF_J_DEFAULT, J_st_list, R_st_list, T_st_list, k_st_list
from .altitude_dialog import AltitudeThrustDialog
from .inverse import calculate_inverse_nozzle
from .validators import FlexibleDoubleValidator


class InverseNozzleDialog(QDialog):
    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.last_result = None
        self._altitude_dialog = None
        self.setModal(False)
        self.setMinimumWidth(620)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)

        self.intro = QLabel()
        self.intro.setWordWrap(True)
        root.addWidget(self.intro)

        form = QFormLayout()
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(9)
        root.addLayout(form)

        self.cb_fuel = QComboBox()
        self._prepare_combo(self.cb_fuel)
        for row in range(window.cbFuel.count()):
            fuel_idx = int(window.cbFuel.itemData(row))
            self.cb_fuel.addItem(window._fuel_name(fuel_idx), fuel_idx)
        self.cb_fuel.setCurrentIndex(max(0, window.cbFuel.currentIndex()))
        self.btn_fuel_params = QPushButton("•••")
        self.btn_fuel_params.setFixedSize(44, 28)
        self.btn_fuel_params.clicked.connect(self._open_fuel_parameters)
        fuel_row = QHBoxLayout()
        fuel_row.setContentsMargins(0, 0, 0, 0)
        fuel_row.setSpacing(8)
        fuel_row.addWidget(self.cb_fuel, 1)
        fuel_row.addWidget(self.btn_fuel_params)
        self.lbl_fuel = QLabel()
        form.addRow(self.lbl_fuel, fuel_row)

        self.ed_D_kr = self._number_edit("21")
        self.ed_D_a = self._number_edit("70")
        self.ed_p_k = self._number_edit("10")
        self.ed_coefJ = self._number_edit(f"{COEF_J_DEFAULT:g}")
        self.ed_chamber_count = self._integer_edit("1")
        self.lbl_D_kr = QLabel()
        self.lbl_D_a = QLabel()
        self.lbl_p_k = QLabel()
        self.lbl_coefJ = QLabel()
        self.lbl_chamber_count = QLabel()
        form.addRow(self.lbl_D_kr, self.ed_D_kr)
        form.addRow(self.lbl_D_a, self.ed_D_a)
        form.addRow(self.lbl_p_k, self.ed_p_k)
        form.addRow(self.lbl_coefJ, self.ed_coefJ)
        form.addRow(self.lbl_chamber_count, self.ed_chamber_count)

        self.results = QTextEdit()
        self.results.setReadOnly(True)
        self.results.setMinimumHeight(260)
        self.results.setFontFamily("Consolas")
        root.addWidget(self.results)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        self.btn_calculate = QPushButton()
        self.btn_altitude_plot = QPushButton()
        self.btn_close = QPushButton()
        self.btn_calculate.setMinimumWidth(120)
        self.btn_altitude_plot.setMinimumWidth(170)
        self.btn_altitude_plot.setEnabled(False)
        self.btn_close.setMinimumWidth(100)
        self.btn_calculate.clicked.connect(self.calculate)
        self.btn_altitude_plot.clicked.connect(self.open_altitude_plot)
        self.btn_close.clicked.connect(self.close)
        buttons.addWidget(self.btn_calculate)
        buttons.addWidget(self.btn_altitude_plot)
        buttons.addWidget(self.btn_close)
        root.addLayout(buttons)

        self._load_current_geometry()
        self.retranslate_ui()

    @staticmethod
    def _prepare_combo(combo):
        """Use the styled Qt popup instead of a native popup with unreadable selection."""
        view = QListView(combo)
        view.setStyleSheet(
            "QListView {"
            "color: palette(text);"
            "background-color: palette(base);"
            "selection-color: palette(highlighted-text);"
            "selection-background-color: palette(highlight);"
            "}"
        )
        combo.setView(view)

    def retranslate_ui(self):
        tr = self.window._tr
        self.setWindowTitle(tr(
            "Engine Performance from Nozzle Geometry",
            "Расчет характеристик двигателя по геометрии сопла",
        ))
        self.intro.setText(tr(
            "Select the propellant pair and enter the chamber pressure, nozzle geometry, specific "
            "impulse coefficient, and number of chambers. Flow rates, exit pressure, specific "
            "impulses, and thrusts will be calculated.",
            "Выберите топливную пару и введите давление в камере, геометрию сопла, коэффициент "
            "удельного импульса и количество камер. Будут рассчитаны расходы, давление на срезе, "
            "удельные импульсы и тяги.",
        ))
        self.lbl_fuel.setText(tr("Propellant pair", "Топливная пара"))
        self.btn_fuel_params.setToolTip(tr(
            "Propellant pair parameters",
            "Параметры топливной пары",
        ))
        self.lbl_D_kr.setText(tr(
            "Throat diameter D_t [mm]",
            "Диаметр критического сечения D_кр [мм]",
        ))
        self.lbl_D_a.setText(tr(
            "Exit diameter D_e [mm]",
            "Диаметр среза сопла D_a [мм]",
        ))
        self.lbl_p_k.setText(tr(
            "Chamber pressure p_c [MPa]",
            "Давление в камере p_k [МПа]",
        ))
        self.lbl_coefJ.setText(tr(
            "Specific impulse coefficient J_coef",
            "Коэффициент удельного импульса coefJ",
        ))
        self.lbl_chamber_count.setText(tr(
            "Number of combustion chambers N_c",
            "Количество камер сгорания z_k",
        ))
        self.refresh_fuel_names()

        self.btn_calculate.setText(tr("Calculate", "Рассчитать"))
        self.btn_altitude_plot.setText(tr(
            "Thrust vs Altitude",
            "График тяги по высоте",
        ))
        self.btn_close.setText(tr("Close", "Закрыть"))

        if self._altitude_dialog is not None:
            self._altitude_dialog.retranslate_ui()

        # Rebuild language-dependent result and warning text, if already calculated.
        if self.results.toPlainText():
            self.calculate()

    @staticmethod
    def _number_edit(default):
        edit = QLineEdit(default)
        edit.setValidator(FlexibleDoubleValidator())
        edit.setAlignment(Qt.AlignRight)
        return edit

    @staticmethod
    def _integer_edit(default):
        edit = QLineEdit(default)
        edit.setValidator(QIntValidator(1, 999, edit))
        edit.setAlignment(Qt.AlignRight)
        return edit

    @staticmethod
    def _value(edit):
        return float(edit.text().strip().replace(",", "."))

    def _error_text(self, error):
        english = str(error)
        russian_errors = {
            "nozzle expansion ratio must be greater than one": "степень расширения сопла должна быть больше единицы",
            "specific heat ratio must be greater than one": "показатель адиабаты должен быть больше единицы",
            "all input values must be finite": "все исходные значения должны быть конечными числами",
            "exit diameter must be greater than throat diameter": "диаметр среза должен быть больше диаметра критического сечения",
            "chamber pressure must be greater than sea-level pressure": "давление в камере должно быть выше давления на уровне Земли",
            "thermodynamic inputs must be positive": "термодинамические параметры должны быть положительными",
            "specific impulse coefficient must be between zero and one": "коэффициент удельного импульса должен быть больше нуля и не больше единицы",
            "calculated chamber temperature must be positive": "расчетная температура в камере должна быть положительной",
            "number of chambers must be a positive integer": "количество камер должно быть положительным целым числом",
            "specific impulse cannot be calculated for these pressures": "для заданных давлений невозможно рассчитать удельный импульс",
            "Newton method did not converge": "метод Ньютона не сошелся",
        }
        russian = russian_errors.get(english, "проверьте числовые значения во всех полях")
        return self.window._tr(english, russian)

    def _load_current_geometry(self):
        model = self.window.model
        for edit, value in (
            (self.ed_D_kr, model.D_kr),
            (self.ed_D_a, model.D_a),
            (self.ed_p_k, model.p_k),
            (self.ed_coefJ, model.coefJ),
            (self.ed_chamber_count, model.z_k),
        ):
            if value is not None:
                edit.setText(f"{value:.8g}")

    def refresh_fuel_names(self):
        """Synchronize names and available pairs with the main fuel selector."""
        selected_fuel = self.cb_fuel.currentData()
        self.cb_fuel.clear()
        for row in range(self.window.cbFuel.count()):
            fuel_idx = int(self.window.cbFuel.itemData(row))
            self.cb_fuel.addItem(self.window._fuel_name(fuel_idx), fuel_idx)
        selected_row = self.cb_fuel.findData(selected_fuel)
        if selected_row < 0:
            selected_row = max(0, self.window.cbFuel.currentIndex())
        self.cb_fuel.setCurrentIndex(selected_row)

    def _open_fuel_parameters(self):
        """Open the shared propellant-parameter editor for the selected pair."""
        fuel_idx = self.cb_fuel.currentData()
        main_row = self.window.cbFuel.findData(fuel_idx)
        if main_row >= 0:
            self.window.cbFuel.setCurrentIndex(main_row)
        self.window.open_fuel_params_dialog()
        dialog = getattr(self.window, "_fuel_params_dialog", None)
        if dialog is not None:
            dialog.finished.connect(self.refresh_fuel_names)

    def calculate(self):
        try:
            fuel_idx = int(self.cb_fuel.currentData())
            result = calculate_inverse_nozzle(
                D_kr=self._value(self.ed_D_kr),
                D_a=self._value(self.ed_D_a),
                p_k=self._value(self.ed_p_k),
                T_st=T_st_list[fuel_idx],
                R=R_st_list[fuel_idx],
                k=k_st_list[fuel_idx],
                J_st_ud=J_st_list[fuel_idx],
                coefJ=self._value(self.ed_coefJ),
                chamber_count=int(self.ed_chamber_count.text().strip()),
            )
        except Exception as error:
            QMessageBox.warning(
                self,
                self.window._tr("Nozzle Analysis", "Анализ готового сопла"),
                self.window._tr(
                    f"Check the input data: {self._error_text(error)}",
                    f"Проверьте исходные данные: {self._error_text(error)}",
                ),
            )
            return

        unit_K = self.window._tr("K", "К")
        unit_flow = self.window._tr("kg/s", "кг/с")
        unit_MPa = self.window._tr("MPa", "МПа")
        unit_impulse = self.window._tr("m/s", "м/с")
        unit_force = self.window._tr("N", "Н")
        lines = [
            self.window._tr("ENGINE PERFORMANCE FROM NOZZLE GEOMETRY", "ХАРАКТЕРИСТИКИ ДВИГАТЕЛЯ ПО ГЕОМЕТРИИ СОПЛА"),
            "-" * 62,
            f"T_k       = {result.T_k:12.3f} {unit_K}",
            f"coefJ     = {self._value(self.ed_coefJ):12.6f}",
            f"z_k       = {result.chamber_count:12d}",
            f"m_dot,1   = {result.mass_flow:12.6f} {unit_flow}",
            f"m_dot,sum = {result.total_mass_flow:12.6f} {unit_flow}",
            f"f_a       = {result.fa:12.6f}",
            f"eps       = {result.eps:12.9f}",
            f"p_a       = {result.p_a:12.6f} {unit_MPa}",
            f"J_r       = {result.J_r_ud:12.3f} {unit_impulse}",
            f"J_SL      = {result.J_SL:12.3f} {unit_impulse}",
            f"J_vac     = {result.J_vac:12.3f} {unit_impulse}",
            f"P_SL,1    = {result.P_SL_per_chamber:12.3f} {unit_force}",
            f"P_vac,1   = {result.P_vac_per_chamber:12.3f} {unit_force}",
            f"P_SL,sum  = {result.P_SL:12.3f} {unit_force}",
            f"P_vac,sum = {result.P_vac:12.3f} {unit_force}",
            "-" * 62,
            self.window._tr(
                f"Newton iterations: {result.iterations}",
                f"Итераций метода Ньютона: {result.iterations}",
            ),
        ]
        self.results.setPlainText("\n".join(lines))
        self.last_result = result
        self.btn_altitude_plot.setEnabled(True)
        if self._altitude_dialog is not None:
            self._altitude_dialog.update_result(result)

    def open_altitude_plot(self):
        if self.last_result is None:
            return
        if self._altitude_dialog is None:
            self._altitude_dialog = AltitudeThrustDialog(self, self.last_result)
        else:
            self._altitude_dialog.update_result(self.last_result)
        self._altitude_dialog.show()
        self._altitude_dialog.raise_()
        self._altitude_dialog.activateWindow()

    def set_theme(self, mode):
        if self._altitude_dialog is not None:
            self._altitude_dialog.set_theme(mode)


def open_inverse_nozzle_dialog(window):
    dialog = getattr(window, "_inverse_dialog", None)
    if dialog is None:
        dialog = InverseNozzleDialog(window)
        window._inverse_dialog = dialog
    dialog.show()
    dialog.raise_()
    dialog.activateWindow()
