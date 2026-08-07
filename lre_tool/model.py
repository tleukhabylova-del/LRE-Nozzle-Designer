"""Original engine and nozzle geometry model."""

from dataclasses import dataclass
from typing import Optional

import numpy as np
from scipy.optimize import fsolve, minimize_scalar

from .constants import (
    COEF_J_DEFAULT, J_st_list, R_st_list, T_st_list, k_m_list, k_st_list,
)


@dataclass
class GeometryState:
    """Per-window nozzle geometry used by background calculations and plots."""

    a1: Optional[float] = None
    a2: Optional[float] = None
    alpha1: Optional[float] = None
    alpha2: Optional[float] = None
    D_k: Optional[float] = None
    D_kr: Optional[float] = None
    D_a: Optional[float] = None
    R_k: Optional[float] = None
    R_kr: Optional[float] = None
    R_a: Optional[float] = None
    R3: Optional[float] = None
    L_g: Optional[float] = None
    L_cy: Optional[float] = None
    L_vh: Optional[float] = None
    L_c: Optional[float] = None
    L_dv: Optional[float] = None
    k: Optional[float] = None
    x: Optional[np.ndarray] = None

    def update_from_model(self, model) -> None:
        """Copy already-computed values; do not recalculate engineering data."""
        for name in (
            "a1", "a2", "alpha1", "alpha2", "D_k", "D_kr", "D_a",
            "R_k", "R_kr", "R_a", "R3", "L_g", "L_cy", "L_vh",
            "L_c", "L_dv", "k",
        ):
            value = getattr(model, name, None)
            setattr(self, name, None if value is None else float(value))
        self.x = None

