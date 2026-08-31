import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QMessageBox

from lre_tool.constants import (
    J_st_list,
    PARA,
    PARA_DEFAULT,
    PARA_RU,
    R_st_list,
    T_st_list,
    k_m_list,
    k_st_list,
)
from lre_tool.dialogs import open_fuel_parameters_dialog
from main import Window


class PropellantReferenceTableTests(unittest.TestCase):
    def test_names_and_numeric_tables_have_matching_lengths(self):
        pair_count = len(PARA)
        self.assertEqual(len(PARA_DEFAULT), pair_count)
        self.assertEqual(len(PARA_RU), pair_count)
        for values in (k_m_list, R_st_list, k_st_list, T_st_list, J_st_list):
            self.assertEqual(len(values), pair_count + 1)
            self.assertIsNone(values[0])

    def test_nitric_acid_kerosene_reference_gas_constant(self):
        self.assertEqual(PARA[7], "Nitric acid 98% - Kerosene")
        self.assertEqual(R_st_list[8], 315)


class PropellantPairDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.window = Window()

    def tearDown(self):
        dialog = getattr(self.window, "_fuel_params_dialog", None)
        if dialog is not None:
            dialog.close()
        self.window.close()

    def test_localized_names_use_one_based_pair_ids(self):
        self.window._language = "en"
        self.assertEqual(self.window._fuel_name(1), PARA[0].strip())
        self.assertEqual(self.window._fuel_name(len(PARA)), PARA[-1].strip())

        self.window._language = "ru"
        self.assertEqual(self.window._fuel_name(1), PARA_RU[0].strip())
        self.assertEqual(self.window._fuel_name(len(PARA)), PARA_RU[-1].strip())

    def test_dialog_lists_every_pair_with_its_own_parameters(self):
        self.window._language = "en"
        open_fuel_parameters_dialog(self.window)

        self.assertEqual(self.window.list_fuels.count(), len(PARA))
        self.assertEqual(self.window.list_fuels.item(0).text(), PARA[0].strip())
        self.assertEqual(self.window.list_fuels.item(len(PARA) - 1).text(), PARA[-1].strip())

        for row in range(len(PARA)):
            fuel_idx = row + 1
            self.window.list_fuels.setCurrentRow(row)
            self.assertEqual(self.window.ed_fuel_name.text(), PARA[row].strip())
            self.assertAlmostEqual(float(self.window.ed_k_m.text()), k_m_list[fuel_idx])
            self.assertAlmostEqual(float(self.window.ed_R.text()), R_st_list[fuel_idx])
            self.assertAlmostEqual(float(self.window.ed_k.text()), k_st_list[fuel_idx])
            self.assertAlmostEqual(float(self.window.ed_Tst.text()), T_st_list[fuel_idx])
            self.assertAlmostEqual(float(self.window.ed_Jst.text()), J_st_list[fuel_idx])

    def test_hiding_pair_does_not_renumber_reference_ids(self):
        open_fuel_parameters_dialog(self.window)
        pair_count = len(PARA)
        numeric_lengths = tuple(
            len(values)
            for values in (k_m_list, R_st_list, k_st_list, T_st_list, J_st_list)
        )

        self.window.list_fuels.setCurrentRow(1)
        self.assertEqual(self.window.list_fuels.currentItem().data(Qt.UserRole), 2)
        with patch.object(QMessageBox, "question", return_value=QMessageBox.Yes):
            self.window.btn_delete_fuel.click()

        self.assertEqual(self.window.cbFuel.count(), pair_count - 1)
        self.assertEqual(self.window.cbFuel.findData(2), -1)
        self.assertGreaterEqual(self.window.cbFuel.findData(3), 0)
        self.assertEqual(
            tuple(len(values) for values in (k_m_list, R_st_list, k_st_list, T_st_list, J_st_list)),
            numeric_lengths,
        )
        visible_ids = [
            self.window.list_fuels.item(row).data(Qt.UserRole)
            for row in range(self.window.list_fuels.count())
        ]
        self.assertNotIn(2, visible_ids)
        self.assertIn(3, visible_ids)


if __name__ == "__main__":
    unittest.main()
