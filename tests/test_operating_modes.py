import math
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication

from lre_tool.constants import COEF_J_DEFAULT
from lre_tool.model import Model
from main import Window


class ModelOperatingModeTests(unittest.TestCase):
    def setUp(self):
        self.p_k = 1.0
        self.model = Model()
        self.model.set_fuel(1)
        self.T_k = self.model.auto_Tk(self.p_k)

    def test_mode_is_authoritative_for_ambient_pressure(self):
        vacuum = Model()
        vacuum.set_fuel(1)
        vacuum.compute_geometry(
            self.p_k, 500.0, COEF_J_DEFAULT, 1.0, self.T_k, 0.001,
            p_h=0.0981, calc_mode="vacuum",
        )
        self.assertEqual(vacuum.p_h, 0.0)
        self.assertEqual(vacuum.J_calc_ud, vacuum.J_8_ud)

        sea = Model()
        sea.set_fuel(1)
        p_e_min = sea.min_p_a(COEF_J_DEFAULT, self.p_k, self.T_k)
        sea.compute_geometry(
            self.p_k, 500.0, COEF_J_DEFAULT, 1.0, self.T_k, p_e_min,
            p_h=0.0, calc_mode="sea_level",
        )
        self.assertEqual(sea.p_h, sea.p_0)
        self.assertEqual(sea.J_calc_ud, sea.J_0_ud)

    def test_minimum_exit_pressure_keeps_sea_level_impulse_positive(self):
        p_e_min = self.model.min_p_a(COEF_J_DEFAULT, self.p_k, self.T_k)
        self.model.compute_geometry(
            self.p_k, 500.0, COEF_J_DEFAULT, 1.0, self.T_k, p_e_min,
            calc_mode="sea_level",
        )
        self.assertGreater(self.model.J_0_ud, 0.0)


class WindowOperatingModeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.window = Window()
        self.window.model.set_fuel(1)

    def tearDown(self):
        self.window.close()

    def test_editing_thrust_does_not_change_selected_ambient(self):
        self.window.cb_calc_mode.setCurrentIndex(1)
        self.window._on_thrust_edited("P_0")
        self.assertEqual(self.window._current_p_h(), 0.0)

        self.window.cb_calc_mode.setCurrentIndex(0)
        self.window._on_thrust_edited("P_8")
        self.assertEqual(self.window._current_p_h(), self.window.model.p_0)

    def test_low_exit_pressure_is_limited_only_at_sea_level(self):
        p_k = 1.0
        T_k = self.window.model.auto_Tk(p_k)

        self.window._calc_mode = "sea_level"
        sea_p_e = self.window._apply_min_p_e_if_needed(p_k, T_k, 0.001)
        self.assertGreater(sea_p_e, 0.001)

        self.window._calc_mode = "vacuum"
        vacuum_p_e = self.window._apply_min_p_e_if_needed(p_k, T_k, 0.001)
        self.assertEqual(vacuum_p_e, 0.001)

    def test_negative_sea_level_thrust_can_define_positive_vacuum_thrust(self):
        p_k = 1.0
        p_e = 0.001
        T_k = self.window.model.auto_Tk(p_k)
        self.window._calc_mode = "vacuum"
        p_calc = self.window._resolve_design_thrust(
            p_k, -1435.3507084869668, "P_0", COEF_J_DEFAULT, 1.0,
            T_k, p_e, self.window._current_p_h(),
        )
        self.assertTrue(math.isclose(p_calc, 500.0, rel_tol=1e-9))
        self.assertTrue(math.isclose(float(self.window.ed_P_8.text()), 500.0, rel_tol=1e-9))


if __name__ == "__main__":
    unittest.main()