class Model:
    def __init__(self):
        self.idx = 1
        self.k_m = None
        self.R = None
        self.k = None
        self.T_st = None
        self.J_st_ud = None
        # Input parameters.
        self.p_k = None  # MPa
        self.P_calc = None  # N
        self.P_h = None  # N
        self.P_0 = None  # N
        self.P_8 = None  # N
        self.coefJ = COEF_J_DEFAULT
        self.z_k = None
        self.T_k = None  # K
        self.p_e = None  # MPa
        self.p_h = None  # MPa
        self.p_a = None  # MPa
        self.p_0 = 0.0981  # MPa
        self.p = 0.0981  # MPa
        self.k1 = None

        # --- Geometry ---
        self.J_pr_ud_st = None
        self.J_r_ud = None
        self.J_h_ud = None
        self.J_8_ud = None
        self.J_0_ud = None
        self.m_ = None
        self.m_g = None
        self.m_ok = None
        self.K_0 = None
        self.D_kr = None
        self.fa = None
        self.D_a = None
        self.D_k = None

        # Parameters used to construct the nozzle contour.
        self.a = 5.0
        self.b1 = 5.0
        self.c1 = 0.0
        self.a1 = self.a
        self.a2 = self.a
        self.alpha1 = 20 * np.pi / 180.0
        self.alpha2 = 8 * np.pi / 180.0
        self.R0 = None
        self.R1 = None
        self.R2 = None
        self.R3 = None
        self.R4 = None
        self.gamma = None
        self.betta = None

        self.R_kr = None
        self.R_a = None
        self.R_k = None
        self.R3 = None
        self.L_c = None
        self.L_vh = None
        self.L_g = None
        self.L_cy = None
        self.L_dv = None
        self.L_du = None

    def set_fuel(self, idx: int):
        # Load the thermodynamic constants associated with the selected propellant pair.
        self.idx = idx
        self.k_m = k_m_list[idx]
        self.R = R_st_list[idx]
        self.k = k_st_list[idx]
        self.T_st = T_st_list[idx]
        self.J_st_ud = J_st_list[idx]

    def auto_Tk(self, p_k: float) -> float:
        if self.T_st is None or p_k is None:
            return None
        return self.T_st * (86.9 - 0.578 * p_k + 6.27 * p_k ** 0.5) / 100.0

    def min_p_a(self, coefJ: float, p_k: float, T_k: float) -> float:
        k1 = (self.k - 1) / self.k
        self.k1 = k1
        R = self.R
        J_st_ud = self.J_st_ud
        p = self.p
        fJr = lambda p_a: coefJ * J_st_ud * (0.67 - 0.016 * p_k + 0.163 * p_k ** 0.5) * np.sqrt(
            (1 - (p_a / p_k) ** k1) * p_k ** k1 / (p_k ** k1 - 0.0981 ** k1))
        fJ8 = lambda p_a: fJr(p_a) + R * T_k * (p_a / p_k) ** k1 / fJr(p_a)
        f = lambda p_a: fJ8(p_a) - R * T_k * (p_a / p_k) ** k1 / fJr(p_a) * (p / p_a)
        a = 20.0
        for x0 in range(1, 100):
            root, info, ier, msg = fsolve(f, x0 / 1000.0, full_output=True, maxfev=10000, xtol=1e-12)
            if ier == 1:
                a = float(root[0])
        return a + 0.000000001
        0.000000001
        0.005861015066065835
        0.005861015066

    def calc_J_at_ambient(self, p_e, p_amb):
        delta = self.R * self.T_k * (p_e / self.p_k) ** self.k1 / self.J_r_ud
        return self.J_8_ud - delta * (p_amb / p_e)

    def compute_geometry(self, p_k, P_calc, coefJ, z_k, T_k, p_e, p_h=0.0981, calc_mode="sea_level"):
        # Convert the design inputs into specific impulse, mass flow, and nozzle dimensions.
        self.p_k, self.P_calc, self.P_h = p_k, P_calc, P_calc
        self.coefJ, self.z_k, self.T_k = coefJ, z_k, T_k
        self.p_e, self.p_h, self.p_a = p_e, p_h, p_e
        self.calc_mode = calc_mode
        self.k1 = (self.k - 1) / self.k
        eps = self.p_e / self.p_k

        self.J_pr_ud_st = self.coefJ * self.J_st_ud
        self.J_r_ud = self.J_pr_ud_st * (0.67 - 0.016 * self.p_k + 0.163 * self.p_k ** 0.5) * np.sqrt(
            (1 - eps ** self.k1) * self.p_k ** self.k1 / (self.p_k ** self.k1 - 0.0981 ** self.k1))
        self.J_8_ud = self.J_r_ud + self.R * self.T_k * eps ** self.k1 / self.J_r_ud
        self.J_0_ud = self.calc_J_at_ambient(self.p_e, self.p_0)
        self.J_h_ud = self.calc_J_at_ambient(self.p_e, self.p_h)
        if self.J_h_ud <= 0:
            raise ValueError("specific impulse in selected design mode is non-positive")
        self.m_ = self.P_calc / (self.z_k * self.J_h_ud)
        self.P_0 = self.m_ * self.z_k * self.J_0_ud
        self.P_8 = self.m_ * self.z_k * self.J_8_ud
        self.P_h = self.m_ * self.z_k * self.J_h_ud

        self.m_g = self.m_ / (1 + self.k_m)
        self.m_ok = self.m_ * self.k_m / (1 + self.k_m)
        self.K_0 = (2 / (self.k + 1)) ** ((self.k + 1) / 2 / (self.k - 1)) * np.sqrt(self.k)

        self.D_kr = np.sqrt(4 * self.m_ * np.sqrt(self.R * self.T_k) / (0.98 * np.pi * self.K_0 * self.p_k))
        self.fa = (2 / (self.k + 1)) ** ((self.k + 1) / (2 * (self.k - 1))) * ((self.k - 1) / 2) ** 0.5 / np.sqrt(
            (self.p_e / self.p_k) ** (2 / self.k) - (self.p_e / self.p_k) ** ((self.k + 1) / self.k))
        self.D_a = self.D_kr * np.sqrt(self.fa)
        self.D_k = self.D_kr * 2

        self.R_kr = self.D_kr / 2
        self.R_a = self.D_a / 2
        self.R_k = self.D_k / 2

        EO = self.R_a - self.R_kr

        self.R3 = 2 * self.R_kr

        self.L_c = (
                (EO - self.R3 * (1 - np.cos(self.alpha1)))
                * (np.sin(self.alpha1) - np.sin(self.alpha2))
                / (np.cos(self.alpha2) - np.cos(self.alpha1))
                + self.R3 * np.sin(self.alpha1)
        )

        self.R4 = (
                          EO
                          - self.R3 * (1 - np.cos(self.alpha1))
                          - self.a * (np.sin(self.alpha1) + np.sin(self.alpha2))
                  ) / (np.cos(self.alpha2) - np.cos(self.alpha1))

        self.L_vh = 0.5 * np.sqrt(
            self.D_k ** 2 + 3 * self.D_k * self.D_kr - 4 * self.D_kr ** 2
        )

        self.L_g = 0.25 * self.D_k
        self.L_cy = 1.25 * self.D_k
        self.L_dv = self.L_g + self.L_cy + self.L_vh + self.L_c
        self.L_du = 2 * (self.L_c + self.L_vh)

        d = self.R_k - self.R_kr

        A = (self.L_vh + self.b1) ** 2 + d ** 2
        B = -2 * (self.L_vh + self.b1) ** 2
        C = (self.L_vh + self.b1) ** 2 - d ** 2
        D = B ** 2 - 4 * A * C

        cos_betta = (-B - np.sqrt(D)) / (2 * A)
        self.betta = np.arccos(cos_betta)

        self.R2 = (self.L_vh ** 2 + d ** 2 - self.b1 ** 2) / (2 * d) - self.R3

        self.R1 = self.R_k / 4

        cos_gamma = (
                -2 * (self.L_g - self.R1) * (self.R1 - self.c1 - self.R_k)
                / ((self.L_g - self.R1) ** 2 + (self.R1 - self.c1 - self.R_k) ** 2)
        )

        self.gamma = np.arccos(cos_gamma)

        self.R0 = (
                          self.L_g ** 2
                          + self.R_k ** 2
                          - self.c1 ** 2
                          - 2 * self.R_k * self.R1
                  ) / (2 * (self.L_g - self.R1))

        return {
            'D_kr': self.D_kr, 'D_a': self.D_a, 'D_k': self.D_k, 'f_a': self.fa,
            'J*_пр,уд,ст': self.J_pr_ud_st, 'J*_р,уд': self.J_r_ud,
            'J*_h,уд': self.J_h_ud, 'J*_8,уд': self.J_8_ud, 'J*_0,уд': self.J_0_ud,
            'ṁ сум': self.m_, 'ṁ_г': self.m_g, 'ṁ_ок': self.m_ok, 'K0': self.K_0,
            'L_g': self.L_g, 'L_ц': self.L_cy, 'L_вх': self.L_vh, 'L_c': self.L_c, 'Lдв': self.L_dv
        }

    # ====== NOZZLE CONTOUR ======
    def take_x_y(self):
        # Generate the chamber and nozzle contour used by plots and downstream calculations.
        x_head0 = -(self.L_g + self.L_cy + self.L_vh)
        x_cyl0 = -(self.L_cy + self.L_vh)
        x_conv0 = -self.L_vh

        # 1. Chamber head section.
        O0 = np.array([self.R0, 0.0])
        O1 = np.array([self.L_g, self.R_k - self.R1])

        B = np.array([
            self.R0 * (1 - np.sin(self.gamma)),
            self.R0 * np.cos(self.gamma)
        ])

        C = np.array([
            O1[0] - self.R1 * np.sin(self.gamma),
            O1[1] + self.R1 * np.cos(self.gamma)
        ])

        t0 = np.linspace(np.pi, np.pi / 2 + self.gamma, 200)
        x_head_arc0 = x_head0 + O0[0] + self.R0 * np.cos(t0)
        y_head_arc0 = O0[1] + self.R0 * np.sin(t0)

        x_head_line = x_head0 + np.array([B[0], C[0]])
        y_head_line = np.array([B[1], C[1]])

        t1 = np.linspace(np.pi / 2 + self.gamma, np.pi / 2, 200)
        x_head_arc1 = x_head0 + O1[0] + self.R1 * np.cos(t1)
        y_head_arc1 = O1[1] + self.R1 * np.sin(t1)

        # 2. Cylindrical chamber section.
        x_cyl = np.array([x_cyl0, x_conv0])
        y_cyl = np.array([self.R_k, self.R_k])

        # 3. Converging section leading to the throat.
        d = self.R_k - self.R_kr

        O2 = np.array([0.0, d - self.R2])
        O3 = np.array([self.L_vh, self.R3])

        P2 = np.array([
            O2[0] + self.R2 * np.sin(self.betta),
            O2[1] + self.R2 * np.cos(self.betta)
        ])

        P3 = np.array([
            O3[0] - self.R3 * np.sin(self.betta),
            O3[1] - self.R3 * np.cos(self.betta)
        ])

        t2 = np.linspace(np.pi / 2, np.pi / 2 - self.betta, 200)
        x_conv_arc2 = x_conv0 + O2[0] + self.R2 * np.cos(t2)
        y_conv_arc2 = self.R_kr + O2[1] + self.R2 * np.sin(t2)

        x_conv_line = x_conv0 + np.array([P2[0], P3[0]])
        y_conv_line = self.R_kr + np.array([P2[1], P3[1]])

        t3 = np.linspace(3 * np.pi / 2 - self.betta, 3 * np.pi / 2, 200)
        x_conv_arc3 = x_conv0 + O3[0] + self.R3 * np.cos(t3)
        y_conv_arc3 = self.R_kr + O3[1] + self.R3 * np.sin(t3)

        # 4. Diverging nozzle section.
        B = np.array([
            self.R3 * np.sin(self.alpha1),
            self.R3 * (1 - np.cos(self.alpha1))
        ])

        C = B + self.a * np.array([
            np.cos(self.alpha1),
            np.sin(self.alpha1)
        ])

        O4 = np.array([
            C[0] + self.R4 * np.sin(self.alpha1),
            C[1] - self.R4 * np.cos(self.alpha1)
        ])

        D = O4 + np.array([
            -self.R4 * np.sin(self.alpha2),
            self.R4 * np.cos(self.alpha2)
        ])

        E = D + self.a * np.array([
            np.cos(self.alpha2),
            np.sin(self.alpha2)
        ])

        O3_div = np.array([0.0, self.R3])

        t4 = np.linspace(-np.pi / 2, -np.pi / 2 + self.alpha1, 200)
        x_div_arc3 = O3_div[0] + self.R3 * np.cos(t4)
        y_div_arc3 = self.R_kr + O3_div[1] + self.R3 * np.sin(t4)

        x_div_line1 = np.array([B[0], C[0]])
        y_div_line1 = self.R_kr + np.array([B[1], C[1]])

        t5 = np.linspace(np.pi / 2 + self.alpha1, np.pi / 2 + self.alpha2, 300)
        x_div_arc4 = O4[0] + self.R4 * np.cos(t5)
        y_div_arc4 = self.R_kr + O4[1] + self.R4 * np.sin(t5)

        x_div_line2 = np.array([D[0], E[0]])
        y_div_line2 = self.R_kr + np.array([D[1], E[1]])

        x_contour = np.concatenate([
            x_head_arc0,
            x_head_line,
            x_head_arc1,
            x_cyl,
            x_conv_arc2,
            x_conv_line,
            x_conv_arc3,
            x_div_arc3,
            x_div_line1,
            x_div_arc4,
            x_div_line2
        ])

        y_contour = np.concatenate([
            y_head_arc0,
            y_head_line,
            y_head_arc1,
            y_cyl,
            y_conv_arc2,
            y_conv_line,
            y_conv_arc3,
            y_div_arc3,
            y_div_line1,
            y_div_arc4,
            y_div_line2
        ])

        xmin = np.min(x_contour)
        x_contour = x_contour - xmin

        X = [
            0,
            self.L_g,
            self.L_g + self.L_cy,
            self.L_g + self.L_cy + self.L_vh,
            self.L_g + self.L_cy + self.L_vh + self.L_c,
            self.L_g + self.L_cy + self.L_vh + self.L_c
        ]

        Y = [
            0,
            self.R_k,
            self.R_k,
            self.R_kr,
            self.R_a,
            0
        ]

        return x_contour, y_contour, X, Y
