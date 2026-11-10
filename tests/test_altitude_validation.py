"""Independent engineering checks for the thrust-versus-altitude curve."""

import math
import unittest

from lre_tool.constants import J_st_list, R_st_list, T_st_list, k_st_list
from lre_tool.inverse import (
    calculate_altitude_thrust_curve,
    calculate_inverse_nozzle,
    standard_atmosphere_pressure_mpa,
)


class AltitudeCurveValidationTests(unittest.TestCase):
    CASES = (
        # fuel index, throat [mm], exit [mm], chamber pressure [MPa], chambers
        (1, 21.0, 70.0, 10.0, 1),
        (2, 30.0, 110.0, 8.0, 2),
        (4, 40.0, 130.0, 15.0, 4),
    )

    @staticmethod
    def _result(case):
        fuel, throat, exit_diameter, chamber_pressure, chambers = case
        return calculate_inverse_nozzle(
            throat,
            exit_diameter,
            chamber_pressure,
            T_st_list[fuel],
            R_st_list[fuel],
            k_st_list[fuel],
            J_st_list[fuel],
            chamber_count=chambers,
        )

    def test_control_points_and_monotonicity(self):
        for case in self.CASES:
            with self.subTest(case=case):
                result = self._result(case)
                curve = calculate_altitude_thrust_curve(result)
                self.assertTrue(math.isclose(curve.thrust[0], result.P_SL, rel_tol=1e-12))
                self.assertTrue(math.isclose(curve.thrust[-1], result.P_vac, rel_tol=5e-8))
                self.assertTrue(all(
                    left <= right
                    for left, right in zip(curve.thrust, curve.thrust[1:])
                ))
                if curve.matched_altitude_km is not None:
                    matched_pressure = standard_atmosphere_pressure_mpa(
                        curve.matched_altitude_km
                    )
                    self.assertTrue(math.isclose(
                        matched_pressure, result.p_a, rel_tol=2e-3
                    ))

    def test_against_independent_pressure_thrust_equation(self):
        """Compare P(h) with P_vac - p_amb(h) * geometric exit area."""
        validation_altitudes = (0.0, 5.0, 10.0, 20.0, 50.0, 100.0)
        for case in self.CASES:
            with self.subTest(case=case):
                result = self._result(case)
                _, _, exit_diameter, _, chambers = case
                geometric_exit_area_mm2 = (
                    math.pi * exit_diameter ** 2 / 4.0 * chambers
                )
                effective_exit_area_mm2 = (
                    result.total_mass_flow
                    * (result.J_vac - result.J_r_ud)
                    / result.p_a
                )

                # The semi-empirical impulse and 0.98 discharge correction make
                # the pressure term slightly different from pure geometric theory.
                self.assertLess(
                    abs(effective_exit_area_mm2 / geometric_exit_area_mm2 - 1.0),
                    0.02,
                )
                for altitude in validation_altitudes:
                    ambient_pressure = standard_atmosphere_pressure_mpa(altitude)
                    application_thrust = (
                        result.P_vac - ambient_pressure * effective_exit_area_mm2
                    )
                    independent_thrust = (
                        result.P_vac - ambient_pressure * geometric_exit_area_mm2
                    )
                    self.assertLess(
                        abs(application_thrust - independent_thrust)
                        / abs(independent_thrust),
                        0.0011,
                    )


if __name__ == "__main__":
    unittest.main()
