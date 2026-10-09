"""Standalone application dialogs."""

import os

from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QDialog, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QMessageBox, QPushButton, QVBoxLayout, QWidget,
)

from .constants import (
    J_st_list, PARA, PARA_DEFAULT, PARA_RU, R_st_list, T_st_list,
    k_m_list, k_st_list,
)


def open_fuel_parameters_dialog(window):
    dlg = QDialog(window)
    dlg.setWindowTitle(window._tr("Propellant Pair Parameters", "Параметры топливной пары"))
    dlg.setModal(False)

    main = QHBoxLayout(dlg)
    main.setContentsMargins(8, 8, 12, 12)
    main.setSpacing(22)

    # ===== LEFT SIDE: propellant-pair list =====
    left = QWidget()
    left_layout = QVBoxLayout(left)
    left_layout.setContentsMargins(0, 0, 0, 0)
    left_layout.setSpacing(6)

    top_left = QHBoxLayout()
    top_left.setSpacing(6)

    window.ed_selected_fuel_name = QLineEdit()
    window.ed_selected_fuel_name.setReadOnly(True)
    window.ed_selected_fuel_name.setMinimumHeight(26)

    # window.btn_edit_fuel = QPushButton("✎")
    window.btn_edit_fuel = QPushButton()
    window.btn_edit_fuel.setFixedSize(26, 26)

    window.icon_edit_normal = QIcon("editing-pencil 0.png")
    window.icon_edit_hover = QIcon("editing-pencil.png")
    import os

    print("Launch directory:", os.getcwd())
    print("normal exists:", os.path.exists("editing-pencil 0.png"))
    print("hover exists:", os.path.exists("editing-pencil.png"))
    print("normal isNull:", window.icon_edit_normal.isNull())
    print("hover isNull:", window.icon_edit_hover.isNull())

    window.btn_edit_fuel.setIcon(window.icon_edit_normal)
    window.btn_edit_fuel.setIconSize(QSize(17, 17))

    window.btn_edit_fuel.setStyleSheet("""
        QPushButton {
            border-radius: 13px;
            border: 1px solid transparent;
            background-color: transparent;
            padding: 0px;
        }

        QPushButton:hover {
            border: 1px solid transparent;
            background-color: transparent;
        }

        QPushButton:pressed {
            border: 1px solid #6200EE;
            background-color: transparent;
        }
    """)

    window.btn_edit_fuel.installEventFilter(window)

    window.btn_delete_fuel = QPushButton()
    window.btn_delete_fuel.setFixedSize(26, 26)

    window.icon_delete_normal = QIcon("delete 0.png")
    window.icon_delete_hover = QIcon("delete.png")

    window.btn_delete_fuel.setIcon(window.icon_delete_normal)
    window.btn_delete_fuel.setIconSize(QSize(17, 17))

    window.btn_delete_fuel.setStyleSheet("""
        QPushButton {
            border-radius: 13px;
            border: 1px solid transparent;
            background-color: transparent;
            padding: 0px;
        }

        QPushButton:hover {
            border: 1px solid transparent;
            background-color: transparent;
        }

        QPushButton:pressed {
            border: 1px solid #c0392b;
            background-color: transparent;
        }
    """)

    window.btn_delete_fuel.installEventFilter(window)

    top_left.addWidget(window.ed_selected_fuel_name)
    top_left.addWidget(window.btn_edit_fuel)
    top_left.addWidget(window.btn_delete_fuel)

    window.list_fuels = QListWidget()
    window.list_fuels.setMinimumWidth(400)
    window.list_fuels.setMinimumHeight(270)

    for combo_row in range(window.cbFuel.count()):
        fuel_idx = int(window.cbFuel.itemData(combo_row))
        window.list_fuels.addItem(window._fuel_name(fuel_idx))
        window.list_fuels.item(window.list_fuels.count() - 1).setData(Qt.UserRole, fuel_idx)

    left_layout.addLayout(top_left)
    left_layout.addWidget(window.list_fuels)

    main.addWidget(left)

    # ===== RIGHT SIDE: parameters of the selected pair =====
    right = QWidget()
    right_layout = QVBoxLayout(right)
    right_layout.setContentsMargins(0, 0, 0, 0)
    right_layout.setSpacing(10)

    grid = QGridLayout()
    grid.setHorizontalSpacing(14)
    grid.setVerticalSpacing(10)

    window.ed_fuel_name = QLineEdit()
    window.ed_fuel_name.setMinimumHeight(28)
    window.ed_fuel_name.setFixedWidth(315)

    window._fuel_dialog_labels = []

    def add_dialog_row(r, english, russian, widget):
        lbl = QLabel(window._tr(english, russian))
        lbl.setWordWrap(True)
        lbl.setMinimumHeight(34)
        grid.addWidget(lbl, r, 0, alignment=Qt.AlignLeft | Qt.AlignVCenter)
        grid.addWidget(widget, r, 1, alignment=Qt.AlignLeft | Qt.AlignVCenter)
        window._fuel_dialog_labels.append((lbl, english, russian))

    row = 0
    add_dialog_row(row, "Propellant pair name", "Название топливной пары", window.ed_fuel_name)
    row += 1

    add_dialog_row(row, "Propellant mass ratio K_m", "Массовое соотношение компонентов K_m", window.ed_k_m)
    row += 1

    add_dialog_row(row, "Specific gas constant R_g", "Удельная газовая постоянная R_g", window.ed_R)
    row += 1

    add_dialog_row(row, "Specific heat ratio gamma", "Показатель адиабаты γ", window.ed_k)
    row += 1

    add_dialog_row(row, "Reference combustion temperature T_ref", "Опорная температура горения T_ref", window.ed_Tst)
    row += 1

    add_dialog_row(row, "Reference specific impulse J_ref", "Опорный удельный импульс J_ref", window.ed_Jst)
    row += 1

    right_layout.addLayout(grid)

    buttons = QHBoxLayout()
    buttons.addStretch(1)

    window.btn_save_fuel_params = QPushButton(window._tr("Save", "Сохранить"))
    window.btn_save_fuel_params.setMinimumWidth(90)

    window.btn_close_fuel_params = QPushButton(window._tr("Close", "Закрыть"))
    window.btn_close_fuel_params.setMinimumWidth(90)
    window.btn_close_fuel_params.clicked.connect(dlg.close)

    buttons.addWidget(window.btn_save_fuel_params)
    buttons.addWidget(window.btn_close_fuel_params)

    right_layout.addLayout(buttons)

    main.addWidget(right)

    # ===== Dialog behavior =====
    def load_fuel_from_list(row_idx):
        if row_idx < 0:
            return

        fuel_idx = int(window.list_fuels.item(row_idx).data(Qt.UserRole))

        window.ed_selected_fuel_name.setText(window._fuel_name(fuel_idx))
        window.ed_fuel_name.setText(window._fuel_name(fuel_idx))

        window.ed_k_m.setText("" if k_m_list[fuel_idx] is None else f"{k_m_list[fuel_idx]:.6g}")
        window.ed_R.setText("" if R_st_list[fuel_idx] is None else f"{R_st_list[fuel_idx]:.6g}")
        window.ed_k.setText("" if k_st_list[fuel_idx] is None else f"{k_st_list[fuel_idx]:.6g}")
        window.ed_Tst.setText("" if T_st_list[fuel_idx] is None else f"{T_st_list[fuel_idx]:.6g}")
        window.ed_Jst.setText("" if J_st_list[fuel_idx] is None else f"{J_st_list[fuel_idx]:.6g}")

    def save_current_fuel():
        row_idx = window.list_fuels.currentRow()
        if row_idx < 0:
            return

        fuel_idx = int(window.list_fuels.item(row_idx).data(Qt.UserRole))
        name = window.ed_fuel_name.text().strip()

        if not name:
            QMessageBox.warning(window, window._tr("Error", "Ошибка"),
                                window._tr("Enter a propellant pair name.", "Введите название топливной пары."))
            return

        try:
            km = float(window.ed_k_m.text().replace(",", "."))
            R = float(window.ed_R.text().replace(",", "."))
            k = float(window.ed_k.text().replace(",", "."))
            Tst = float(window.ed_Tst.text().replace(",", "."))
            Jst = float(window.ed_Jst.text().replace(",", "."))
        except Exception:
            QMessageBox.warning(window, window._tr("Error", "Ошибка"),
                                window._tr("Check the numeric propellant parameters.",
                                         "Проверьте числовые параметры топлива."))
            return

        name_idx = fuel_idx - 1
        PARA[name_idx] = name
        PARA_DEFAULT[name_idx] = name
        PARA_RU[name_idx] = name
        k_m_list[fuel_idx] = km
        R_st_list[fuel_idx] = R
        k_st_list[fuel_idx] = k
        T_st_list[fuel_idx] = Tst
        J_st_list[fuel_idx] = Jst

        window.list_fuels.item(row_idx).setText(name)
        window.ed_selected_fuel_name.setText(name)

        combo_row = window.cbFuel.findData(fuel_idx)
        if combo_row >= 0:
            window.cbFuel.setItemText(combo_row, name)
            window.cbFuel.setCurrentIndex(combo_row)

        window.on_change()
        window.timer.start()
        inverse_dialog = getattr(window, "_inverse_dialog", None)
        if inverse_dialog is not None:
            inverse_dialog.refresh_fuel_names()

    def edit_fuel_name():
        window.ed_fuel_name.setFocus()
        window.ed_fuel_name.selectAll()

    def delete_current_fuel():
        row_idx = window.list_fuels.currentRow()
        if row_idx < 0:
            return

        fuel_idx = int(window.list_fuels.item(row_idx).data(Qt.UserRole))

        reply = QMessageBox.question(
            window,
            window._tr("Delete", "Удаление"),
            window._tr("Delete the selected propellant pair?", "Удалить выбранную топливную пару?"),
            QMessageBox.Yes | QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        window.list_fuels.takeItem(row_idx)
        combo_row = window.cbFuel.findData(fuel_idx)
        if combo_row >= 0:
            window.cbFuel.removeItem(combo_row)

        if window.list_fuels.count() > 0:
            new_row = min(row_idx, window.list_fuels.count() - 1)
            window.list_fuels.setCurrentRow(new_row)
            window.cbFuel.setCurrentIndex(new_row)

        window.on_change()
        window.timer.start()
        inverse_dialog = getattr(window, "_inverse_dialog", None)
        if inverse_dialog is not None:
            inverse_dialog.refresh_fuel_names()

    window.list_fuels.currentRowChanged.connect(load_fuel_from_list)
    window.btn_save_fuel_params.clicked.connect(save_current_fuel)
    window.btn_edit_fuel.clicked.connect(edit_fuel_name)
    window.btn_delete_fuel.clicked.connect(delete_current_fuel)

    current_row = window.cbFuel.currentIndex()
    window.list_fuels.setCurrentRow(current_row)

    dlg.resize(760, 360)
    dlg.show()

    window._fuel_params_dialog = dlg
