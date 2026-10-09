import math
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication, QListView

from lre_tool.constants import COEF_J_DEFAULT
from lre_tool.inverse import calculate_inverse_nozzle, solve_exit_pressure_ratio
from lre_tool.inverse_dialog import InverseNozzleDialog
from lre_tool.model import Model
from main import Window


class InverseNozzleTests(unittest.TestCase):
    def test_area_ratio_round_trip_uses_supersonic_branch(self):
        eps, _ = solve_exit_pressure_ratio(25.0, 1.11)
        k = 1.11
        fa = (
            (2 / (k + 1)) ** ((k + 1) / (2 * (k - 1)))
            * ((k - 1) / 2) ** 0.5
            / math.sqrt(eps ** (2 / k) - eps ** ((k + 1) / k))
        )
        self.assertLess(eps, (2 / (k + 1)) ** (k / (k - 1)))
        self.assertTrue(math.isclose(fa, 25.0, rel_tol=1e-10))

    def test_inverse_recovers_forward_temperature_and_performance(self):
        model = Model()
        model.set_fuel(1)
        p_k = 10.0
        T_k = model.auto_Tk(p_k)
        model.compute_geometry(
            p_k, 10000.0, COEF_J_DEFAULT, 1.0, T_k, 0.05,
            calc_mode="sea_level",
        )
        result = calculate_inverse_nozzle(
            model.D_kr, model.D_a, p_k, model.T_st,
            model.R, model.k, model.J_st_ud,
        )
        self.assertTrue(math.isclose(result.T_k, T_k, rel_tol=1e-10))
        self.assertTrue(math.isclose(result.mass_flow, model.m_, rel_tol=1e-10))
        self.assertTrue(math.isclose(result.p_a, model.p_a, rel_tol=1e-9))
        self.assertTrue(math.isclose(result.P_SL, model.P_0, rel_tol=1e-9))
        self.assertTrue(math.isclose(result.P_vac, model.P_8, rel_tol=1e-9))

    def test_invalid_geometry_is_rejected(self):
        with self.assertRaises(ValueError):
            calculate_inverse_nozzle(30, 20, 10, 3631, 324, 1.11, 3034)

    def test_chamber_count_scales_total_flow_and_thrust(self):
        one = calculate_inverse_nozzle(21, 70, 10, 3631, 324, 1.11, 3034)
        four = calculate_inverse_nozzle(
            21, 70, 10, 3631, 324, 1.11, 3034,
            coefJ=0.95, chamber_count=4,
        )
        self.assertEqual(four.chamber_count, 4)
        self.assertTrue(math.isclose(four.total_mass_flow, 4 * one.mass_flow))
        self.assertTrue(math.isclose(four.P_SL, 4 * one.P_SL))
        self.assertTrue(math.isclose(four.P_vac, 4 * one.P_vac))
        self.assertTrue(math.isclose(four.P_SL_per_chamber, one.P_SL))

    def test_coefJ_changes_impulse_but_not_mass_flow(self):
        nominal = calculate_inverse_nozzle(21, 70, 10, 3631, 324, 1.11, 3034)
        reduced = calculate_inverse_nozzle(
            21, 70, 10, 3631, 324, 1.11, 3034, coefJ=0.90,
        )
        self.assertTrue(math.isclose(reduced.mass_flow, nominal.mass_flow))
        self.assertLess(reduced.J_r_ud, nominal.J_r_ud)
        self.assertNotEqual(reduced.P_vac, nominal.P_vac)

    def test_non_integer_chamber_count_is_rejected(self):
        with self.assertRaises(ValueError):
            calculate_inverse_nozzle(
                21, 70, 10, 3631, 324, 1.11, 3034, chamber_count=1.5,
            )

    def test_coefJ_above_one_is_rejected(self):
        with self.assertRaises(ValueError):
            calculate_inverse_nozzle(
                21, 70, 10, 3631, 324, 1.11, 3034, coefJ=1.01,
            )


class InverseNozzleDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_dialog_calculates_and_displays_results(self):
        window = Window()
        dialog = InverseNozzleDialog(window)
        dialog.calculate()
        self.assertIn("T_k", dialog.results.toPlainText())
        self.assertIn("m_dot,sum", dialog.results.toPlainText())
        self.assertIn("P_vac,sum", dialog.results.toPlainText())
        dialog.close()
        window.close()

    def test_dialog_applies_coefficient_and_chamber_count(self):
        window = Window()
        dialog = InverseNozzleDialog(window)
        dialog.ed_coefJ.setText("0.9")
        dialog.ed_chamber_count.setText("3")
        dialog.calculate()
        text = dialog.results.toPlainText()
        self.assertIn("coefJ     =     0.900000", text)
        self.assertIn("z_k       =            3", text)
        dialog.close()
        window.close()

    def test_dialog_retranslates_with_main_window(self):
        window = Window()
        dialog = InverseNozzleDialog(window)
        window._inverse_dialog = dialog
        self.assertEqual(dialog.btn_calculate.text(), "Calculate")
        self.assertEqual(window.btn_inverse_calc.text(), "Nozzle Analysis")
        self.assertEqual(dialog.windowTitle(), "Engine Performance from Nozzle Geometry")
        dialog.calculate()
        window._toggle_language()
        self.assertEqual(dialog.btn_calculate.text(), "Рассчитать")
        self.assertEqual(window.btn_inverse_calc.text(), "Анализ готового сопла")
        self.assertEqual(dialog.lbl_fuel.text(), "Топливная пара")
        self.assertEqual(dialog.windowTitle(), "Расчет характеристик двигателя по геометрии сопла")
        self.assertIn("ХАРАКТЕРИСТИКИ ДВИГАТЕЛЯ ПО ГЕОМЕТРИИ СОПЛА", dialog.results.toPlainText())
        self.assertIn("м/с", dialog.results.toPlainText())
        dialog.close()
        window.close()

    def test_combo_popups_have_explicit_readable_selection_colors(self):
        window = Window()
        dialog = InverseNozzleDialog(window)
        for combo in (dialog.cb_fuel,):
            self.assertIsInstance(combo.view(), QListView)
            stylesheet = combo.view().styleSheet()
            self.assertIn("selection-color: palette(highlighted-text)", stylesheet)
            self.assertIn("selection-background-color: palette(highlight)", stylesheet)
        dialog.close()
        window.close()

    def test_propellant_parameters_button_opens_shared_dialog(self):
        window = Window()
        dialog = InverseNozzleDialog(window)
        window._inverse_dialog = dialog
        dialog.cb_fuel.setCurrentIndex(1)
        selected_fuel = dialog.cb_fuel.currentData()
        dialog.btn_fuel_params.click()
        self.app.processEvents()
        self.assertTrue(window._fuel_params_dialog.isVisible())
        self.assertEqual(window.cbFuel.currentData(), selected_fuel)
        window._fuel_params_dialog.close()
        dialog.close()
        window.close()


if __name__ == "__main__":
    unittest.main()
