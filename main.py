
import sys, re, os, html
from datetime import datetime
import numpy as np
from collections import defaultdict
import csv
from pathlib import Path
import pandas as pd

from PyQt5.QtWidgets import QSizePolicy
from PyQt5 import QtCore
from PyQt5.QtCore import Qt, QTimer, QEvent, QLocale
from PyQt5.QtGui import QDoubleValidator, QFont, QColor, QPalette, QCursor
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QGridLayout, QVBoxLayout,
    QLabel, QLineEdit, QComboBox, QMessageBox, QCheckBox, QHBoxLayout, QPushButton,
    QTextEdit, QProgressBar, QStatusBar, QStackedWidget, QFrame,
    QFileDialog, QInputDialog, QWidgetAction, QScrollArea, QListView,
    QToolTip, QListWidget
)
from PyQt5.QtWidgets import QDialog, QDialogButtonBox
from PyQt5.QtGui import QTextOption
from PyQt5.QtWidgets import QStyle

from PyQt5.QtWidgets import QPushButton
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QSize, QEvent

from scipy.optimize import fsolve, minimize_scalar
from scipy import ndimage

# --- Matplotlib внутри окна ---
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.image as mpimg
from matplotlib.patches import FancyArrowPatch
from matplotlib.collections import PolyCollection
from matplotlib.colors import Normalize
import matplotlib.cm as cm
from mpl_toolkits.axes_grid1 import make_axes_locatable

from openpyxl import Workbook
from openpyxl.styles import PatternFill, Alignment, Font
from openpyxl.utils import get_column_letter


# --------------------- Глобальный перехватчик исключений --------------------- #
def _except_hook(exctype, value, tb):
    import traceback
    msg = "".join(traceback.format_exception(exctype, value, tb))
    try:
        QMessageBox.critical(None, "Unhandled exception",
                             "An error was caught; the application will continue running.\n\n" + msg)
    except Exception:
        print(msg, file=sys.stderr)


sys.excepthook = _except_hook

NOZZLE_EXIT_PRESSURE_MAX_MPA = 0.10856

# ----------------------- Табличные данные ----------------------- #
PARA = [
    "Liquid oxygen - Kerosene              ",
    "Liquid oxygen - Liquid hydrogen",
    "Liquid oxygen - Liquid ammonia",
    "Liquid oxygen - UDMH",
    "Nitrogen tetroxide - UDMH",
    "Nitrogen tetroxide - Aerozine 50",
    "Nitrogen tetroxide - Hydrazine",
    "Nitric acid - Kerosene",
    "Nitric acid 70% / Nitrogen oxide 30% - UDMH",
    "Nitric acid 73% / Nitrogen oxide 27% - UDMH",
    "Nitric acid 80% / Nitrogen oxide 20% - UDMH",
    "Nitric acid 73% / Nitrogen oxide 23% - Kerosene",
    "Nitric acid 80% / Nitrogen oxide 20% - Kerosene",
    "Nitric acid 73% / Nitrogen oxide 27% - Tonka 250",
    "Nitric acid 80% / Nitrogen oxide 20% - Tonka 250",
    "Nitric acid - Hydrazine",
]
PARA_DEFAULT = PARA.copy()
PARA_RU = [
    "Жидкий кислород - Керосин              ",
    "Жидкий кислород - Жидкий водород",
    "Жидкий кислород - Жидкий аммиак",
    "Жидкий кислород - НДМГ",
    "Четырехокись азота - НДМГ",
    "Четырехокись азота - Аэрозин 50",
    "Четырехокись азота - Гидразин",
    "Азотная кислота - Керосин",
    "Азотная кислота 70% / Оксид азота 30% - НДМГ",
    "Азотная кислота 73% / Оксид азота 27% - НДМГ",
    "Азотная кислота 80% / Оксид азота 20% - НДМГ",
    "Азотная кислота 73% / Оксид азота 23% - Керосин",
    "Азотная кислота 80% / Оксид азота 20% - Керосин",
    "Азотная кислота 73% / Оксид азота 27% - Тонка 250",
    "Азотная кислота 80% / Оксид азота 20% - Тонка 250",
    "Азотная кислота - Гидразин",
]
k_m_list = [None, 3.40, 4.76, 1.41, 2.14, 3.07, 2.24, 1.44, 5.37, 3.00, 3.35, 3.37, 5.34, 5.37, 2.14, 4.67, 1.45]
R_st_list = [None, 324, 520, 420, 359, 336, 357, 390, 308, 378, 340, 340, 313, 314, 312, 313, 409]
k_st_list = [None, 1.11, 1.22, 1.16, 1.11, 1.13, 1.14, 1.17, 1.13, 1.14, 1.14, 1.14, 1.13, 1.31, 1.13, 1.13, 1.25]
T_st_list = [None, 3631, 3270, 3045, 3575, 3382, 3322, 3231, 3087, 3140, 3134, 3115, 3128, 3107, 3143, 3122, 3045]
J_st_list = [None, 3034, 3286, 3057, 3156, 2950, 2990, 3033, 2730, 2482, 2840, 2831, 2742, 2733, 2745, 2737, 2737]

COEF_J_DEFAULT = 0.95


# ----------------------- Модель ----------------------- #
class Model:
    def __init__(self):
        self.idx = 1
        self.k_m = None
        self.R = None
        self.k = None
        self.T_st = None
        self.J_st_ud = None
        # входы
        self.p_k = None  # МПа
        self.P_calc = None  # Н
        self.P_h = None  # Н
        self.P_0 = None  # Н
        self.P_8 = None  # Н
        self.coefJ = COEF_J_DEFAULT
        self.z_k = None
        self.T_k = None  # К
        self.p_e = None  # МПа
        self.p_h = None  # МПа
        self.p_a = None  # МПа
        self.p_0 = 0.0981  # МПа
        self.p = 0.0981  # МПа
        self.k1 = None

        # --- геометрия ---
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

        # для контура
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

    # ====== КОНТУР СОПЛА ======
    def take_x_y(self):
        x_head0 = -(self.L_g + self.L_cy + self.L_vh)
        x_cyl0 = -(self.L_cy + self.L_vh)
        x_conv0 = -self.L_vh

        # 1. Головная часть камеры
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

        # 2. Цилиндрический участок камеры
        x_cyl = np.array([x_cyl0, x_conv0])
        y_cyl = np.array([self.R_k, self.R_k])

        # 3. Входной участок к критическому сечению
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

        # 4. Расширяющаяся часть сопла
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


# ------------------ Глобали для funM ------------------ #
a1 = a2 = alpha1 = alpha2 = None
D_k = D_kr = D_a = R_k = R_kr = R_a = R3 = None
L_g = L_cy = L_vh = L_c = L_dv = None
x = None  # массив x вдоль сопла


# ------------------ Расчёт M (с прогрессом) ------------------ #
def funM(y, m=10, progress_cb=None):
    global x, k, R_kr, L_g, L_cy
    if x is None or len(x) != len(y):
        x = np.arange(len(y), dtype=float)

    def replace_by_best(a, f, ndigits=2):
        a = np.asarray(a, dtype=float)
        groups = defaultdict(list)
        for i, val in enumerate(a):
            key = round(val, ndigits)
            groups[key].append(i)
        for _, indices in groups.items():
            if len(indices) > 1:
                vals = [a[i] for i in indices]
                fvals = [f(xx) for xx in vals]
                best_idx = indices[int(np.argmin(fvals))]
                best_val = a[best_idx]
                for j in indices:
                    a[j] = best_val
        for i in range(len(a)):
            if (not np.isfinite(a[i])) or abs(f(a[i])) > 1e-4:
                a[i] = 20
        a_round = np.round(a, 12)
        a2 = sorted(set(a_round.tolist()))
        for i in range(len(a2)):
            a[i] = a2[i]
        for i in range(len(a2), len(a)):
            a[i] = 20
        return a

    def fill_gaps(arr):
        arr = np.asarray(arr, dtype=float).copy()
        n = len(arr);
        i = 0
        while i < n:
            if arr[i] == 20:
                start = i
                while i < n and arr[i] == 20:
                    i += 1
                end = i - 1
                Lidx = start - 1
                Ridx = end + 1
                kseg = end - start + 1
                for j in range(1, kseg + 1):
                    if Lidx >= 0 and Ridx < n:
                        da = (arr[Ridx] - arr[Lidx]) / (kseg + 1)
                        arr[start + j - 1] = arr[Lidx] + da * j
                    if Lidx < 0 and Ridx < n:
                        arr[start + j - 1] = arr[end + 1]
                    if Ridx == n and Lidx >= 0:
                        arr[start + j - 1] = arr[start - 1]
            else:
                i += 1
        return arr

    def sortM(A):
        idx_start = np.argmin(np.abs(x - (L_g + L_cy)))
        idx_m1 = np.argmin(np.abs(y - R_kr))

        for i in range(0, idx_m1):
            if A[i][0] > 1.0:
                A[i][0], A[i][1] = A[i][1], A[i][0]
        for i in range(idx_m1, len(x)):
            if A[i][0] < 1.0:
                A[i][0], A[i][1] = A[i][1], A[i][0]

        Arr = [A[i][0] for i in range(len(x))]
        Arr[:idx_start] = [Arr[idx_start] for _ in Arr[:idx_start]]
        Arr = fill_gaps(Arr)
        return Arr

    A = [[1, 1] for _ in range(len(x))]
    idx_m1 = np.argmin(np.abs(y - R_kr))

    for i in range(len(x)):
        yi = y[i]
        if progress_cb and (i % 5 == 0 or i == len(x) - 1):
            progress_cb(int(100 * (i + 1) / len(x)))

        m_loc = 80 if abs(i - idx_m1) < 5 else 2.5
        f = lambda M: 1 / M * (2 / (k + 1) * (1 + (k - 1) * M ** 2 / 2)) ** (
                (k + 1) / 2 / (k - 1)) - yi ** 2 / R_kr ** 2

        res = minimize_scalar(f)
        if res.fun >= 0:
            a = [20, 20]
        else:
            starts = [s / m_loc for s in range(1, int(4 * m_loc))]
            roots = [float(fsolve(f, s0)[0]) for s0 in starts]
            a = replace_by_best(roots, f)

        A[i] = [a[0], a[1]]

    Arr = sortM(A)
    return np.asarray(Arr, dtype=float)


# ------------------ Полотно для графиков ------------------ #
class PlotWidget(QWidget):
    def __init__(self, title=""):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 8, 8, 8)

        self.fig = Figure(figsize=(6, 4), dpi=100)
        self.canvas = FigureCanvas(self.fig)
        lay.addWidget(self.canvas)

        self.ax = self.fig.add_subplot(111)
        self.title = title
        self._responsive_margins = False
        self._layout_update_pending = False

        # по умолчанию светлая тема
        self._theme_mode = "light"
        self.fg_color = "#000000"
        self.bg_color = "#ffffff"
        self._apply_ax_theme()

        self._hover_x = None
        self._hover_val = None
        self._hover_label = ""
        self.hover_text_changed = None
        self.point_clicked = None
        self.canvas.mpl_connect("motion_notify_event", self._on_hover)
        self.canvas.mpl_connect("button_press_event", self._on_click)

        self._hover_x = None
        self._hover_y = None
        self._hover_val = None
        self._hover_label = ""

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._responsive_margins and not self._layout_update_pending:
            self._layout_update_pending = True
            QTimer.singleShot(0, self._update_responsive_margins)

    def _update_responsive_margins(self):
        self._layout_update_pending = False
        if not self._responsive_margins or self.width() < 2 or self.height() < 2:
            return
        self._apply_line_margins()
        self.canvas.draw_idle()

    def _apply_line_margins(self):
        """Keep titles and axis labels inside the canvas at small window sizes."""
        canvas_width = max(1, self.canvas.width())
        canvas_height = max(1, self.canvas.height())
        compact = canvas_height < 220
        self.ax.title.set_fontsize(10 if compact else 12)
        self.ax.xaxis.label.set_fontsize(9 if compact else 10)
        self.ax.yaxis.label.set_fontsize(8 if compact else 10)
        self.ax.tick_params(labelsize=8 if compact else 10)
        legend = self.ax.get_legend()
        if legend is not None:
            for text_item in legend.get_texts():
                text_item.set_fontsize(8 if compact else 10)
        left = min(0.18, max(0.08, 75.0 / canvas_width))
        right = 1.0 - min(0.08, max(0.02, 16.0 / canvas_width))
        bottom = min(0.42, max(0.15, 58.0 / canvas_height))
        top = 1.0 - min(0.25, max(0.08, 30.0 / canvas_height))
        self.fig.subplots_adjust(
            left=left,
            right=right,
            top=top,
            bottom=bottom,
        )

    def _split_label_unit(self, clabel):
        if "," in clabel:
            label, unit = clabel.split(",", 1)
            return label.strip(), unit.strip()
        return clabel.strip(), ""

    def _nearest_data_text(self, event):
        if event.inaxes != self.ax:
            return None

        if self._hover_x is None or self._hover_y is None or self._hover_val is None:
            return None

        if event.xdata is None:
            return None

        x_arr = np.asarray(self._hover_x, dtype=float)
        y_arr = np.asarray(self._hover_y, dtype=float)
        val_arr = np.asarray(self._hover_val, dtype=float)

        idx = int(np.argmin(np.abs(x_arr - event.xdata)))

        label = self._hover_label if self._hover_label else "value"
        unit = self._hover_unit if hasattr(self, "_hover_unit") else ""
        unit_s = f" {unit}" if unit else ""

        return (
            f"x={x_arr[idx]:.3f} mm   |   "
            f"R={y_arr[idx]:.3f} mm   |   "
            f"{label}={val_arr[idx]:.6g}{unit_s}"
        )

    def _on_click(self, event):
        if event.button != 1:
            return

        text = self._nearest_data_text(event)

        if text is not None and self.point_clicked is not None:
            self.point_clicked(text)

    def _on_hover(self, event):
        text = self._nearest_data_text(event)

        if text is None:
            text = " "
            QToolTip.hideText()
        else:
            QToolTip.showText(QCursor.pos(), text.replace("   |   ", "\n"), self.canvas)

        if self.hover_text_changed is not None:
            self.hover_text_changed(text)

    # --- смена темы для графика ---
    def set_theme(self, mode: str):
        """mode: 'light' | 'dark'"""
        if mode not in ("light", "dark"):
            mode = "light"
        self._theme_mode = mode
        if mode == "dark":
            self.bg_color = "#1b1f26"
            self.fg_color = "#f4f4f4"
        else:
            self.bg_color = "#ffffff"
            self.fg_color = "#111827"
        self._apply_ax_theme()
        self.canvas.draw_idle()

    def _apply_ax_theme(self):
        """Apply the current foreground/background colors to the figure and axes."""
        self.fig.set_facecolor(self.bg_color)
        if self.ax is None:
            return
        self.ax.set_facecolor(self.bg_color)
        # границы
        for sp in self.ax.spines.values():
            sp.set_color(self.fg_color)
        # оси, подписи, заголовок
        self.ax.tick_params(colors=self.fg_color)
        self.ax.xaxis.label.set_color(self.fg_color)
        self.ax.yaxis.label.set_color(self.fg_color)
        self.ax.title.set_color(self.fg_color)
        legend = self.ax.get_legend()
        if legend is not None:
            legend.get_frame().set_facecolor(self.bg_color)
            legend.get_frame().set_edgecolor(self.fg_color)
            for text in legend.get_texts():
                text.set_color(self.fg_color)

    def clear(self):
        self.fig.clf()
        self.ax = self.fig.add_subplot(111)
        self._apply_ax_theme()

    def draw_fill(self, x_arr, y_arr, val_arr, y0=0.0, cmap="turbo", refine=2, clabel=""):
        self.clear()
        x_arr = np.asarray(x_arr);
        y_arr = np.asarray(y_arr);
        val_arr = np.asarray(val_arr)

        idx = np.argsort(x_arr)
        x, y, T = x_arr[idx], y_arr[idx], val_arr[idx]

        try:
            x0_nozzle = float(L_g + L_cy)
            mask = x >= x0_nozzle
            if np.any(mask):
                x, y, T = x[mask], y[mask], T[mask]
        except Exception:
            pass

        label, unit = self._split_label_unit(clabel if clabel else "value")

        self._hover_x = x
        self._hover_y = y
        self._hover_val = T
        self._hover_label = label
        self._hover_unit = unit

        if len(x) < 2:
            self.canvas.draw_idle()
            return

        tmin, tmax = np.nanmin(T), np.nanmax(T)
        norm = Normalize(tmin - 0.5, tmax + 0.5) if np.isclose(tmax, tmin) else Normalize(tmin, tmax)

        verts, colors = [], []
        m = max(1, int(refine))
        for i in range(len(x) - 1):
            xs = np.linspace(x[i], x[i + 1], m + 1)
            ys = np.linspace(y[i], y[i + 1], m + 1)
            Ts = np.linspace(T[i], T[i + 1], m + 1)
            for j in range(m):
                verts.append([(xs[j], y0),
                              (xs[j], ys[j]),
                              (xs[j + 1], ys[j + 1]),
                              (xs[j + 1], y0)])
                colors.append(0.5 * (Ts[j] + Ts[j + 1]))

        coll = PolyCollection(verts, array=np.asarray(colors), cmap=cmap,
                              norm=norm, antialiased=False,
                              linewidth=0, edgecolor="none")
        self.ax.add_collection(coll)

        divider = make_axes_locatable(self.ax)
        cax = divider.append_axes("right", size="3%", pad=0.05)
        cb = self.fig.colorbar(cm.ScalarMappable(norm=norm, cmap=cmap), cax=cax)

        # перекрашиваем colorbar под тему
        cb.outline.set_edgecolor(self.fg_color)
        cb.ax.tick_params(color=self.fg_color)
        for lab in cb.ax.get_yticklabels():
            lab.set_color(self.fg_color)

        # контур сопла
        self.ax.plot(x, y, color=self.fg_color, lw=0.8)
        self.ax.set_aspect("equal", adjustable="box")
        self.ax.set_title(self.title)
        self.ax.set_xlim(float(x.min()), float(x.max()) * 1.01)

        try:
            y_top = float(max(R_k, R_a))
            self.ax.set_ylim(0.0, y_top * 1.02)
        except Exception:
            pass

        self.ax.relim()
        self.ax.autoscale_view(scalex=False, scaley=False)
        self.fig.tight_layout(pad=0)
        self.fig.subplots_adjust(left=0.07, right=0.92, top=0.92, bottom=0.10)
        self.canvas.draw_idle()

    def draw_lines(self, x_arr, series, xlabel="", ylabel="", xlim=None, vlines=None):
        self.clear()
        self._responsive_margins = True
        x_arr = np.asarray(x_arr, dtype=float)
        for y_arr, label in series:
            y_arr = np.asarray(y_arr, dtype=float)
            self.ax.plot(x_arr, y_arr, lw=2.0, label=label)
        self.ax.set_title(self.title)
        self.ax.set_xlabel(xlabel)
        self.ax.set_ylabel(ylabel)
        if xlim is not None:
            self.ax.set_xlim(float(xlim[0]), float(xlim[1]))
        elif xlabel == "R/Rkr":
            ticks = [0.0, 1.0 / 3.0, 2.0 / 3.0, 1.0, 1.0 + 1.0 / 3.0, 1.0 + 2.0 / 3.0, 2.0]
            labels = ["2.5", "2.0", "1.5", "1.0", "1.5", "2.0", "2.5"]
            self.ax.set_xlim(0.0, 2.0)
            self.ax.set_xticks(ticks)
            self.ax.set_xticklabels(labels)
        if vlines is not None:
            for x_line in np.asarray(vlines, dtype=float):
                if np.isfinite(x_line):
                    self.ax.axvline(x_line, color="#9ca3af", lw=0.8, ls="--", alpha=0.45, zorder=0)
        self.ax.grid(True, alpha=0.35)
        if series:
            self.ax.legend()
        self._apply_ax_theme()
        self._apply_line_margins()
        self.canvas.draw_idle()

    # --- единая, исправленная версия draw_geometry ---
    def draw_upper_contour(
            self, x_arr, y_arr, points=None, xlabel="x [mm]", ylabel="R [mm]",
            line_label="nozzle contour", points_label="thermal points",
            xlim=None, vlines=None, show_legend=False
    ):
        self.clear()
        self._responsive_margins = True
        x_arr = np.asarray(x_arr, dtype=float)
        y_arr = np.asarray(y_arr, dtype=float)

        if x_arr.size and y_arr.size:
            self.ax.plot(x_arr, y_arr, color=self.fg_color, lw=2.0, label=line_label)
            if xlim is not None:
                self.ax.set_xlim(float(xlim[0]), float(xlim[1]))
            else:
                self.ax.set_xlim(float(np.nanmin(x_arr)), float(np.nanmax(x_arr)))
            y_min = float(np.nanmin(y_arr))
            y_max = float(np.nanmax(y_arr))
            y_pad = max((y_max - y_min) * 0.08, y_max * 0.03, 1.0)
            self.ax.set_ylim(max(0.0, y_min - y_pad), y_max + y_pad)

        if vlines is not None:
            for x_line in np.asarray(vlines, dtype=float):
                if np.isfinite(x_line):
                    self.ax.axvline(x_line, color="#9ca3af", lw=0.8, ls="--", alpha=0.45, zorder=0)

        if points is not None:
            px, py = points
            px = np.asarray(px, dtype=float)
            py = np.asarray(py, dtype=float)
            if px.size and py.size:
                self.ax.plot(px, py, "o", color="#ff4d4d", markersize=4.5, label=points_label)

        self.ax.set_title(self.title)
        self.ax.set_xlabel(xlabel)
        self.ax.set_ylabel(ylabel)
        self.ax.grid(True, alpha=0.35)
        if show_legend and (x_arr.size or points is not None):
            self.ax.legend()
        self._apply_ax_theme()
        self._apply_line_margins()
        self.canvas.draw_idle()

    def draw_geometry(self, model: Model, x, y, X, Y):
        self.clear()
        ax = self.ax

        x = np.asarray(x, dtype=float)
        y = np.asarray(y, dtype=float)

        x1, x2, x3, x4, x5 = X[0], X[1], X[2], X[3], X[4]
        y1, y2, y3, y4, y5 = Y[0], Y[1], Y[2], Y[3], Y[4]

        ax.plot(x, y, color=self.fg_color, lw=1.5)
        ax.plot(x, -y, color=self.fg_color, lw=1.5)
        ax.plot([x5, x5], [y5, -y5], color=self.fg_color, lw=1.5)

        font_size = 11;

        def text_size_data(ax, text):
            fig = ax.figure
            tmp = ax.text(0, 0, text, fontsize=font_size)
            fig.canvas.draw()
            bbox = tmp.get_window_extent(
                renderer=fig.canvas.get_renderer()
            )
            tmp.remove()
            w_px = bbox.width
            h_px = bbox.height
            x0 = ax.transData.inverted().transform((0, 0))[0]
            x1 = ax.transData.inverted().transform((w_px, 0))[0]
            y0 = ax.transData.inverted().transform((0, 0))[1]
            y1 = ax.transData.inverted().transform((0, h_px))[1]
            return abs(x1 - x0), abs(y1 - y0)

        def draw_v_dim(ax, x, y_bottom, y_top, text, loc="center"):
            dy_text = 0;
            w_text, h_text = text_size_data(ax, text)
            if (w_text >= abs(y_top - y_bottom)):
                dy_text = h_text + abs(y_top - y_bottom) / 2 + w_text / 2;
                ax.plot([x, x], [y_bottom, y_top + h_text + w_text], color=self.fg_color, lw=0.7)

            if loc == "center":    dx = 0;           dx_text = 0;
            if loc == "left":      dx = 2 * h_text;  dx_text = dx;
            if loc == "right":     dx = -2 * h_text; dx_text = dx;
            ax.annotate(
                "",
                xy=(x + dx, y_top),
                xytext=(x + dx, y_bottom),
                arrowprops=dict(arrowstyle="<->", lw=1, color=self.fg_color)
            )
            ax.plot([x, x + dx], [y_top, y_top], color=self.fg_color, lw=0.7)
            ax.plot([x, x + dx], [y_bottom, y_bottom], color=self.fg_color, lw=0.7)
            ax.text(
                x + dx_text,
                (y_top + y_bottom) / 2 + dy_text,
                text,
                rotation=90,
                va="center",
                ha="right",
                fontsize=font_size,
                color=self.fg_color
            )

        def draw_h_dim(ax, x_left, x_right, y_left, y_right, y, text):
            dx_text = 0
            w_text, h_text = text_size_data(ax, text)
            if (w_text >= abs(x_left - x_right)):
                y = y + h_text * 2.5
                dx_text = abs(x_left - x_right) / 2 + w_text / 2;
                ax.plot([(x_left + x_right) / 2, x_right + w_text], [y, y], color=self.fg_color, lw=0.7)
            ax.annotate(
                "",
                xy=(x_right, y),
                xytext=(x_left, y),
                arrowprops=dict(arrowstyle="<->", lw=1, color=self.fg_color)
            )
            ax.plot([x_left, x_left], [y_left, y], color=self.fg_color, lw=0.7)
            ax.plot([x_right, x_right], [y_right, y], color=self.fg_color, lw=0.7)
            ax.text(
                (x_left + x_right) / 2 + dx_text,
                y,
                text,
                va="bottom",
                ha="center",
                fontsize=font_size,
                color=self.fg_color
            )

        w_text, h_text = text_size_data(ax, str(round(L_g, 2)))
        y_dim1 = -max(y) - 2 * h_text
        y_dim2 = y_dim1 - 2.5 * h_text

        # Диаметры
        draw_v_dim(ax, (x2 + x3) / 2, -y2, y2, "Ø " + str(round(D_k, 2)), loc="center")
        draw_v_dim(ax, x4, -y4, y4, "Ø " + str(round(D_kr, 2)), loc="center")
        draw_v_dim(ax, x5, -y5, y5, "Ø " + str(round(D_a, 2)), loc="left")

        # Частные длины
        draw_h_dim(ax, x1, x2, y1, y2, y_dim1, round(L_g, 2))
        draw_h_dim(ax, x2, x3, y2, y3, y_dim1, round(L_cy, 2))
        draw_h_dim(ax, x3, x4, y3, y4, y_dim1, round(L_vh, 2))
        draw_h_dim(ax, x4, x5, y4, y5, y_dim1, round(L_c, 2))
        draw_h_dim(ax, x1, x5, y1, y5, y_dim2, round(L_dv, 2))

        ax.set_aspect("equal", adjustable="box")
        ax.axis("off")
        ax.set_xlim(min(x) - h_text, max(x) + h_text * 3)
        ax.set_ylim(y_dim2 - h_text, max(y) + h_text)

        self.fig.tight_layout(pad=0)
        self.fig.subplots_adjust(left=0.04, right=0.96, top=0.96, bottom=0.04)
        self.canvas.draw_idle()


# ------------------ Страница графика с кнопкой ------------------ #
class GraphPage(QWidget):
    def __init__(self, title: str, button_text: str, show_info=False):
        super().__init__()

        self.setObjectName("graphPage")

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(12, 12, 12, 12)
        self.layout.setSpacing(8)

        self.plot = PlotWidget(title)
        self.layout.addWidget(self.plot)

        self.info_box = None
        self.points_box = None
        self.hover_label = None
        self.search_value = None
        self.search_param = None
        self.btn_search_point = None
        self.language = "en"

        # =====================================================
        # Вариант для страницы геометрии: только график + кнопка
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
        # Вариант для страниц M, T, P
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
            self.points_box.append("Нет данных для поиска." if self.language == "ru" else "No data available for search.")
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
    def __init__(self):
        super().__init__()
        self.setObjectName("graphPage")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

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
        self.table.setMinimumHeight(180)
        self.table.setLineWrapMode(QTextEdit.NoWrap)
        layout.addWidget(self.table, 2)

        self.plot = PlotWidget("Specific heat flux along the combustion wall")
        self.plot.setMinimumHeight(170)
        self.plot.setMaximumHeight(320)
        self.plot.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.plot, 3)

        self.contour_plot = PlotWidget("Nozzle contour")
        self.contour_plot.setMinimumHeight(120)
        self.contour_plot.setMaximumHeight(220)
        self.contour_plot.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.contour_plot, 2)

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
            "This value is used for the thermal-load calculation.",
            "Введите предельно допустимую температуру материала огневой стенки в кельвинах. "
            "Это значение используется при расчёте тепловых нагрузок."
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
                if self.temperature_unit == "К":
                    text += (
                        f"\n\nВыбранная топливная пара: {pair_name}."
                        f"\nДоступный расчётный диапазон вводимой температуры: "
                        f"{minimum:g}–{maximum:g} К."
                    )
                else:
                    text += (
                        f"\n\nSelected propellant pair: {pair_name}."
                        f"\nAvailable calculation range for the input temperature: "
                        f"{minimum:g}–{maximum:g} K."
                    )
            else:
                text += (
                    "\n\nДиапазон температур для выбранной топливной пары недоступен."
                    if self.temperature_unit == "К" else
                    "\n\nThe temperature range for the selected propellant pair is unavailable."
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


# ------------------ Поток-воркер для расчёта M ------------------ #
class MWorker(QtCore.QObject):
    progressed = QtCore.pyqtSignal(int)
    finished = QtCore.pyqtSignal(object)
    failed = QtCore.pyqtSignal(str)

    def __init__(self, y_arr):
        super().__init__()
        self._y = np.asarray(y_arr, dtype=float)

    @QtCore.pyqtSlot()
    def run(self):
        try:
            def cb(p):
                self.progressed.emit(int(p))

            M = funM(self._y, progress_cb=cb)
            self.finished.emit(np.asarray(M, dtype=float))
        except Exception as e:
            self.failed.emit(str(e))


# -------------------------------------- UI -------------------------------------- #
class Window(QMainWindow):
    def __init__(self):
        super().__init__()

        # --- свой заголовок вместо системного ---
        self.setWindowFlag(Qt.FramelessWindowHint, True)
        self._drag_pos = None  # для перетаскивания окна

        self.setWindowTitle("LRE Nozzle Designer")
        self.model = Model()
        self._language = "en"
        self._last_report_args = None

        # ----- локаль -----
        self._locale = QLocale(QLocale.English)
        QLocale.setDefault(self._locale)

        # ----- корневой лэйаут окна -----
        root = QWidget()
        self.setCentralWidget(root)
        h = QHBoxLayout(root)
        h.setContentsMargins(4, 4, 4, 4)
        h.setSpacing(4)

        # ===== левое меню =====
        left = QFrame()
        left.setObjectName("side")
        left.setMinimumWidth(160)  # можно добавить ещё setMaximumWidth(260) при желании
        left.setFrameShape(QFrame.NoFrame)
        vleft = QVBoxLayout(left)
        vleft.setContentsMargins(14, 14, 14, 14)
        vleft.setSpacing(8)

        self.side_title = QLabel("Navigation")
        ft = self.side_title.font()
        ft.setPointSize(10)
        ft.setBold(True)
        self.side_title.setFont(ft)
        self.side_title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        vleft.addWidget(self.side_title)
        vleft.addSpacing(6)

        self.btn_page_main = QPushButton("Home");
        self.btn_page_main.setCheckable(True)
        self.btn_page_geom = QPushButton("Geometry");
        self.btn_page_geom.setCheckable(True)
        self.btn_page_M = QPushButton("Mach number");
        self.btn_page_M.setCheckable(True)
        self.btn_page_T = QPushButton("Temperature");
        self.btn_page_T.setCheckable(True)
        self.btn_page_P = QPushButton("Pressure");
        self.btn_page_P.setCheckable(True)
        self.btn_page_thermal = QPushButton("Thermal loads");
        self.btn_page_thermal.setCheckable(True)

        for b in (self.btn_page_main, self.btn_page_geom,
                  self.btn_page_M, self.btn_page_T, self.btn_page_P, self.btn_page_thermal):
            b.setMinimumHeight(34)
            b.setCursor(Qt.PointingHandCursor)
            vleft.addWidget(b)

        vleft.addStretch(1)

        # ===== центральный стек =====
        self.stack = QStackedWidget()
        self.stack.setObjectName("centralStack")

        # ====== ГЛАВНАЯ ======
        page_main = QWidget()
        self.page_main = page_main
        mainGrid = QGridLayout(page_main)
        mainGrid.setContentsMargins(8, 10, 8, 10)
        mainGrid.setHorizontalSpacing(15)
        mainGrid.setVerticalSpacing(10)

        # ---- левая колонка: прокручиваемая панель + кнопка снизу ----

        # Виджет с полями (то, что будет внутри прокрутки)
        inputsWidget = QWidget()
        inputsWidget.setObjectName("inputPanel")
        vInputs = QVBoxLayout(inputsWidget)
        vInputs.setContentsMargins(20, 20, 20, 20)
        vInputs.setSpacing(10)

        self.chk_autoTk = QCheckBox("Auto-fill")
        self.chk_autoTk.setChecked(True)
        self._auto_mode = True  # флаг режима
        self.chk_autoTk.stateChanged.connect(self.on_auto_mode_toggled)
        vInputs.addWidget(self.chk_autoTk)

        # Сетка параметров
        self.required_inputs_frame = QFrame()
        self.required_inputs_frame.setObjectName("requiredInputsFrame")
        required_inputs_layout = QVBoxLayout(self.required_inputs_frame)
        required_inputs_layout.setContentsMargins(12, 10, 12, 12)
        required_inputs_layout.setSpacing(8)

        self.lbl_required_inputs = QLabel("Required input data")
        self.lbl_required_inputs.setObjectName("requiredInputsTitle")
        required_inputs_layout.addWidget(self.lbl_required_inputs)

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(8)

        LABEL_W = 180
        FIELD_W = 176
        LEFT_TOTAL_W = LABEL_W + FIELD_W + 60  # ← считаем ЗДЕСЬ, до использования

        grid.setColumnMinimumWidth(0, LABEL_W)
        grid.setColumnStretch(0, 0)
        grid.setColumnStretch(1, 1)  # растягиваем колонку с полями
        # grid.setColumnStretch(2, 1)    # третью колонку не используем
        required_inputs_layout.addLayout(grid)
        vInputs.addWidget(self.required_inputs_frame)

        def add_row(r, text, widget):
            lbl = QLabel(text)
            lbl.setWordWrap(True)
            lbl.setMinimumHeight(34)
            lbl.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.MinimumExpanding)

            grid.addWidget(lbl, r, 0, alignment=Qt.AlignLeft | Qt.AlignVCenter)
            grid.addWidget(widget, r, 1, alignment=Qt.AlignLeft | Qt.AlignVCenter)
            return lbl

        def add_help_row(r, text, widget):
            label_row = QWidget()
            label_layout = QHBoxLayout(label_row)
            label_layout.setContentsMargins(0, 0, 0, 0)
            label_layout.setSpacing(5)

            lbl = QLabel(text)
            lbl.setWordWrap(True)
            lbl.setMinimumHeight(34)
            lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.MinimumExpanding)
            label_layout.addWidget(lbl, 1)

            btn_help = QPushButton("i")
            btn_help.setObjectName("helpButton")
            btn_help.setCursor(Qt.PointingHandCursor)
            btn_help.setFixedSize(16, 16)
            btn_help.clicked.connect(lambda _=False, b=btn_help: self._show_help_tooltip(b))
            label_layout.addWidget(btn_help, 0, Qt.AlignVCenter)

            grid.addWidget(label_row, r, 0, alignment=Qt.AlignLeft | Qt.AlignVCenter)
            grid.addWidget(widget, r, 1, alignment=Qt.AlignLeft | Qt.AlignVCenter)
            return lbl, btn_help

        row = 0

        # ===== Топливная пара =====
        self.lbl_propellant_pair = QLabel("Propellant pair:")
        grid.addWidget(self.lbl_propellant_pair, row, 0, 1, 2,
                       alignment=Qt.AlignLeft | Qt.AlignVCenter)
        # self.cbFuel = QComboBox()
        # self.cbFuel.setMinimumHeight(28)
        # for i, name in enumerate(PARA, start=1):
        #     self.cbFuel.addItem(name.strip(), i)
        # self.cbFuel.currentIndexChanged.connect(self.on_change)
        # self.cbFuel.setView(QListView())
        # self.cbFuel.setFixedWidth(LABEL_W + FIELD_W + 12)
        # grid.addWidget(self.cbFuel, row + 1, 0, 1, 2, alignment=Qt.AlignLeft)
        # row += 2
        self.cbFuel = QComboBox()
        self.cbFuel.setMinimumHeight(28)
        for i, name in enumerate(PARA, start=1):
            self.cbFuel.addItem(name.strip(), i)
        self.cbFuel.currentIndexChanged.connect(self.on_change)
        self.cbFuel.setView(QListView())

        self.btn_fuel_params = QPushButton("•••")
        self.btn_fuel_params.setFixedSize(44, 28)
        self.btn_fuel_params.setToolTip("Propellant pair parameters")
        self.btn_fuel_params.clicked.connect(self.open_fuel_params_dialog)

        fuel_row = QWidget()
        fuel_layout = QHBoxLayout(fuel_row)
        fuel_layout.setContentsMargins(0, 0, 0, 0)
        fuel_layout.setSpacing(8)

        self.cbFuel.setFixedWidth(LABEL_W + FIELD_W - 40)
        fuel_layout.addWidget(self.cbFuel)
        fuel_layout.addWidget(self.btn_fuel_params)

        grid.addWidget(fuel_row, row + 1, 0, 1, 2, alignment=Qt.AlignLeft)
        row += 2

        # ===== СТАНДАРТНЫЕ ПАРАМЕТРЫ =====
        # self.ed_k_m = QLineEdit();
        # self.ed_k_m.setFixedWidth(FIELD_W);
        # self.ed_k_m.setMinimumHeight(26)
        # add_row(row, "Весовое соотношение\nкомпонентов топлива", self.ed_k_m);
        # row += 1
        #
        # self.ed_R = QLineEdit();
        # self.ed_R.setMinimumWidth(FIELD_W);
        # self.ed_R.setMinimumHeight(26)
        # add_row(row, "Газовая постоянная", self.ed_R)
        # self.add_overlay_unit(self.ed_R, "Дж/(кг·К)");
        # row += 1
        #
        # self.ed_k = QLineEdit();
        # self.ed_k.setFixedWidth(FIELD_W);
        # self.ed_k.setMinimumHeight(26)
        # add_row(row, "Показатель адиабаты", self.ed_k);
        # row += 1
        #
        # self.ed_Tst = QLineEdit();
        # self.ed_Tst.setFixedWidth(FIELD_W);
        # self.ed_Tst.setMinimumHeight(26)
        # add_row(row, "Стандартная температура\nгорения топлива", self.ed_Tst)
        # self.add_overlay_unit(self.ed_Tst, "К");
        # row += 1
        #
        # self.ed_Jst = QLineEdit();
        # self.ed_Jst.setFixedWidth(FIELD_W);
        # self.ed_Jst.setMinimumHeight(26)
        # add_row(row, "Стандартный удельный \nимпульс тяги", self.ed_Jst)
        # self.add_overlay_unit(self.ed_Jst, "Н·с/кг");
        # row += 1

        # ===== СТАНДАРТНЫЕ ПАРАМЕТРЫ ТОПЛИВА =====
        # Поля создаются здесь, но добавляются не в основную форму, а в отдельное окно

        self.ed_k_m = QLineEdit()
        self.ed_k_m.setFixedWidth(FIELD_W)
        self.ed_k_m.setMinimumHeight(26)

        self.ed_R = QLineEdit()
        self.ed_R.setFixedWidth(FIELD_W)
        self.ed_R.setMinimumHeight(26)
        self.unit_R = self.add_overlay_unit(self.ed_R, "J/(kg K)")

        self.ed_k = QLineEdit()
        self.ed_k.setFixedWidth(FIELD_W)
        self.ed_k.setMinimumHeight(26)

        self.ed_Tst = QLineEdit()
        self.ed_Tst.setFixedWidth(FIELD_W)
        self.ed_Tst.setMinimumHeight(26)
        self.unit_Tst = self.add_overlay_unit(self.ed_Tst, "K")

        self.ed_Jst = QLineEdit()
        self.ed_Jst.setFixedWidth(FIELD_W)
        self.ed_Jst.setMinimumHeight(26)
        self.unit_Jst = self.add_overlay_unit(self.ed_Jst, "m/s")

        # ===== РУЧНЫЕ ПОЛЯ =====
        self.ed_p_k = QLineEdit();
        self.ed_p_k.setFixedWidth(FIELD_W);
        self.ed_p_k.setMinimumHeight(26)
        self.lbl_p_k = add_row(row, "Chamber pressure p_c", self.ed_p_k)
        self.unit_p_k = self.add_overlay_unit(self.ed_p_k, "MPa");
        row += 1

        self.ed_p_a = QLineEdit();
        self.ed_p_a.setFixedWidth(FIELD_W);
        self.ed_p_a.setMinimumHeight(26)
        self.lbl_p_a = add_row(row, "Nozzle exit pressure p_e", self.ed_p_a)
        self.unit_p_a = self.add_overlay_unit(self.ed_p_a, "MPa");
        row += 1

        self.cb_calc_mode = QComboBox()
        self.cb_calc_mode.setFixedWidth(FIELD_W)
        self.cb_calc_mode.setMinimumHeight(26)
        self.cb_calc_mode.addItems(["Sea level", "Vacuum"])
        self.cb_calc_mode.setView(QListView())
        self.cb_calc_mode.currentIndexChanged.connect(self._on_calc_mode_changed)
        self.lbl_calc_mode = add_row(row, "Engine design mode", self.cb_calc_mode)
        row += 1

        self.ed_p_h = QLineEdit()
        self.ed_p_h.setFixedWidth(FIELD_W)
        self.ed_p_h.setMinimumHeight(26)
        self.lbl_p_h = add_row(row, "Ambient pressure p_amb", self.ed_p_h)
        self.unit_p_h = self.add_overlay_unit(self.ed_p_h, "MPa")
        row += 1

        self.ed_P_h = QLineEdit()
        self.ed_P_h.setFixedWidth(FIELD_W)
        self.ed_P_h.setMinimumHeight(26)
        self.lbl_P_h = add_row(row, "Design thrust P_design", self.ed_P_h)
        self.unit_P_h = self.add_overlay_unit(self.ed_P_h, "N")
        for w in (self.ed_p_h, self.lbl_p_h, self.unit_p_h, self.ed_P_h, self.lbl_P_h, self.unit_P_h):
            w.hide()
        row += 1

        self.ed_P_0 = QLineEdit();
        self.ed_P_0.setFixedWidth(FIELD_W);
        self.ed_P_0.setMinimumHeight(26)
        self.lbl_P_0, self.btn_help_P_0 = add_help_row(row, "Sea-level thrust P_SL", self.ed_P_0)
        self.unit_P_0 = self.add_overlay_unit(self.ed_P_0, "N")
        row += 1

        self.ed_P_8 = QLineEdit();
        self.ed_P_8.setFixedWidth(FIELD_W);
        self.ed_P_8.setMinimumHeight(26)
        self.lbl_P_8, self.btn_help_P_8 = add_help_row(row, "Vacuum thrust P_inf", self.ed_P_8)
        self.unit_P_8 = self.add_overlay_unit(self.ed_P_8, "N")
        row += 1

        advanced_grid = QGridLayout()
        advanced_grid.setHorizontalSpacing(12)
        advanced_grid.setVerticalSpacing(8)
        advanced_grid.setColumnMinimumWidth(0, LABEL_W)
        advanced_grid.setColumnStretch(0, 0)
        advanced_grid.setColumnStretch(1, 1)
        vInputs.addLayout(advanced_grid)
        grid = advanced_grid
        row = 0

        self.ed_z_k = QLineEdit();
        self.ed_z_k.setText("1")
        self.ed_z_k.hide()
        self.lbl_z_k = QLabel("Number of combustion chambers N_c")
        self.lbl_z_k.hide()

        # ===== АВТО-ПОЛЯ =====
        self.ed_T_k = QLineEdit();
        self.ed_T_k.setFixedWidth(FIELD_W);
        self.ed_T_k.setMinimumHeight(26)
        self.lbl_T_k = add_row(row, "Chamber temperature T_c", self.ed_T_k)
        self.unit_T_k = self.add_overlay_unit(self.ed_T_k, "K");
        row += 1

        self.ed_Jpr = QLineEdit();
        self.ed_Jpr.setFixedWidth(FIELD_W);
        self.ed_Jpr.setMinimumHeight(26)
        self.lbl_Jpr = add_row(row, "Reduced reference specific impulse J_red", self.ed_Jpr)
        self.unit_Jpr = self.add_overlay_unit(self.ed_Jpr, "m/s");
        row += 1

        self.ed_Jr = QLineEdit();
        self.ed_Jr.setFixedWidth(FIELD_W);
        self.ed_Jr.setMinimumHeight(26)
        self.lbl_Jr = add_row(row, "Design specific impulse J_design", self.ed_Jr)
        self.unit_Jr = self.add_overlay_unit(self.ed_Jr, "m/s");
        row += 1

        self.ed_J0 = QLineEdit();
        self.ed_J0.setFixedWidth(FIELD_W);
        self.ed_J0.setMinimumHeight(26)
        self.lbl_J0 = add_row(row, "Sea-level specific impulse J_SL", self.ed_J0)
        self.unit_J0 = self.add_overlay_unit(self.ed_J0, "m/s");
        row += 1

        vInputs.addStretch(1)

        # --- кнопка расчёта ПОД панелью с прокруткой ---
        self.btn_calc_params = QPushButton("Calculate engine and nozzle")
        self.btn_calc_params.clicked.connect(self.on_calc_params)
        self.btn_calc_params.setMinimumHeight(32)
        self.btn_calc_params.setMinimumWidth(FIELD_W)

        # --- область прокрутки только для inputsWidget ---
        scroll_inputs = QScrollArea()
        scroll_inputs.setWidgetResizable(True)
        scroll_inputs.setFrameShape(QFrame.NoFrame)
        scroll_inputs.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_inputs.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        scroll_inputs.setWidget(inputsWidget)
        scroll_inputs.setMinimumWidth(420)  # как у тебя было; можно поменять
        scroll_inputs.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

        # --- левая колонка: сверху скролл, снизу кнопка ---
        leftColumn = QWidget()
        leftColumn.setMinimumWidth(LEFT_TOTAL_W)  # ← фиксируем ширину всей левой части
        vLeftColumn = QVBoxLayout(leftColumn)
        vLeftColumn.setContentsMargins(0, 0, 0, 0)
        vLeftColumn.setSpacing(8)
        vLeftColumn.addWidget(scroll_inputs)
        vLeftColumn.addSpacing(12)
        vLeftColumn.addWidget(self.btn_calc_params, 0, Qt.AlignRight)

        # ===== трекинг override и сигналы =====
        self._auto_fields = {
            "T_k": self.ed_T_k,  # "p_a": self.ed_p_a,
            "J_pr_ud_st": self.ed_Jpr, "J_r_ud": self.ed_Jr, "J_0_ud": self.ed_J0
        }
        self._std_fields = {
            "k_m": self.ed_k_m, "R": self.ed_R, "k": self.ed_k,
            "T_st": self.ed_Tst, "J_st_ud": self.ed_Jst
        }
        self._user_fields = {
            "p_k": self.ed_p_k,
            "P_0": self.ed_P_0,
            "P_8": self.ed_P_8
        }
        self._overridden = set()
        self._calc_mode = "sea_level"
        self._thrust_source = "P_0"
        self.min_pa = None

        for key, ed in self._auto_fields.items():
            ed.textEdited.connect(lambda _=None, k=key: self._overridden.add(k))
            ed.editingFinished.connect(lambda _=None: self.timer.start())

        for ed in list(self._std_fields.values()) + list(self._user_fields.values()):
            ed.textEdited.connect(lambda *_: self.timer.start())

        # спец. логика для p_k
        self.ed_P_0.textEdited.connect(lambda *_: self._on_thrust_edited("P_0"))
        self.ed_P_8.textEdited.connect(lambda *_: self._on_thrust_edited("P_8"))
        self.ed_p_k.textEdited.connect(self._on_p_k_manual_change)

        # ---- правая колонка: отчёт ----
        self.txtParams = QTextEdit()
        self.txtParams.setObjectName("reportBox")
        self.txtParams.setReadOnly(True)
        self.txtParams.setLineWrapMode(QTextEdit.NoWrap)
        self.txtParams.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.txtParams.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        mono = QFont("Consolas") if QFont("Consolas").family() else QFont("Courier New")
        mono.setPointSize(12)
        self.txtParams.setFont(mono)
        self.txtParams.setMinimumWidth(420)

        self.lbl_nozzle_status = QLabel()
        self.lbl_nozzle_status.setObjectName("nozzleStatus")
        self.lbl_nozzle_status.setWordWrap(True)
        self.lbl_nozzle_status.setMinimumHeight(46)
        self.lbl_nozzle_status.setText(self._tr(
            "Nozzle status will appear after calculation.",
            "\u0421\u0442\u0430\u0442\u0443\u0441 \u0441\u043e\u043f\u043b\u0430 \u043f\u043e\u044f\u0432\u0438\u0442\u0441\u044f \u043f\u043e\u0441\u043b\u0435 \u0440\u0430\u0441\u0447\u0435\u0442\u0430."
        ))
        self.lbl_nozzle_status.setStyleSheet(
            "QLabel#nozzleStatus { border:1px solid rgba(127,127,127,0.25); "
            "border-radius:10px; padding:8px 10px; background:rgba(127,127,127,0.08); }"
        )

        rightColumn = QWidget()
        vRightColumn = QVBoxLayout(rightColumn)
        vRightColumn.setContentsMargins(0, 0, 0, 0)
        vRightColumn.setSpacing(8)
        vRightColumn.addWidget(self.lbl_nozzle_status, 0)
        vRightColumn.addWidget(self.txtParams, 1)

        # ---- разместим две колонки в одной главной сетке ----
        mainGrid.addWidget(leftColumn, 0, 0, 1, 1)
        mainGrid.addWidget(rightColumn, 0, 1, 1, 1)
        mainGrid.setColumnStretch(0, 0)
        mainGrid.setColumnStretch(1, 1)

        # ===== страницы графиков =====
        self.page_geom = GraphPage("Nozzle geometry", "Draw the nozzle", show_info=False)

        self.page_M = GraphPage("Mach number along the nozzle M(x)", "Calculate Mach number", show_info=True)
        self.page_T = GraphPage("Static temperature along the nozzle T(x) [K]", "Calculate temperature", show_info=True)
        self.page_P = GraphPage("Static pressure along the nozzle p(x) [MPa]", "Calculate pressure", show_info=True)
        self.page_thermal = ThermalPage()
        self.page_thermal.temperature_range_provider = self._thermal_temperature_input_range

        self.page_geom.btn_calc.clicked.connect(self.on_draw_geom)
        self.page_M.btn_calc.clicked.connect(self.on_calc_M)
        self.page_T.btn_calc.clicked.connect(self.on_calc_T)
        self.page_P.btn_calc.clicked.connect(self.on_calc_P)
        self.page_thermal.btn_calc.clicked.connect(self.on_calc_thermal)

        self.page_M.btn_calc.setEnabled(False)
        self.page_T.btn_calc.setEnabled(False)
        self.page_P.btn_calc.setEnabled(False)

        self.stack.addWidget(page_main)
        self.stack.addWidget(self.page_geom)
        self.stack.addWidget(self.page_M)
        self.stack.addWidget(self.page_T)
        self.stack.addWidget(self.page_P)
        self.stack.addWidget(self.page_thermal)

        h.addWidget(left)

        # Обёртка для центральной части
        center_wrap = QWidget()
        center_wrap.setObjectName("centerPanel")
        center_layout = QVBoxLayout(center_wrap)
        center_layout.setContentsMargins(3, 3, 3, 3)
        center_layout.setSpacing(0)
        center_layout.addWidget(self.stack)
        h.addWidget(center_wrap, 1)

        # ===== стиль, статусбар, таймер =====
        self.setStyleSheet("""
            #side { background:#2b66a4; color:#fff; border-radius:16px; }
        """)
        self.statusbar = QStatusBar(self)
        self.setStatusBar(self.statusbar)
        self.progressBar = QProgressBar(self)
        self.progressBar.setRange(0, 100)
        self.progressBar.setValue(0)
        self.progressBar.setVisible(False)
        self.progressBar.setTextVisible(True)
        self.progressBar.setFixedHeight(14)
        self.statusbar.addPermanentWidget(self.progressBar, 1)

        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(200)
        self.timer.timeout.connect(self.recompute)

        # ===== данные =====
        self.x_curve = None
        self.y_curve = None
        self.M = None
        self.T = None
        self.P = None

        # ===== инициализация/сигналы =====
        self.cbFuel.setCurrentIndex(0)
        self.model.set_fuel(self.cbFuel.itemData(0))
        self.on_change()

        for ed in (self.ed_p_k,):
            ed.textEdited.connect(lambda *_: self.timer.start())
        self.ed_T_k.textEdited.connect(lambda *_: self._overridden.add("T_k"))
        self.ed_T_k.editingFinished.connect(lambda *_: self.timer.start())
        self.ed_p_a.textChanged.connect(lambda: self.timer.start())
        self.ed_p_a.editingFinished.connect(lambda: self._enforce_p_e_bounds(show_warning=True))

        # фильтр ввода для числовых
        self._all_numeric_edits = [
            self.ed_k_m, self.ed_R, self.ed_k, self.ed_Tst, self.ed_Jst,
            self.ed_p_k, self.ed_P_0, self.ed_P_8,
            self.ed_T_k, self.ed_p_a, self.ed_Jpr, self.ed_Jr, self.ed_J0
        ]
        for ed in self._all_numeric_edits:
            ed.installEventFilter(self)

        # навигация
        self.btn_page_main.clicked.connect(lambda: self._goto(0, self.btn_page_main))
        self.btn_page_geom.clicked.connect(lambda: self._goto(1, self.btn_page_geom))
        self.btn_page_M.clicked.connect(lambda: self._goto(2, self.btn_page_M))
        self.btn_page_T.clicked.connect(lambda: self._goto(3, self.btn_page_T))
        self.btn_page_P.clicked.connect(lambda: self._goto(4, self.btn_page_P))
        self.btn_page_thermal.clicked.connect(lambda: self._goto(5, self.btn_page_thermal))
        self._goto(0, self.btn_page_main)

        # ===== Минимальные размеры =====
        RIGHT_MIN_W = 430
        MENU_W = 150
        self.setMinimumWidth(MENU_W + LEFT_TOTAL_W + RIGHT_MIN_W + 80)
        self.setMinimumHeight(600)

        # ===== Тулбар + Тема/Settings =====
        self._build_toolbar()
        self._load_settings_and_theme()
        self._update_max_button_icon()
        self._apply_language()
        self._on_calc_mode_changed()

        # восстановление геометрии окна
        try:
            sz = self._settings.value("window/size")
            pos = self._settings.value("window/pos")
            if sz:
                self.resize(sz)
            if pos:
                self.move(pos)
        except Exception:
            pass

    def _tr(self, english, russian):
        return russian if self._language == "ru" else english

    def _fuel_name(self, idx):
        if self._language == "ru" and idx < len(PARA_RU) and PARA[idx] == PARA_DEFAULT[idx]:
            return PARA_RU[idx].strip()
        return PARA[idx].strip()

    def _refresh_fuel_names(self):
        current_idx = self.cbFuel.currentIndex()
        with QtCore.QSignalBlocker(self.cbFuel):
            for i in range(self.cbFuel.count()):
                if i < len(PARA):
                    self.cbFuel.setItemText(i, self._fuel_name(i))
            self.cbFuel.setCurrentIndex(current_idx)

        if hasattr(self, "list_fuels") and self.list_fuels is not None:
            for row in range(self.list_fuels.count()):
                fuel_idx = row + 1
                if fuel_idx < len(PARA):
                    self.list_fuels.item(row).setText(self._fuel_name(fuel_idx))

    def _toggle_language(self):
        self._language = "ru" if self._language == "en" else "en"
        self._locale = QLocale(QLocale.Russian if self._language == "ru" else QLocale.English)
        QLocale.setDefault(self._locale)
        self._apply_language()

    def _show_help_tooltip(self, button):
        pos = button.mapToGlobal(QtCore.QPoint(button.width() + 4, button.height() // 2))
        QToolTip.showText(pos, button.toolTip(), button)

    def _apply_language(self):
        tr = self._tr
        self.btn_language.setText("eng" if self._language == "ru" else "рус")
        self.btn_language.setToolTip(tr("Switch language", "Сменить язык"))
        self.side_title.setText(tr("Navigation", "Навигация"))
        self.btn_page_main.setText(tr("Home", "Главная"))
        self.btn_page_geom.setText(tr("Geometry", "Геометрия"))
        self.btn_page_M.setText(tr("Mach number", "Число Маха"))
        self.btn_page_T.setText(tr("Temperature along nozzle", "Температура вдоль сопла"))
        self.btn_page_P.setText(tr("Pressure along nozzle", "Давление вдоль сопла"))
        self.btn_page_thermal.setText(tr("Thermal loads", "Тепловые нагрузки"))
        self.chk_autoTk.setText(tr("Auto-fill", "Автозаполнение"))
        self.lbl_propellant_pair.setText(tr("Propellant pair:", "Топливная пара:"))
        self.btn_fuel_params.setToolTip(tr("Propellant pair parameters", "Параметры топливной пары"))
        self.lbl_p_k.setText(tr("Chamber pressure p_c", "Давление в камере сгорания p_c"))
        self.lbl_calc_mode.setText(tr("Engine design mode", "Расчетный режим двигателя"))
        self.lbl_required_inputs.setText(tr("Required input data", "Обязательные исходные данные"))
        mode_idx = self.cb_calc_mode.currentIndex()
        with QtCore.QSignalBlocker(self.cb_calc_mode):
            self.cb_calc_mode.clear()
            self.cb_calc_mode.addItems([
                tr("Sea level", "Уровень Земли"),
                tr("Vacuum", "Вакуум"),
            ])
            self.cb_calc_mode.setCurrentIndex(min(max(0, mode_idx), 1))
        self.lbl_p_h.setText(tr("Ambient pressure p_amb", "Давление окружающей среды p_amb"))
        self.lbl_P_h.setText(tr("Design thrust P_design", "Тяга на расчётном режиме P_design"))
        self.lbl_P_0.setText(tr("Sea-level thrust P_SL", "Тяга на уровне моря P_SL"))
        self.lbl_P_8.setText(tr("Vacuum thrust P_inf", "Тяга в вакууме P_inf"))
        self.btn_help_P_0.setToolTip(
            "<div style='width:380px;'>"
            + tr(
                "Sea-level thrust is the thrust of an engine operating near the Earth’s surface, "
                "where the ambient atmospheric pressure is at its maximum. It is used for first-stage "
                "engines or for calculations under ground-level conditions. It is usually lower than "
                "vacuum thrust because the atmosphere exerts back pressure on the exhaust jet from the nozzle.",
                "Тяга на земле - тяга двигателя при работе у поверхности Земли, где внешнее атмосферное "
                "давление максимально. Используется для двигателей первой ступени или для расчетов в "
                "наземных условиях. Обычно меньше тяги в пустоте, так как атмосфера оказывает обратное "
                "давление на выходную струю из сопла."
            )
            + "</div>"
        )
        self.btn_help_P_8.setToolTip(
            "<div style='width:380px;'>"
            + tr(
                "Vacuum thrust is the thrust of an engine operating under near-vacuum conditions, where "
                "the ambient pressure is almost absent. It is used for upper stages, orbital transfer "
                "stages, and space conditions. It is usually higher than sea-level thrust because the "
                "ambient pressure has almost no reducing effect on the engine thrust.",
                "Тяга в пустоте - тяга двигателя при работе в условиях, близких к вакууму, где внешнее "
                "давление практически отсутствует. Используется для верхних ступеней, разгонных блоков "
                "и космических условий. Обычно больше тяги на земле, так как внешнее давление почти не "
                "уменьшает тягу двигателя."
            )
            + "</div>"
        )
        self.lbl_z_k.setText(tr("Number of combustion chambers N_c", "Число камер сгорания N_c"))
        self.lbl_T_k.setText(tr("Chamber temperature T_c", "Температура продуктов в камере T_c"))
        self.lbl_p_a.setText(tr("Nozzle exit pressure p_e", "Давление на срезе сопла p_e"))
        self.lbl_Jpr.setText(tr("Reduced reference specific impulse J_red", "Приведённый опорный удельный импульс J_red"))
        self.lbl_Jr.setText(tr("Design specific impulse J_design", "Удельный импульс на расчётном режиме J_design"))
        self.lbl_J0.setText(tr("Sea-level specific impulse J_SL", "Удельный импульс на уровне моря J_SL"))
        self.unit_R.setText(tr("J/(kg K)", "Дж/(кг К)"))
        self.unit_Tst.setText(tr("K", "К"))
        self.unit_Jst.setText(tr("m/s", "м/с"))
        self.unit_p_k.setText(tr("MPa", "МПа"))
        self.unit_p_h.setText(tr("MPa", "МПа"))
        self.unit_P_h.setText(tr("N", "Н"))
        self.unit_P_0.setText(tr("N", "Н"))
        self.unit_P_8.setText(tr("N", "Н"))
        self.unit_T_k.setText(tr("K", "К"))
        self.unit_p_a.setText(tr("MPa", "МПа"))
        self.unit_Jpr.setText(tr("m/s", "м/с"))
        self.unit_Jr.setText(tr("m/s", "м/с"))
        self.unit_J0.setText(tr("m/s", "м/с"))
        for ed in (self.ed_R, self.ed_Tst, self.ed_Jst, self.ed_p_k,
                   self.ed_P_0, self.ed_P_8,
                   self.ed_T_k, self.ed_p_a, self.ed_Jpr, self.ed_Jr, self.ed_J0):
            ed._reposition_unit()
        self.btn_calc_params.setText(tr("Calculate engine and nozzle", "Рассчитать двигатель и сопло"))

        self.page_geom.plot.title = tr("Nozzle geometry", "Геометрия сопла")
        self.page_geom.btn_calc.setText(tr("Show drawing", "Вывести чертеж"))
        self.page_M.plot.title = tr("Mach number distribution M", "Распределение числа Маха M")
        self.page_M.btn_calc.setText(tr("Calculate M", "Рассчитать M"))
        self.page_T.plot.title = tr("Temperature distribution T [K]", "Распределение температуры T [К]")
        self.page_T.btn_calc.setText(tr("Calculate T", "Рассчитать T"))
        self.page_P.plot.title = tr("Pressure distribution P [MPa]", "Распределение давления P [МПа]")
        self.page_P.btn_calc.setText(tr("Calculate P", "Рассчитать P"))
        self.page_geom.btn_calc.setText(tr("Build nozzle drawing", "Построить чертёж сопла"))
        self.page_M.plot.title = tr("Mach number along the nozzle M(x)", "Число Маха вдоль сопла M(x)")
        self.page_M.btn_calc.setText(tr("Calculate Mach number", "Рассчитать число Маха"))
        self.page_T.plot.title = tr("Static temperature along the nozzle T(x) [K]", "Статическая температура вдоль сопла T(x) [К]")
        self.page_T.btn_calc.setText(tr("Calculate temperature", "Рассчитать температуру"))
        self.page_P.plot.title = tr("Static pressure along the nozzle p(x) [MPa]", "Статическое давление вдоль сопла p(x) [МПа]")
        self.page_P.btn_calc.setText(tr("Calculate pressure", "Рассчитать давление"))
        self.page_geom.btn_calc.setText(self._tr("Draw the nozzle", self.page_geom.btn_calc.text()))
        self.page_thermal.set_language(tr)
        for page in (self.page_M, self.page_T, self.page_P):
            page.language = self._language
            page.hover_label.setText(tr("x = -    |    R = -    |    value = -", "x = -    |    R = -    |    значение = -"))
            page.search_value.setPlaceholderText(tr("value", "значение"))
            page.btn_search_point.setToolTip(tr("Find the nearest point", "Найти ближайшую точку"))

        self.act_calc.setText(tr("Calculate engine and nozzle (Ctrl+R)", "Рассчитать двигатель и сопло (Ctrl+R)"))
        self.act_calc.setStatusTip(tr("Calculate geometry and update the report", "Рассчитать геометрию и обновить отчет"))
        self.act_geom.setText(tr("Drawing (Ctrl+D)", "Чертеж (Ctrl+D)"))
        self.act_geom.setStatusTip(tr("Show the nozzle drawing", "Показать чертеж сопла"))
        self.btn_tb_open.setToolTip(tr("Auto-fill... (Ctrl+L)", "Автозаполнение... (Ctrl+L)"))
        self.btn_tb_save.setToolTip(tr("Save... (Ctrl+S)", "Сохранить... (Ctrl+S)"))
        self.btn_themeToggle.setToolTip(tr("Toggle light/dark theme", "Переключить светлую/темную тему"))
        self._update_max_button_icon()
        self._refresh_fuel_names()
        self._update_nozzle_status()

        if self._last_report_args is not None:
            self._fill_params_text(*self._last_report_args)
        if hasattr(self, "_settings") and self.x_curve is not None:
            self._set_plot_theme(self._settings.value("ui/theme", "light"))
            if self.M is not None:
                self.page_M.set_info(self._make_plot_info(self.M, "M", ""))
            if self.T is not None:
                self.page_T.set_info(self._make_plot_info(self.T, "T", "K"))
            if self.P is not None:
                self.page_P.set_info(self._make_plot_info(self.P, "p", "MPa"))
        if hasattr(self, "_fuel_params_dialog") and self._fuel_params_dialog.isVisible():
            self._fuel_params_dialog.setWindowTitle(tr("Propellant Pair Parameters", "Параметры топливной пары"))
            for lbl, en_text, ru_text in self._fuel_dialog_labels:
                lbl.setText(tr(en_text, ru_text))
            self.btn_save_fuel_params.setText(tr("Save", "Сохранить"))
            self.btn_close_fuel_params.setText(tr("Close", "Закрыть"))

    def _section_value(self, arr, x_target):
        arr = np.asarray(arr, dtype=float)
        x_arr = np.asarray(self.x_curve, dtype=float)

        idx = int(np.argmin(np.abs(x_arr - x_target)))
        return x_arr[idx], arr[idx]

    def _make_plot_info(self, arr, label, unit):
        m = self.model

        x_in = m.L_g + m.L_cy
        x_crit = m.L_g + m.L_cy + m.L_vh
        x_out = m.L_g + m.L_cy + m.L_vh + m.L_c

        xin, vin = self._section_value(arr, x_in)
        xcr, vcr = self._section_value(arr, x_crit)
        xou, vou = self._section_value(arr, x_out)

        unit = {"K": self._tr("K", "К"), "MPa": self._tr("MPa", "МПа")}.get(unit, unit)
        return (
            f"{self._tr('Inlet', 'Вход')}:              \tx = {xin:.2f} {self._tr('mm', 'мм')},  "
            f"Rc = {m.R_k:.2f} {self._tr('mm', 'мм')},  {label} = {vin:.6g} {unit}\n"
            f"{self._tr('Throat', 'Критическое сечение')}:     \tx = {xcr:.2f} {self._tr('mm', 'мм')},  "
            f"Rt = {m.R_kr:.2f} {self._tr('mm', 'мм')},  {label} = {vcr:.6g} {unit}\n"
            f"{self._tr('Exit', 'Выход')}:               \tx = {xou:.2f} {self._tr('mm', 'мм')},  "
            f"Re = {m.R_a:.2f} {self._tr('mm', 'мм')},  {label} = {vou:.6g} {unit}\n\n"
            f"{self._tr('Specific heat ratio', 'Показатель адиабаты')} \tγ = {m.k:.4g},\n"
            # f"Сводка:\n"
            # f"Радиус критики\tRкр\t{m.R_kr:.2f} мм,\n"
            # f"Dкр = {m.D_kr:.2f} мм,\n"
            # f"Da = {m.D_a:.2f} мм,\n"
            # f"f_a = {m.fa:.3f},\n"
            # f"pк = {m.p_k:.4g} МПа,\n"
            # f"pа = {m.p_a:.6g} МПа"
        )

    def open_fuel_params_dialog(self):
        dlg = QDialog(self)
        dlg.setWindowTitle(self._tr("Propellant Pair Parameters", "Параметры топливной пары"))
        dlg.setModal(False)

        main = QHBoxLayout(dlg)
        main.setContentsMargins(8, 8, 12, 12)
        main.setSpacing(22)

        # ===== ЛЕВАЯ ЧАСТЬ: список топливных пар =====
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(6)

        top_left = QHBoxLayout()
        top_left.setSpacing(6)

        self.ed_selected_fuel_name = QLineEdit()
        self.ed_selected_fuel_name.setReadOnly(True)
        self.ed_selected_fuel_name.setMinimumHeight(26)

        # self.btn_edit_fuel = QPushButton("✎")
        self.btn_edit_fuel = QPushButton()
        self.btn_edit_fuel.setFixedSize(26, 26)

        self.icon_edit_normal = QIcon("editing-pencil 0.png")
        self.icon_edit_hover = QIcon("editing-pencil.png")
        import os

        print("Launch directory:", os.getcwd())
        print("normal exists:", os.path.exists("editing-pencil 0.png"))
        print("hover exists:", os.path.exists("editing-pencil.png"))
        print("normal isNull:", self.icon_edit_normal.isNull())
        print("hover isNull:", self.icon_edit_hover.isNull())

        self.btn_edit_fuel.setIcon(self.icon_edit_normal)
        self.btn_edit_fuel.setIconSize(QSize(17, 17))

        self.btn_edit_fuel.setStyleSheet("""
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

        self.btn_edit_fuel.installEventFilter(self)

        self.btn_delete_fuel = QPushButton()
        self.btn_delete_fuel.setFixedSize(26, 26)

        self.icon_delete_normal = QIcon("delete 0.png")
        self.icon_delete_hover = QIcon("delete.png")

        self.btn_delete_fuel.setIcon(self.icon_delete_normal)
        self.btn_delete_fuel.setIconSize(QSize(17, 17))

        self.btn_delete_fuel.setStyleSheet("""
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

        self.btn_delete_fuel.installEventFilter(self)

        top_left.addWidget(self.ed_selected_fuel_name)
        top_left.addWidget(self.btn_edit_fuel)
        top_left.addWidget(self.btn_delete_fuel)

        self.list_fuels = QListWidget()
        self.list_fuels.setMinimumWidth(400)
        self.list_fuels.setMinimumHeight(270)

        for fuel_idx in range(1, len(PARA)):
            self.list_fuels.addItem(self._fuel_name(fuel_idx))

        left_layout.addLayout(top_left)
        left_layout.addWidget(self.list_fuels)

        main.addWidget(left)

        # ===== ПРАВАЯ ЧАСТЬ: параметры выбранной пары =====
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)

        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(10)

        self.ed_fuel_name = QLineEdit()
        self.ed_fuel_name.setMinimumHeight(28)
        self.ed_fuel_name.setFixedWidth(315)

        self._fuel_dialog_labels = []

        def add_dialog_row(r, english, russian, widget):
            lbl = QLabel(self._tr(english, russian))
            lbl.setWordWrap(True)
            lbl.setMinimumHeight(34)
            grid.addWidget(lbl, r, 0, alignment=Qt.AlignLeft | Qt.AlignVCenter)
            grid.addWidget(widget, r, 1, alignment=Qt.AlignLeft | Qt.AlignVCenter)
            self._fuel_dialog_labels.append((lbl, english, russian))

        row = 0
        add_dialog_row(row, "Propellant pair name", "Название топливной пары", self.ed_fuel_name)
        row += 1

        add_dialog_row(row, "Propellant mass ratio K_m", "Массовое соотношение компонентов K_m", self.ed_k_m)
        row += 1

        add_dialog_row(row, "Specific gas constant R_g", "Удельная газовая постоянная R_g", self.ed_R)
        row += 1

        add_dialog_row(row, "Specific heat ratio gamma", "Показатель адиабаты γ", self.ed_k)
        row += 1

        add_dialog_row(row, "Reference combustion temperature T_ref", "Опорная температура горения T_ref", self.ed_Tst)
        row += 1

        add_dialog_row(row, "Reference specific impulse J_ref", "Опорный удельный импульс J_ref", self.ed_Jst)
        row += 1

        right_layout.addLayout(grid)

        buttons = QHBoxLayout()
        buttons.addStretch(1)

        self.btn_save_fuel_params = QPushButton(self._tr("Save", "Сохранить"))
        self.btn_save_fuel_params.setMinimumWidth(90)

        self.btn_close_fuel_params = QPushButton(self._tr("Close", "Закрыть"))
        self.btn_close_fuel_params.setMinimumWidth(90)
        self.btn_close_fuel_params.clicked.connect(dlg.close)

        buttons.addWidget(self.btn_save_fuel_params)
        buttons.addWidget(self.btn_close_fuel_params)

        right_layout.addLayout(buttons)

        main.addWidget(right)

        # ===== ЛОГИКА =====
        def load_fuel_from_list(row_idx):
            if row_idx < 0:
                return

            fuel_idx = row_idx + 1

            self.ed_selected_fuel_name.setText(self._fuel_name(fuel_idx))
            self.ed_fuel_name.setText(self._fuel_name(fuel_idx))

            self.ed_k_m.setText("" if k_m_list[fuel_idx] is None else f"{k_m_list[fuel_idx]:.6g}")
            self.ed_R.setText("" if R_st_list[fuel_idx] is None else f"{R_st_list[fuel_idx]:.6g}")
            self.ed_k.setText("" if k_st_list[fuel_idx] is None else f"{k_st_list[fuel_idx]:.6g}")
            self.ed_Tst.setText("" if T_st_list[fuel_idx] is None else f"{T_st_list[fuel_idx]:.6g}")
            self.ed_Jst.setText("" if J_st_list[fuel_idx] is None else f"{J_st_list[fuel_idx]:.6g}")

        def save_current_fuel():
            row_idx = self.list_fuels.currentRow()
            if row_idx < 0:
                return

            fuel_idx = row_idx + 1
            name = self.ed_fuel_name.text().strip()

            if not name:
                QMessageBox.warning(self, self._tr("Error", "Ошибка"),
                                    self._tr("Enter a propellant pair name.", "Введите название топливной пары."))
                return

            try:
                km = float(self.ed_k_m.text().replace(",", "."))
                R = float(self.ed_R.text().replace(",", "."))
                k = float(self.ed_k.text().replace(",", "."))
                Tst = float(self.ed_Tst.text().replace(",", "."))
                Jst = float(self.ed_Jst.text().replace(",", "."))
            except Exception:
                QMessageBox.warning(self, self._tr("Error", "Ошибка"),
                                    self._tr("Check the numeric propellant parameters.",
                                             "Проверьте числовые параметры топлива."))
                return

            PARA[fuel_idx] = name
            PARA_DEFAULT[fuel_idx] = name
            PARA_RU[fuel_idx] = name
            k_m_list[fuel_idx] = km
            R_st_list[fuel_idx] = R
            k_st_list[fuel_idx] = k
            T_st_list[fuel_idx] = Tst
            J_st_list[fuel_idx] = Jst

            self.list_fuels.item(row_idx).setText(name)
            self.ed_selected_fuel_name.setText(name)

            self.cbFuel.setItemText(row_idx, name)
            self.cbFuel.setCurrentIndex(row_idx)

            self.on_change()
            self.timer.start()

        def edit_fuel_name():
            self.ed_fuel_name.setFocus()
            self.ed_fuel_name.selectAll()

        def delete_current_fuel():
            row_idx = self.list_fuels.currentRow()
            if row_idx < 0:
                return

            fuel_idx = row_idx + 1

            reply = QMessageBox.question(
                self,
                self._tr("Delete", "Удаление"),
                self._tr("Delete the selected propellant pair?", "Удалить выбранную топливную пару?"),
                QMessageBox.Yes | QMessageBox.No
            )

            if reply != QMessageBox.Yes:
                return

            del PARA[fuel_idx]
            del PARA_DEFAULT[fuel_idx]
            del PARA_RU[fuel_idx]
            del k_m_list[fuel_idx]
            del R_st_list[fuel_idx]
            del k_st_list[fuel_idx]
            del T_st_list[fuel_idx]
            del J_st_list[fuel_idx]

            self.list_fuels.takeItem(row_idx)

            self.cbFuel.clear()
            for i, name in enumerate(PARA[1:], start=1):
                self.cbFuel.addItem(self._fuel_name(i), i)

            if self.list_fuels.count() > 0:
                new_row = min(row_idx, self.list_fuels.count() - 1)
                self.list_fuels.setCurrentRow(new_row)
                self.cbFuel.setCurrentIndex(new_row)

            self.on_change()
            self.timer.start()

        self.list_fuels.currentRowChanged.connect(load_fuel_from_list)
        self.btn_save_fuel_params.clicked.connect(save_current_fuel)
        self.btn_edit_fuel.clicked.connect(edit_fuel_name)
        self.btn_delete_fuel.clicked.connect(delete_current_fuel)

        current_row = self.cbFuel.currentIndex()
        self.list_fuels.setCurrentRow(current_row)

        dlg.resize(760, 360)
        dlg.show()

        self._fuel_params_dialog = dlg

    def eventFilter(self, obj, event):
        # ===== 1. Кнопка редактирования топливной пары =====
        if hasattr(self, "btn_edit_fuel") and obj == self.btn_edit_fuel:
            if event.type() == QEvent.Enter:
                self.btn_edit_fuel.setIcon(self.icon_edit_hover)
                return False

            elif event.type() == QEvent.Leave:
                self.btn_edit_fuel.setIcon(self.icon_edit_normal)
                return False

        # ===== 2. Кнопка удаления топливной пары =====
        if hasattr(self, "btn_delete_fuel") and obj == self.btn_delete_fuel:
            if event.type() == QEvent.Enter:
                self.btn_delete_fuel.setIcon(self.icon_delete_hover)
                return False

            elif event.type() == QEvent.Leave:
                self.btn_delete_fuel.setIcon(self.icon_delete_normal)
                return False

        # ===== 3. Фильтр ввода для числовых QLineEdit =====
        if (
                hasattr(self, "_all_numeric_edits")
                and obj in self._all_numeric_edits
                and event.type() == QEvent.KeyPress
        ):
            key = event.key()
            modifiers = event.modifiers()
            is_shortcut = bool(modifiers & (Qt.ControlModifier | Qt.MetaModifier))

            if is_shortcut:
                if key in (Qt.Key_C, Qt.Key_X, Qt.Key_A, Qt.Key_Z, Qt.Key_Y):
                    return False
                if key == Qt.Key_V:
                    pasted = QApplication.clipboard().text().strip()
                    if pasted and re.fullmatch(r"[0-9eE+\-.,\s]+", pasted):
                        return False
                    QApplication.beep()
                    return True

            allowed_keys = {
                Qt.Key_Backspace,
                Qt.Key_Delete,
                Qt.Key_Left,
                Qt.Key_Right,
                Qt.Key_Home,
                Qt.Key_End,
                Qt.Key_Tab,
                Qt.Key_Return,
                Qt.Key_Enter,
                Qt.Key_Escape,
            }

            if key in allowed_keys:
                return False

            text = event.text()

            if text and not re.match(r"[0-9eE\+\-\,\.]", text):
                QApplication.beep()
                return True

        return super().eventFilter(obj, event)

    # ---------------- Toolbar / Theme ----------------
    def _build_toolbar(self):
        from PyQt5.QtWidgets import QAction

        tb = self.addToolBar("Main")
        tb.setMovable(False)
        tb.setIconSize(QtCore.QSize(18, 18))
        s = self.style()

        # --- действия с горячими клавишами (НЕ на тулбаре) ---
        self.act_calc = QAction(s.standardIcon(s.SP_MediaPlay),
                                "Calculate parameters (Ctrl+R)", self)
        self.act_calc.setShortcut("Ctrl+R")
        self.act_calc.setStatusTip("Calculate geometry and update the report")
        self.act_calc.triggered.connect(self.on_calc_params)
        self.addAction(self.act_calc)

        self.act_geom = QAction(s.standardIcon(s.SP_ComputerIcon),
                                "Drawing (Ctrl+D)", self)
        self.act_geom.setShortcut("Ctrl+D")
        self.act_geom.setStatusTip("Show the nozzle drawing")
        self.act_geom.triggered.connect(self.on_draw_geom)
        self.addAction(self.act_geom)

        # --- содержимое тулбара как один виджет ---
        wrap = QWidget()
        lay = QHBoxLayout(wrap)
        lay.setContentsMargins(6, 0, 6, 0)
        lay.setSpacing(10)

        # 1) Кнопка "Открыть"
        self.btn_tb_open = QPushButton()
        self.btn_tb_open.setIcon(s.standardIcon(s.SP_DialogOpenButton))
        self.btn_tb_open.setFlat(True)
        self.btn_tb_open.setToolTip("Auto-fill... (Ctrl+L)")
        self.btn_tb_open.clicked.connect(self.on_load_autofill)
        self.btn_tb_open.setFixedSize(26, 24)
        lay.addWidget(self.btn_tb_open)

        # 2) Кнопка "Сохранить"
        self.btn_tb_save = QPushButton()
        self.btn_tb_save.setIcon(s.standardIcon(s.SP_DialogSaveButton))
        self.btn_tb_save.setFlat(True)
        self.btn_tb_save.setToolTip("Save... (Ctrl+S)")
        self.btn_tb_save.clicked.connect(self.on_save_results)
        self.btn_tb_save.setFixedSize(26, 24)
        lay.addWidget(self.btn_tb_save)

        # 3) Тумблер темы
        self.btn_themeToggle = QPushButton("☀")
        self.btn_themeToggle.setObjectName("themeToggle")
        self.btn_themeToggle.setCheckable(True)
        self.btn_themeToggle.setCursor(Qt.PointingHandCursor)
        self.btn_themeToggle.setFixedSize(60, 26)
        self.btn_themeToggle.setToolTip("Toggle light/dark theme")
        self.btn_themeToggle.toggled.connect(self._on_theme_toggled)
        lay.addWidget(self.btn_themeToggle)

        # 4) Language selector
        self.btn_language = QPushButton("рус")
        self.btn_language.setObjectName("languageToggle")
        self.btn_language.setCursor(Qt.PointingHandCursor)
        self.btn_language.setFixedSize(48, 26)
        self.btn_language.setToolTip("Switch language")
        self.btn_language.clicked.connect(self._toggle_language)
        lay.addWidget(self.btn_language)

        # 5) Растяжка слева от заголовка
        lay.addStretch(1)

        # 6) Название приложения
        self.lbl_title = QLabel("LRE Nozzle Designer")
        f = self.lbl_title.font()
        f.setPointSize(12)
        f.setBold(True)
        self.lbl_title.setFont(f)
        self.lbl_title.setAlignment(Qt.AlignCenter)
        self.lbl_title.setStyleSheet("color: palette(WindowText);")
        lay.addWidget(self.lbl_title, 0, Qt.AlignCenter)

        lay.addStretch(1)

        # 7) Кнопки окна справа
        buttons_wrap = QWidget()
        hb = QHBoxLayout(buttons_wrap)
        hb.setContentsMargins(12, 0, 0, 0)
        hb.setSpacing(0)

        self.btn_win_min = QPushButton("–")
        self.btn_win_min.setObjectName("winMin")
        self.btn_win_min.setFlat(True)
        self.btn_win_min.setFixedSize(32, 24)
        self.btn_win_min.clicked.connect(self.showMinimized)
        hb.addWidget(self.btn_win_min)

        self.btn_win_max = QPushButton("□")
        self.btn_win_max.setObjectName("winMax")
        self.btn_win_max.setFlat(True)
        self.btn_win_max.setFixedSize(32, 24)
        self.btn_win_max.clicked.connect(self._toggle_max_restore)
        hb.addWidget(self.btn_win_max)

        self.btn_win_close = QPushButton("✕")
        self.btn_win_close.setObjectName("winClose")
        self.btn_win_close.setFlat(True)
        self.btn_win_close.setFixedSize(32, 24)
        self.btn_win_close.clicked.connect(self.close)
        hb.addWidget(self.btn_win_close)

        lay.addWidget(buttons_wrap, 0, Qt.AlignRight | Qt.AlignVCenter)

        act = QWidgetAction(self)
        act.setDefaultWidget(wrap)
        tb.addAction(act)

    def changeEvent(self, event):
        from PyQt5.QtCore import QEvent
        if event.type() == QEvent.WindowStateChange:
            self._update_max_button_icon()
        super().changeEvent(event)

    def _toggle_max_restore(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()
        self._update_max_button_icon()

    def _update_max_button_icon(self):
        if not hasattr(self, "btn_win_max"):
            return

        if self.isMaximized():
            self.btn_win_max.setText("❐")
            self.btn_win_max.setToolTip(self._tr("Restore window", "Восстановить окно"))
            font = self.btn_win_max.font()
            font.setPointSize(12)
            self.btn_win_max.setFont(font)
        else:
            self.btn_win_max.setText("▫")
            self.btn_win_max.setToolTip(self._tr("Maximize window", "Развернуть окно"))
            font = self.btn_win_max.font()
            font.setPointSize(20)
            self.btn_win_max.setFont(font)

    def _update_theme_button(self, mode: str):
        if not hasattr(self, "btn_themeToggle"):
            return
        checked = (mode == "dark")
        blocker = QtCore.QSignalBlocker(self.btn_themeToggle)
        self.btn_themeToggle.setChecked(checked)
        self.btn_themeToggle.setText("🌙" if checked else "☀")
        del blocker

    def _on_theme_toggled(self, checked: bool):
        mode = "dark" if checked else "light"
        self._apply_palette(mode)
        self._settings.setValue("ui/theme", mode)
        self._update_theme_button(mode)

    def _apply_palette(self, mode: str):
        """Configure the palette and styles for light or dark mode."""
        app = QApplication.instance()
        app.setStyle("Fusion")

        if mode == "dark":
            pal = QPalette()
            pal.setColor(QPalette.Window, QColor("#121212"))
            pal.setColor(QPalette.WindowText, QColor("#FFFFFF"))
            pal.setColor(QPalette.Base, QColor("#1E1E1E"))
            pal.setColor(QPalette.AlternateBase, QColor("#242424"))
            pal.setColor(QPalette.ToolTipBase, QColor("#FFFFFF"))
            pal.setColor(QPalette.ToolTipText, QColor("#121212"))
            pal.setColor(QPalette.Text, QColor("#FFFFFF"))
            pal.setColor(QPalette.Button, QColor("#1F1F1F"))
            pal.setColor(QPalette.ButtonText, QColor("#FFFFFF"))
            pal.setColor(QPalette.BrightText, QColor("#FF80AB"))
            pal.setColor(QPalette.Highlight, QColor("#BB86FC"))
            pal.setColor(QPalette.HighlightedText, QColor("#000000"))

            side_bg = "#181818"
            center_bg = "#121212"
            panel_bg = "#1E1E1E"
            report_bg = "#181818"
            border_col = "rgba(255,255,255,0.12)"
            field_border = "rgba(255,255,255,0.22)"
            field_focus = "#BB86FC"

            nav_hover = "rgba(255,255,255,0.12)"
            nav_checked = "rgba(187,134,252,0.30)"

            primary_btn_bg = "#BB86FC"
            primary_btn_fg = "#000000"

            theme_border = "#BB86FC"
            theme_bg = "#1F1F1F"
            theme_fg = "#EDE7F6"

            # <<< вот ЭТИ четыре + общий цвет текста >>>
            hover_bg = "#3D2C78"
            hover_fg = "#FFFFFF"
            select_bg = "#BB86FC"
            select_fg = "#000000"
            text_col = "#FFFFFF"
            required_bg = "rgba(187,134,252,0.10)"
            required_border = "rgba(187,134,252,0.55)"
        else:
            pal = QPalette()
            pal.setColor(QPalette.Window, QColor("#F2F2F2"))
            pal.setColor(QPalette.WindowText, QColor("#1F1F1F"))
            pal.setColor(QPalette.Base, QColor("#FFFFFF"))
            pal.setColor(QPalette.AlternateBase, QColor("#F5F5F5"))
            pal.setColor(QPalette.ToolTipBase, QColor("#FFFFFF"))
            pal.setColor(QPalette.ToolTipText, QColor("#1F1F1F"))
            pal.setColor(QPalette.Text, QColor("#1F1F1F"))
            pal.setColor(QPalette.Button, QColor("#FAFAFA"))
            pal.setColor(QPalette.ButtonText, QColor("#1F1F1F"))
            pal.setColor(QPalette.BrightText, QColor("#D32F2F"))
            pal.setColor(QPalette.Highlight, QColor("#6200EE"))
            pal.setColor(QPalette.HighlightedText, QColor("#FFFFFF"))

            side_bg = "#6200EE"
            center_bg = "#F2F2F2"
            panel_bg = "#FFFFFF"
            report_bg = "#FFFFFF"
            border_col = "rgba(0,0,0,0.10)"
            field_border = "rgba(0,0,0,0.16)"
            field_focus = "#6200EE"

            nav_hover = "rgba(255,255,255,0.20)"
            nav_checked = "rgba(255,255,255,0.32)"

            primary_btn_bg = "#6200EE"
            primary_btn_fg = "#FFFFFF"

            theme_border = "#7C4DFF"
            theme_bg = "#EDE7F6"
            theme_fg = "#311B92"

            # цвета для выпадающих списков в светлой теме
            hover_bg = "#E8DDFF"
            hover_fg = "#311B92"
            select_bg = "#6200EE"
            select_fg = "#FFFFFF"
            text_col = "#1F1F1F"
            required_bg = "#F7F2FF"
            required_border = "rgba(98,0,238,0.35)"

        app.setPalette(pal)

        base_styles = f"""
            #side {{
                background:{side_bg};
                color:#fff;
                border-radius:16px;
            }}
            #side QPushButton {{
                background:transparent;
                color:#EDE7F6;
                text-align:left;
                padding:8px 14px;
                border:none;
                border-radius:10px;
                font-size:16px;
            }}
            #side QPushButton:hover {{
                background:{nav_hover};
            }}
            #side QPushButton:checked {{
                background:{nav_checked};
                color:#FFFFFF;
            }}

            #centerPanel {{
                background:{center_bg};
                border-radius:16px;
                border: 1px solid {border_col};
            }}

            #inputPanel {{
                border-radius:14px;
                background:{panel_bg};
                padding: 50px;
            }}

            QScrollArea QWidget#inputPanel {{
                padding: 18px;
            }}

            QFrame#requiredInputsFrame {{
                border: 1px solid {required_border};
                border-radius: 14px;
                background: {required_bg};
            }}

            QLabel#requiredInputsTitle {{
                font-weight: 700;
                color: {field_focus};
            }}

            #graphPage {{
                border-radius:14px;
                background:{panel_bg};
            }}

            #reportBox {{
                border-radius:12px;
                border:1px solid {border_col};
                background:{report_bg};
                padding:6px;
            }}

            * {{ outline: 0; }}
            QToolBar {{
                border: none;
                padding: 4px 8px;
                background: transparent;
            }}
            QToolBar QToolButton {{
                padding: 6px 10px;
                border-radius: 8px;
            }}
            QToolBar QToolButton:hover {{
                background: rgba(127,127,127,0.15);
            }}
            QToolBar QLabel {{ font-weight: 600; }}

            QPushButton {{
                border: 1px solid {field_border};
                padding: 6px 12px;
                border-radius: 10px;
                background: palette(Button);
            }}
            QPushButton:hover {{
                border-color: {field_focus};
            }}
            QPushButton:disabled {{
                opacity: .6;
            }}

            QPushButton#helpButton {{
                border: 1px solid #8A8A8A;
                border-radius: 8px;
                padding: 0px;
                font-weight: 700;
                font-size: 10px;
                color: #8A8A8A;
                background: transparent;
            }}
            QPushButton#helpButton:hover {{
                background: {hover_bg};
                color: {hover_fg};
            }}

            /* Основная фиолетовая кнопка (если задашь objectName="primaryButton") */
            QPushButton#primaryButton {{
                background: {primary_btn_bg};
                color: {primary_btn_fg};
                border: none;
                font-weight: 600;
            }}
            QPushButton#primaryButton:hover {{
                background: {primary_btn_bg};
                filter: brightness(1.05);
            }}

            QLineEdit, QComboBox, QTextEdit {{
                border: 1px solid {field_border};
                border-radius: 9px;
                padding: 4px 8px;
                background: palette(Base);
            }}
            QLineEdit:focus, QComboBox:focus, QTextEdit:focus {{
                border: 1px solid {field_focus};
            }}

            QStatusBar {{
                padding: 2px 8px;
            }}

            QProgressBar {{
                border-radius: 7px;
                text-align: center;
                font-size: 12px;
                background: rgba(0,0,0,0.08);
            }}
            QProgressBar::chunk {{
                border-radius: 6px;
                background: palette(Highlight);
            }}

            /* popup QComboBox */
            QComboBox QAbstractItemView {{
                background: {panel_bg};
                color: {text_col};
            }}



            /* Цветные скроллбары с фиолетовым ползунком */
            QScrollBar:vertical {{
                background: transparent;
                width: 10px;
                margin: 4px 0 4px 0;
            }}
            QScrollBar::handle:vertical {{
                background: {field_focus};
                min-height: 20px;
                border-radius: 5px;
            }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{
                height: 0;
                background: transparent;
            }}

            #themeToggle, #languageToggle {{
                border-radius: 14px;
                border: 2px solid {theme_border};
                padding: 0 10px;
                font-size: 13px;
                font-weight: 600;
                background-color: {theme_bg};
                color: {theme_fg};
            }}
            #themeToggle:hover, #languageToggle:hover {{
                border-color: {field_focus};
            }}
            #themeToggle:checked {{
                background-color: {"#121212" if mode == "dark" else "#6200EE"};
                color: {"#BB86FC" if mode == "dark" else "#FFFFFF"};
                border-color: {field_focus};
            }}

            #winMin, #winClose, #winMax {{
                border: none;
                border-radius: 0;
                padding: 0;
                margin: 0;
                background: transparent;
            }}
            #winMin:hover, #winMax:hover {{
                background: rgba(255,255,255,0.10);
            }}
            #winClose:hover {{
                background: #e81123;
                color: white;
            }}
        """

        self.setStyleSheet(base_styles)

        # применяем ту же тему к matplotlib-графикам
        if hasattr(self, "page_geom"):
            try:
                self._set_plot_theme(mode)
            except Exception:
                pass
        if hasattr(self, "lbl_nozzle_status"):
            self._update_nozzle_status()

    def _crop_curve_by_x_range(self, x_arr, y_arr, x_min, x_max):
        x_arr = np.asarray(x_arr, dtype=float)
        y_arr = np.asarray(y_arr, dtype=float)
        mask = np.isfinite(x_arr) & np.isfinite(y_arr)
        x_arr = x_arr[mask]
        y_arr = y_arr[mask]
        if x_arr.size == 0 or y_arr.size == 0:
            return x_arr, y_arr

        order = np.argsort(x_arr)
        x_arr = x_arr[order]
        y_arr = y_arr[order]
        x_min, x_max = sorted((float(x_min), float(x_max)))
        x_min = max(x_min, float(x_arr[0]))
        x_max = min(x_max, float(x_arr[-1]))

        inner = (x_arr >= x_min) & (x_arr <= x_max)
        x_crop = x_arr[inner]
        y_crop = y_arr[inner]

        y_left = float(np.interp(x_min, x_arr, y_arr))
        y_right = float(np.interp(x_max, x_arr, y_arr))
        if x_crop.size == 0 or not np.isclose(x_crop[0], x_min):
            x_crop = np.insert(x_crop, 0, x_min)
            y_crop = np.insert(y_crop, 0, y_left)
        if x_crop.size == 0 or not np.isclose(x_crop[-1], x_max):
            x_crop = np.append(x_crop, x_max)
            y_crop = np.append(y_crop, y_right)
        return x_crop, y_crop

    def _set_plot_theme(self, mode: str):
        """Apply the theme mode to every PlotWidget and redraw the graphs."""
        plots = []
        if hasattr(self, "page_geom"):
            plots.append(self.page_geom.plot)
        if hasattr(self, "page_M"):
            plots.append(self.page_M.plot)
        if hasattr(self, "page_T"):
            plots.append(self.page_T.plot)
        if hasattr(self, "page_P"):
            plots.append(self.page_P.plot)
        if hasattr(self, "page_thermal"):
            plots.append(self.page_thermal.plot)
            if hasattr(self.page_thermal, "contour_plot"):
                plots.append(self.page_thermal.contour_plot)

        for pw in plots:
            pw.set_theme(mode)

        try:
            if getattr(self, "x_curve", None) is not None and getattr(self, "y_curve", None) is not None:
                xg, yg, Xg, Yg = self.model.take_x_y()
                self.page_geom.draw_geometry(self.model, xg, yg, Xg, Yg)

            if getattr(self, "M", None) is not None and self.x_curve is not None:
                self.page_M.draw_fill(
                    self.x_curve, self.y_curve, self.M,
                    y0=0.0, cmap="turbo", refine=4, clabel="M"
                )

            if getattr(self, "T", None) is not None and self.x_curve is not None:
                self.page_T.draw_fill(
                    self.x_curve, self.y_curve, self.T,
                    y0=0.0, cmap="turbo", refine=4, clabel=self._tr("T, K", "T, К")
                )

            if getattr(self, "P", None) is not None and self.x_curve is not None:
                self.page_P.draw_fill(
                    self.x_curve, self.y_curve, self.P,
                    y0=0.0, cmap="turbo", refine=4, clabel=self._tr("p, MPa", "p, МПа")
                )


            if hasattr(self, "page_thermal"):
                self.page_thermal._render_transposed_table()
                table = getattr(self, "heat_load_table", None)
                if table is not None and hasattr(table, "columns") and "x [mm]" in table.columns:
                    x_heat = np.asarray(table["x [mm]"], dtype=float)
                    x_min = float(np.nanmin(x_heat))
                    x_max = float(np.nanmax(x_heat))
                    xlim = (x_min, x_max)
                    self.page_thermal.plot.draw_lines(
                        x_heat,
                        [
                            (np.asarray(table["q_k [W/m^2]"], dtype=float), "q_k"),
                            (np.asarray(table["q_l [W/m^2]"], dtype=float), "q_l"),
                            (np.asarray(table["q_sum [W/m^2]"], dtype=float), "q_sum"),
                        ],
                        xlabel=self._tr("x [mm]", "x [\u043c\u043c]"),
                        ylabel=self._tr("q [W/m^2]", "q [\u0412\u0442/\u043c^2]"),
                        xlim=xlim,
                        vlines=x_heat
                    )
                    if (
                            getattr(self, "x_curve", None) is not None
                            and getattr(self, "y_curve", None) is not None
                            and "R/R_t [-]" in table.columns
                    ):
                        x_arr = np.asarray(self.x_curve, dtype=float)
                        y_arr = np.asarray(self.y_curve, dtype=float)
                        contour_x, contour_y = self._crop_curve_by_x_range(x_arr, y_arr, x_min, x_max)
                        radii = np.asarray(table["R/R_t [-]"], dtype=float) * float(self.model.R_kr)
                        self.page_thermal.contour_plot.draw_upper_contour(
                            contour_x,
                            contour_y,
                            points=(x_heat, radii),
                            xlabel=self._tr("x [mm]", "x [\u043c\u043c]"),
                            ylabel=self._tr("R [mm]", "R [\u043c\u043c]"),
                            line_label=self._tr("nozzle contour", "\u043a\u043e\u043d\u0442\u0443\u0440 \u0441\u043e\u043f\u043b\u0430"),
                            points_label=self._tr("thermal points", "\u0442\u043e\u0447\u043a\u0438 \u0442\u0435\u043f\u043b\u043e\u0432\u043e\u0433\u043e \u0440\u0430\u0441\u0447\u0435\u0442\u0430"),
                            xlim=xlim,
                            vlines=x_heat
                        )
        except Exception:
            pass

    # --- перетаскивание окна ---
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and event.pos().y() <= 40:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None and (event.buttons() & Qt.LeftButton):
            self.move(event.globalPos() - self._drag_pos)
            event.accept()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton and event.pos().y() <= 40:
            self._toggle_max_restore()
            event.accept()
        super().mouseDoubleClickEvent(event)

    def _apply_theme_from_ui(self):
        idx = self.cb_theme.currentIndex()
        if idx == 1:
            self._apply_palette("dark")
            self._settings.setValue("ui/theme", "dark")
        else:
            self._apply_palette("light")
            self._settings.setValue("ui/theme", "light")

    def on_auto_mode_toggled(self, state):
        """Handle toggling the Auto-fill checkbox."""
        self._auto_mode = (state == Qt.Checked)

        # В полном авто-режиме запретим редактировать авто-поля,
        # чтобы было понятно, что ими управляет программа.
        for key, ed in self._auto_fields.items():
            ed.setReadOnly(self._auto_mode)

        # При включении авторежима забываем ручные переопределения
        if self._auto_mode:
            self._overridden.clear()

        # Пересчитать всё с учётом нового режима
        if hasattr(self, "timer"):
            self.timer.start()

    def _auto_allowed(self, key: str) -> bool:
        """
        Whether the field identified by 'key' can be recalculated automatically now.
        - In auto mode, always return True.
        - In manual mode, only return True when the user has not overridden it.
        """
        if self._auto_mode:
            return True
        return key not in self._overridden

    def _load_settings_and_theme(self):
        self._settings = QtCore.QSettings("LRE", "NozzleDesigner")
        theme = self._settings.value("ui/theme", "light")
        if theme not in ("light", "dark"):
            theme = "light"
        self._apply_palette(theme)
        self._update_theme_button(theme)

    def closeEvent(self, ev):
        self._settings.setValue("window/size", self.size())
        self._settings.setValue("window/pos", self.pos())
        super().closeEvent(ev)

    # ---------------- Остальной функционал окна ----------------

    def _report_text(self) -> str:
        try:
            return getattr(self, "_last_report_text", self.txtParams.toPlainText())
        except Exception:
            return ""

    def _report_params_block(self) -> str:
        lines = ["# LRE_NOZZLE_DESIGNER_PARAMS_BEGIN"]
        for key, value in self._collect_params_for_save():
            lines.append(f"# {key}\t{value}")
        lines.append("# LRE_NOZZLE_DESIGNER_PARAMS_END")
        return "\n".join(lines)

    def _report_text_for_save(self) -> str:
        report = self._report_text().rstrip()
        return report + "\n\n" + self._report_params_block() + "\n"

    def _split_pair_text(self, s: str):
        parts = re.split(r"\s*[–—-]\s*", (s or "").strip(), maxsplit=1)
        ox = parts[0].strip() if len(parts) >= 1 else ""
        fu = parts[1].strip() if len(parts) >= 2 else ""
        return ox, fu

    def _on_thrust_edited(self, source: str):
        self._thrust_source = source
        if hasattr(self, "cb_calc_mode"):
            target_idx = 1 if source == "P_8" else 0
            if self.cb_calc_mode.currentIndex() != target_idx:
                with QtCore.QSignalBlocker(self.cb_calc_mode):
                    self.cb_calc_mode.setCurrentIndex(target_idx)
                self._calc_mode = "vacuum" if target_idx == 1 else "sea_level"
        if hasattr(self, "timer"):
            self.timer.start()

    def _current_thrust_input(self):
        source = getattr(self, "_thrust_source", "P_0")
        fields = {
            "P_0": self.ed_P_0,
            "P_8": self.ed_P_8,
        }
        if source not in fields:
            source = "P_0"
        return source, self._v(fields[source])

    def _resolve_design_thrust(self, p_k, thrust_value, thrust_source, coefJ, z_k, T_k, p_e, p_h):
        self.model.compute_geometry(p_k, 1.0, coefJ, z_k, T_k, p_e, p_h=p_h, calc_mode=self._calc_mode)
        if thrust_source == "P_0":
            if self.model.J_0_ud is None or self.model.J_0_ud <= 0:
                raise ValueError("specific impulse at sea level is non-positive")
            return thrust_value * self.model.J_h_ud / self.model.J_0_ud
        if thrust_source == "P_8":
            if self.model.J_8_ud is None or self.model.J_8_ud <= 0:
                raise ValueError("specific impulse in vacuum is non-positive")
            return thrust_value * self.model.J_h_ud / self.model.J_8_ud
        return thrust_value

    def _on_p_k_manual_change(self, *_):
        # как только пользователь меняет p_k,
        # снова разрешаем автоматически пересчитывать T_k
        if "T_k" in self._overridden:
            self._overridden.remove("T_k")

    def _on_calc_mode_changed(self, *_):
        idx = self.cb_calc_mode.currentIndex()
        self._calc_mode = "vacuum" if idx == 1 else "sea_level"
        self._thrust_source = "P_8" if self._calc_mode == "vacuum" else "P_0"
        if hasattr(self, "timer"):
            self.timer.start()

    def add_overlay_unit(self, ed: QLineEdit, unit_text: str):
        lab = QLabel(unit_text, ed)
        lab.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        lab.setStyleSheet("color:#888; background:transparent; padding:0px;")
        lab.adjustSize()

        def reposition():
            lab.adjustSize()
            ed.setTextMargins(0, 0, lab.width() + 8, 0)
            x = ed.rect().right() - lab.width() - 4
            y = (ed.height() - lab.height()) // 2
            lab.move(x, y)

        ed.textChanged.connect(lambda *_: reposition())
        old_resize = getattr(ed, "resizeEvent", None)

        def _resize(ev):
            if callable(old_resize):
                old_resize(ev)
            reposition()

        ed.resizeEvent = _resize
        ed._reposition_unit = reposition
        reposition()
        return lab

    def _collect_params_for_save(self):
        m = self.model

        def v(x):
            return "" if x is None else (float(x) if isinstance(x, (int, float, np.floating)) else x)

        pairs = [
            ("timestamp", datetime.now().isoformat(timespec="seconds")),
            ("fuel_name", self.cbFuel.currentText().strip()),
            ("fuel_index", v(m.idx)),
            ("calc_mode", self._calc_mode),
            ("k_m", v(m.k_m)), ("R", v(m.R)), ("k", v(m.k)), ("T_st", v(m.T_st)), ("J_st_ud", v(m.J_st_ud)),
            ("p_k_MPa", v(m.p_k)), ("p_e_MPa", v(m.p_e)),
            ("P_0_N", v(m.P_0)), ("P_8_N", v(m.P_8)),
            ("coefJ", v(m.coefJ)), ("z_k", v(m.z_k)),
            ("T_k_K", v(m.T_k)), ("p_a_MPa", v(m.p_a)),
            ("k1", v(m.k1)), ("p_MPa_sea_level", v(m.p)),
            ("J_pr_ud_st", v(m.J_pr_ud_st)), ("J_r_ud", v(m.J_r_ud)),
            ("J_8_ud", v(m.J_8_ud)), ("J_0_ud", v(m.J_0_ud)),
            ("m_sum_kg_s", v(m.m_)), ("m_g_kg_s", v(m.m_g)), ("m_ok_kg_s", v(m.m_ok)), ("K0", v(m.K_0)),
            ("D_kr_mm", v(m.D_kr)), ("D_a_mm", v(m.D_a)), ("D_k_mm", v(m.D_k)), ("f_a", v(m.fa)),
            ("R_kr_mm", v(m.R_kr)), ("R_a_mm", v(m.R_a)), ("R_k_mm", v(m.R_k)), ("R3_mm", v(m.R3)),
            ("L_c_mm", v(m.L_c)), ("L_vh_mm", v(m.L_vh)), ("L_g_mm", v(m.L_g)), ("L_cy_mm", v(m.L_cy)),
            ("L_dv_mm", v(m.L_dv)), ("L_du_mm", v(m.L_du)),
            ("a1_mm", v(m.a1)), ("a2_mm", v(m.a2)), ("alpha1_rad", v(m.alpha1)), ("alpha2_rad", v(m.alpha2)),
        ]
        return pairs

    def _goto(self, idx, btn):
        for b in (self.btn_page_main, self.btn_page_geom, self.btn_page_M, self.btn_page_T, self.btn_page_P, self.btn_page_thermal):
            b.setChecked(b is btn)
        self.stack.setCurrentIndex(idx)

    def _current_p_h(self):
        source = getattr(self, "_thrust_source", "P_0")
        return 0.0 if source == "P_8" else 0.0981

    def _expansion_warnings(self, p_e, p_h):
        warnings = []
        if self._calc_mode == "vacuum":
            if p_e > 0.02:
                warnings.append(self._tr(
                    "For a vacuum engine, the nozzle exit pressure is fairly high. Specific impulse may be lost because of insufficient expansion.",
                    "Для вакуумного двигателя давление на срезе довольно высокое. Возможна потеря удельного импульса из-за недостаточного расширения."
                ))
            return warnings

        if p_h > 0 and p_e < 0.4 * p_h:
            warnings.append(self._tr(
                "The nozzle is strongly overexpanded for the selected mode. In reality, flow separation, shock waves and side loads are possible. The one-dimensional isentropic model may be inapplicable.",
                "Сопло сильно перерасширено для выбранного режима. В реальности возможны отрыв потока, ударные волны и боковые нагрузки. Одномерная изоэнтропическая модель может быть неприменима."
            ))
        elif p_h > 0 and p_e < p_h:
            warnings.append(self._tr(
                "The nozzle is overexpanded: the exit pressure is below the ambient pressure.",
                "Сопло перерасширено: давление на срезе ниже внешнего давления."
            ))

        if p_h > 0 and p_e > 1.5 * p_h:
            warnings.append(self._tr(
                "The nozzle is noticeably underexpanded: the exit pressure is above the ambient pressure. Part of the potential gas energy is not used inside the nozzle.",
                "Сопло заметно недорасширено: давление на срезе выше внешнего давления. Часть потенциальной энергии газа не используется внутри сопла."
            ))
        return warnings

    def _set_nozzle_status(self, kind, title, detail):
        if not hasattr(self, "lbl_nozzle_status"):
            return

        dark = False
        try:
            dark = self.palette().color(QPalette.Base).lightness() < 128
        except Exception:
            pass

        if kind == "ok":
            accent = "#16a34a"
            bg = "#12351f" if dark else "#ecfdf5"
            fg = "#dcfce7" if dark else "#14532d"
            border = "#22c55e"
        elif kind == "warning":
            accent = "#f59e0b"
            bg = "#3a2a08" if dark else "#fffbeb"
            fg = "#fef3c7" if dark else "#78350f"
            border = "#f59e0b"
        elif kind == "danger":
            accent = "#ef4444"
            bg = "#3a1414" if dark else "#fef2f2"
            fg = "#fee2e2" if dark else "#7f1d1d"
            border = "#ef4444"
        else:
            accent = "#8b5cf6"
            bg = "#25212d" if dark else "#f5f3ff"
            fg = "#ede9fe" if dark else "#4c1d95"
            border = "#8b5cf6"

        self.lbl_nozzle_status.setText(
            f"<b>{html.escape(title)}</b><br>"
            f"<span style='font-size:12px;'>{html.escape(detail)}</span>"
        )
        self.lbl_nozzle_status.setStyleSheet(
            "QLabel#nozzleStatus {"
            f"border:1px solid {border}; border-left:5px solid {accent}; "
            f"border-radius:10px; padding:8px 10px; background:{bg}; color:{fg};"
            "}"
        )

    def _update_nozzle_status(self):
        if not hasattr(self, "lbl_nozzle_status"):
            return

        J0 = getattr(self.model, "J_0_ud", None)
        P0 = getattr(self.model, "P_0", None)
        pe = getattr(self.model, "p_e", None)
        p0 = getattr(self.model, "p_0", 0.0981)

        if J0 is None or P0 is None or pe is None:
            self._set_nozzle_status(
                "neutral",
                self._tr("Nozzle status", "\u0421\u0442\u0430\u0442\u0443\u0441 \u0441\u043e\u043f\u043b\u0430"),
                self._tr(
                    "Calculate the engine and nozzle to see the physical interpretation.",
                    "\u0420\u0430\u0441\u0441\u0447\u0438\u0442\u0430\u0439\u0442\u0435 \u0434\u0432\u0438\u0433\u0430\u0442\u0435\u043b\u044c \u0438 \u0441\u043e\u043f\u043b\u043e, \u0447\u0442\u043e\u0431\u044b \u0443\u0432\u0438\u0434\u0435\u0442\u044c \u0444\u0438\u0437\u0438\u0447\u0435\u0441\u043a\u0443\u044e \u0438\u043d\u0442\u0435\u0440\u043f\u0440\u0435\u0442\u0430\u0446\u0438\u044e."
                )
            )
            return

        if J0 <= 0 or P0 <= 0:
            self._set_nozzle_status(
                "danger",
                self._tr("Vacuum / high-altitude nozzle", "\u0421\u043e\u043f\u043b\u043e \u0432\u0430\u043a\u0443\u0443\u043c\u043d\u043e\u0433\u043e / \u0432\u044b\u0441\u043e\u0442\u043d\u043e\u0433\u043e \u0442\u0438\u043f\u0430"),
                self._tr(
                    "Sea-level specific impulse or thrust is non-positive. This nozzle is not intended for operation at sea level.",
                    "\u0423\u0434\u0435\u043b\u044c\u043d\u044b\u0439 \u0438\u043c\u043f\u0443\u043b\u044c\u0441 \u0438\u043b\u0438 \u0442\u044f\u0433\u0430 \u043d\u0430 \u0443\u0440\u043e\u0432\u043d\u0435 \u043c\u043e\u0440\u044f \u043d\u0435\u043f\u043e\u043b\u043e\u0436\u0438\u0442\u0435\u043b\u044c\u043d\u044b. \u042d\u0442\u043e \u0441\u043e\u043f\u043b\u043e \u043d\u0435 \u043f\u0440\u0435\u0434\u043d\u0430\u0437\u043d\u0430\u0447\u0435\u043d\u043e \u0434\u043b\u044f \u0440\u0430\u0431\u043e\u0442\u044b \u0443 \u0437\u0435\u043c\u043b\u0438."
                )
            )
        elif pe < p0:
            self._set_nozzle_status(
                "warning",
                self._tr("Overexpanded for sea level", "\u0421\u043e\u043f\u043b\u043e \u043f\u0435\u0440\u0435\u0440\u0430\u0441\u0448\u0438\u0440\u0435\u043d\u043e \u0434\u043b\u044f \u0443\u0440\u043e\u0432\u043d\u044f \u043c\u043e\u0440\u044f"),
                self._tr(
                    "The exit pressure is lower than atmospheric pressure. The nozzle can be suitable for altitude or vacuum conditions.",
                    "\u0414\u0430\u0432\u043b\u0435\u043d\u0438\u0435 \u043d\u0430 \u0441\u0440\u0435\u0437\u0435 \u043d\u0438\u0436\u0435 \u0430\u0442\u043c\u043e\u0441\u0444\u0435\u0440\u043d\u043e\u0433\u043e. \u0422\u0430\u043a\u043e\u0435 \u0441\u043e\u043f\u043b\u043e \u043c\u043e\u0436\u0435\u0442 \u043f\u043e\u0434\u0445\u043e\u0434\u0438\u0442\u044c \u0434\u043b\u044f \u0432\u044b\u0441\u043e\u0442\u044b \u0438\u043b\u0438 \u0432\u0430\u043a\u0443\u0443\u043c\u0430."
                )
            )
        else:
            self._set_nozzle_status(
                "ok",
                self._tr("Suitable for sea level", "\u0421\u043e\u043f\u043b\u043e \u043f\u043e\u0434\u0445\u043e\u0434\u0438\u0442 \u0434\u043b\u044f \u0443\u0440\u043e\u0432\u043d\u044f \u043c\u043e\u0440\u044f"),
                self._tr(
                    "The sea-level specific impulse is positive, and the nozzle exit pressure is compatible with ground-level operation.",
                    "\u0423\u0434\u0435\u043b\u044c\u043d\u044b\u0439 \u0438\u043c\u043f\u0443\u043b\u044c\u0441 \u043d\u0430 \u0443\u0440\u043e\u0432\u043d\u0435 \u043c\u043e\u0440\u044f \u043f\u043e\u043b\u043e\u0436\u0438\u0442\u0435\u043b\u0435\u043d, \u0430 \u0434\u0430\u0432\u043b\u0435\u043d\u0438\u0435 \u043d\u0430 \u0441\u0440\u0435\u0437\u0435 \u0441\u043e\u0432\u043c\u0435\u0441\u0442\u0438\u043c\u043e \u0441 \u043d\u0430\u0437\u0435\u043c\u043d\u044b\u043c \u0440\u0435\u0436\u0438\u043c\u043e\u043c."
                )
            )

    def _apply_min_p_e_if_needed(self, p_k, T_k, p_e, p_h=None):
        if None in (p_k, T_k) or p_k <= 0 or T_k <= 0:
            return p_e
        try:
            pmin = self.model.min_p_a(COEF_J_DEFAULT, p_k, T_k)
        except Exception:
            return p_e
        if pmin is None or not np.isfinite(pmin):
            return p_e
        self.min_pa = pmin
        if p_e is None or p_e <= 0 or p_e < pmin:
            self._set_if_diff(self.ed_p_a, pmin)
            self._set_pa_validator(pmin)
            return pmin
        self._set_pa_validator(pmin)
        if p_e > NOZZLE_EXIT_PRESSURE_MAX_MPA:
            return self._enforce_p_e_bounds(show_warning=True) or NOZZLE_EXIT_PRESSURE_MAX_MPA
        return p_e

    def on_calc_params(self):
        # 1. Сначала пробрасываем ручные значения "табличных" параметров в модель
        for attr, ed in self._std_fields.items():
            val = self._v(ed)
            if val is not None:
                setattr(self.model, attr, val)

        # Если галочка автозаполнения выключена и ты хочешь,
        # чтобы вручную введённые авто-поля тоже использовались в модели:
        if not self.chk_autoTk.isChecked():
            for attr, ed in self._auto_fields.items():
                val = self._v(ed)
                if val is not None:
                    setattr(self.model, attr, val)

        def fnum(ed: QLineEdit):
            s = ed.text().strip().replace(',', '.');
            return float(s) if s else None

        p_k = fnum(self.ed_p_k)
        thrust_source, thrust_value = self._current_thrust_input()
        P_calc = thrust_value
        coefJ = COEF_J_DEFAULT
        z_k = 1.0
        self.ed_z_k.setText("1")
        cur_Tk = fnum(self.ed_T_k)

        # В полном авто-режиме T_k всегда берём из формулы
        if self._auto_mode and (p_k is not None):
            Tk_auto = self.model.auto_Tk(p_k)
            if Tk_auto is not None and np.isfinite(Tk_auto):
                cur_Tk = Tk_auto
                self.ed_T_k.blockSignals(True)
                self.ed_T_k.setText(f"{Tk_auto:.10g}")
                self.ed_T_k.blockSignals(False)

        p_e = fnum(self.ed_p_a)
        p_h = self._current_p_h()
        if p_e is not None:
            p_e = self._enforce_p_e_bounds(show_warning=True) or p_e

        if any(v is None for v in [p_k, thrust_value, z_k, cur_Tk, p_e]):
            QMessageBox.warning(self, self._tr("Input", "Ввод"),
                                self._tr("Fill in p_c, p_e, P_SL or P_inf, and T_c first.",
                                         "Сначала заполните p_c, p_e, P_SL или P_inf и T_c."))
            return

        checks = [
            (p_k <= 0, self._tr("Combustion chamber pressure must be positive.",
                                "Давление в камере должно быть положительным.")),
            (p_e <= 0, self._tr("Nozzle exit pressure must be positive.",
                                "Давление на срезе сопла должно быть положительным.")),
            (p_e >= p_k, self._tr("Nozzle exit pressure must be lower than chamber pressure.",
                                  "Давление на срезе должно быть меньше давления в камере.")),
            (cur_Tk <= 0, self._tr("Combustion chamber temperature must be positive.",
                                   "Температура в камере должна быть положительной.")),
            (z_k <= 0, self._tr("The number of chambers must be positive.",
                                "Количество камер должно быть положительным.")),
            (thrust_value <= 0, self._tr("Thrust must be positive.",
                                   "Расчетная тяга P_h должна быть положительной.")),
        ]
        for failed, message in checks:
            if failed:
                QMessageBox.critical(self, self._tr("Input error", "Ошибка ввода"), message)
                return

        try:
            P_calc = self._resolve_design_thrust(p_k, thrust_value, thrust_source, coefJ, z_k, cur_Tk, p_e, p_h)
            res = self.model.compute_geometry(p_k, P_calc, coefJ, z_k, cur_Tk, p_e,
                                              p_h=p_h, calc_mode=self._calc_mode)
            if self.model.J_h_ud is None or self.model.J_h_ud <= 0:
                QMessageBox.critical(
                    self, self._tr("Input error", "Ошибка ввода"),
                    self._tr("Specific impulse in the selected design mode is non-positive.",
                             "Удельный импульс в выбранном расчетном режиме получился неположительным.")
                )
                return
            self._set_if_diff(self.ed_P_0, self.model.P_0)
            self._set_if_diff(self.ed_P_8, self.model.P_8)
        except Exception as e:
            if "specific impulse" in str(e):
                QMessageBox.critical(
                    self, self._tr("Input error", "Ошибка ввода"),
                    self._tr("Specific impulse in the selected design mode is non-positive.",
                             "Удельный импульс в выбранном расчетном режиме получился неположительным.")
                )
                return
            QMessageBox.critical(self, self._tr("Calculation", "Расчет"),
                                 self._tr(f"Could not calculate parameters: {e}",
                                          f"Не удалось рассчитать параметры: {e}"))
            return

        self._last_report_args = (res, p_k, cur_Tk, p_e)
        self._fill_params_text(res, p_k, cur_Tk, p_e)
        self._update_nozzle_status()

        try:
            self._build_globals_from_model()
            x, y, X, Y = self.model.take_x_y()
            self.x_curve, self.y_curve = np.asarray(x, float), np.asarray(y, float)
        except Exception as e:
            QMessageBox.critical(self, self._tr("Drawing preparation", "Подготовка чертежа"),
                                 self._tr(f"Error preparing the contour: {e}",
                                          f"Ошибка подготовки контура: {e}"))
            return

        self.page_geom.btn_calc.setEnabled(True)
        self.M = None;
        self.T = None;
        self.P = None
        self.page_M.btn_calc.setEnabled(True)
        self.page_T.btn_calc.setEnabled(False)
        self.page_P.btn_calc.setEnabled(False)

        self.statusbar.showMessage(
            self._tr("Parameters recalculated and report updated.", "Параметры пересчитаны, отчет обновлен."), 3000)

    def on_draw_geom(self):
        if self.x_curve is None or self.y_curve is None:
            QMessageBox.information(self, self._tr("No data", "Нет данных"),
                                    self._tr("Click 'Calculate parameters' first.",
                                             "Сначала нажмите «Рассчитать параметры»."))
            return
        try:
            x, y, X, Y = self.model.take_x_y()
            self.page_geom.draw_geometry(self.model, x, y, X, Y)
            self._goto(1, self.btn_page_geom)
            self.page_geom.plot.canvas.draw_idle()
        except Exception as e:
            QMessageBox.critical(self, self._tr("Drawing", "Чертеж"),
                                 self._tr(f"Error plotting the contour: {e}",
                                          f"Ошибка построения контура: {e}"))

    def _fill_params_text(self, res_dict, p_k, T_k, p_a):
        def fmt_val(val):
            if val is None:
                return " "
            try:
                if isinstance(val, (int, float, np.integer, np.floating)):
                    if not np.isfinite(val):
                        return " "
                    return f"{float(val):.6g}".replace(".", ",")
                return f"{float(val):.6g}".replace(".", ",")
            except Exception:
                return str(val)

        def add_row(rows, section, name, val=None, unit=""):
            rows.append([section, name, fmt_val(val), unit])

        def get_val(key, edit=None):
            if (not self.chk_autoTk.isChecked()) and (edit is not None):
                text = edit.text().strip()
                if text:
                    try:
                        return float(text.replace(",", "."))
                    except Exception:
                        return text
            return res_dict.get(key)

        def wrap_name(name, width=36):
            words = str(name).split()
            lines = []
            cur = ""

            for w in words:
                if not cur:
                    cur = w
                elif len(cur) + 1 + len(w) <= width:
                    cur += " " + w
                else:
                    lines.append(cur)
                    cur = w

            if cur:
                lines.append(cur)

            return lines if lines else [""]

        rows = []
        ox, fu = self._split_pair_text(self.cbFuel.currentText())
        inputs = self._tr("Input and Key Parameters", "Входные и ключевые параметры")
        impulses = self._tr("Specific Impulse and Flow Rates", "Удельные импульсы и расходы")
        geometry = self._tr("Geometry Parameters", "Геометрические параметры")
        unit_n = self._tr("N", "Н")
        unit_mpa = self._tr("MPa", "МПа")
        unit_k = self._tr("K", "К")
        unit_isp = self._tr("m/s", "м/с")
        unit_flow = self._tr("kg/s", "кг/с")
        unit_mm = self._tr("mm", "мм")

        add_row(rows, inputs, self._tr("Oxidizer", "Окислитель"), ox)
        add_row(rows, inputs, self._tr("Fuel", "Горючее"), fu)
        add_row(rows, inputs, self._tr("Engine design mode", "Расчетный режим двигателя"),
                self.cb_calc_mode.currentText())
        add_row(rows, inputs, self._tr("Sea-level thrust P_SL", "Тяга на уровне моря P_SL"), self.model.P_0, unit_n)
        add_row(rows, inputs, self._tr("Vacuum thrust P_inf", "Тяга в вакууме P_inf"), self.model.P_8, unit_n)
        add_row(rows, inputs, self._tr("Chamber pressure p_c", "Давление в камере сгорания p_c"), p_k, unit_mpa)
        add_row(rows, inputs, self._tr("Nozzle exit pressure p_e", "Давление на срезе сопла p_e"), p_a, unit_mpa)
        add_row(rows, inputs, self._tr("Chamber temperature T_c", "Температура продуктов в камере T_c"), T_k, unit_k)
        # add_row(rows, "Входные и ключевые параметры", "Показатель адиабаты", self.model.k)
        # add_row(rows, "Входные и ключевые параметры", "Газовая постоянная", self.model.R, "Дж/(кг·К)")
        add_row(rows, inputs, self._tr("Propellant mass ratio K_m", "Массовое соотношение компонентов K_m"),
                self.model.k_m)

        # add_row(rows, "Удельные импульсы и расходы", "Приведённый стандартный удельный импульс тяги",
        #         get_val("J*_пр,уд,ст", self.ed_Jpr), "Н·с/кг")
        add_row(rows, impulses, self._tr("Design specific impulse J_design",
                                         "Удельный импульс на расчётном режиме J_design"),
                get_val("J*_р,уд", self.ed_Jr), unit_isp)
        add_row(rows, impulses, self._tr("Vacuum specific impulse J_inf", "Удельный импульс в вакууме J_inf"),
                get_val("J*_8,уд"), unit_isp)
        add_row(rows, impulses, self._tr("Sea-level specific impulse J_SL", "Удельный импульс на уровне моря J_SL"),
                get_val("J*_0,уд", self.ed_J0), unit_isp)
        add_row(rows, impulses, self._tr("Total propellant flow rate per chamber",
                                         "Суммарный расход топлива единичной камеры"),
                get_val("ṁ сум"), unit_flow)
        add_row(rows, impulses, self._tr("Fuel flow rate", "Расход горючего"), get_val("ṁ_г"), unit_flow)
        add_row(rows, impulses, self._tr("Oxidizer flow rate", "Расход окислителя"), get_val("ṁ_ок"), unit_flow)
        # add_row(rows, "Удельные импульсы и расходы", "Расчётный коэффициент", get_val("K0"))

        add_row(rows, geometry, self._tr("Nozzle throat diameter D_t", "Диаметр критического сечения D_t"),
                get_val("D_kr"), unit_mm)
        add_row(rows, geometry, self._tr("Nozzle expansion ratio epsilon=A_e/A_t", "Степень расширения сопла ε=A_e/A_t"),
                get_val("f_a"))
        add_row(rows, geometry, self._tr("Nozzle exit diameter D_e", "Диаметр среза сопла D_e"), get_val("D_a"), unit_mm)
        add_row(rows, geometry, self._tr("Combustion chamber diameter D_c", "Диаметр камеры сгорания D_c"),
                get_val("D_k"), unit_mm)
        add_row(rows, geometry, self._tr("Chamber head length L_head", "Длина головной части камеры L_head"),
                get_val("L_g"), unit_mm)
        add_row(rows, geometry, self._tr("Cylindrical chamber length L_cyl", "Длина цилиндрической части камеры L_cyl"),
                get_val("L_ц"), unit_mm)
        add_row(rows, geometry, self._tr("Convergent nozzle length L_conv", "Длина сужающейся части сопла L_conv"), get_val("L_вх"), unit_mm)
        add_row(rows, geometry, self._tr("Divergent nozzle length L_div", "Длина расширяющейся части сопла L_div"),
                get_val("L_c"), unit_mm)
        add_row(rows, geometry, self._tr("Chamber-nozzle assembly length L_total", "Полная длина камеры и сопла L_total"),
                get_val("Lдв"), unit_mm)

        # --- текстовый вариант ---
        text_lines = []
        current_section = None
        line_width = 60
        name_width = 38
        val_width = 12

        for section, name, val, unit in rows:
            if section != current_section:
                title = section
                n1 = max(2, (line_width - len(title)) // 2)
                n2 = line_width - n1 - len(title)
                title_underlined = ''.join('\u0332' + ch + '\u0332' for ch in title)
                text_lines.append("_" * line_width)
                text_lines.append("_" * n1 + title_underlined + "_" * n2)
                current_section = section

            unit_s = f"[{unit}]" if unit else ""
            name_lines = wrap_name(name, width=name_width - 2)

            for i, name_part in enumerate(name_lines):
                if i == len(name_lines) - 1:
                    text_lines.append(
                        f"{name_part.ljust(name_width)}{str(val).ljust(val_width)} {unit_s}"
                    )
                else:
                    text_lines.append(name_part)

        text_lines.append("_" * line_width)
        # text_lines.append("")
        # text_lines.append("")
        text_block = "\n".join(text_lines)
        self._last_report_text = text_block

        # --- табличный вариант ---
        html = f"""<div style="font-family:Consolas, Courier New; font-size:10pt;">
            <pre>{text_block}</pre>

            <br>
            <table style="
                border-collapse:collapse;
                width:100%;
                table-layout:fixed;
                font-family:Segoe UI, Arial;
                font-size:13px;
            ">
                <tr>
                    <th style="border:1px solid black; padding:5px; width:45%;">{self._tr("Parameter", "Параметр")}</th>
                    <th style="border:1px solid black; padding:5px; width:30%;">{self._tr("Value", "Значение")}</th>
                    <th style="border:1px solid black; padding:5px; width:25%;">{self._tr("Unit", "Единица")}</th>
                </tr>
        """

        current_section = None

        for section, name, val, unit in rows:
            if section != current_section:
                html += f"""
                <tr>
                    <td colspan="3" style="
                        background:#d9eef3;
                        border:1px solid black;
                        text-align:center;
                        font-weight:600;
                        padding:6px;
                    ">{section}</td>
                </tr>
                """
                current_section = section

            html += f"""
            <tr>
                <td style="border:1px solid black; padding:5px; white-space:normal; word-wrap:break-word;">{name}</td>
                <td style="border:1px solid black; padding:5px; white-space:normal; word-wrap:break-word;">{val}</td>
                <td style="border:1px solid black; padding:5px; white-space:normal; word-wrap:break-word;">{unit}</td>
            </tr>
            """

        html += """
            </table>
        </div>
        """
        html = f"""<div style="font-family:Consolas, Courier New; font-size:10pt;">
            <pre>{text_block}</pre>
        </div>
        """

        self.txtParams.clear()
        self.txtParams.setLineWrapMode(QTextEdit.WidgetWidth)
        self.txtParams.setHtml(html)

    def _build_globals_from_model(self):
        global a1, a2, alpha1, alpha2
        global D_k, D_kr, D_a, R_k, R_kr, R_a, R3
        global L_g, L_cy, L_vh, L_c, L_dv
        global x
        a1, a2 = self.model.a1, self.model.a2
        alpha1, alpha2 = self.model.alpha1, self.model.alpha2
        D_k, D_kr, D_a = float(self.model.D_k), float(self.model.D_kr), float(self.model.D_a)
        R_k, R_kr, R_a = float(self.model.R_k), float(self.model.R_kr), float(self.model.R_a)
        R3 = float(self.model.R3)
        L_g, L_cy = float(self.model.L_g), float(self.model.L_cy)
        L_vh, L_c = float(self.model.L_vh), float(self.model.L_c)
        L_dv = float(self.model.L_dv)
        x = None

    # ---------- Кнопки M ----------
    def on_calc_M(self):
        if self.x_curve is None or self.y_curve is None:
            QMessageBox.information(self, self._tr("Parameters required", "Сначала параметры"),
                                    self._tr("Click 'Calculate parameters' first.",
                                             "Сначала нажмите «Рассчитать параметры»."))
            return

        global x, k, R_kr, L_g, L_cy
        x = np.asarray(self.x_curve, dtype=float)
        k = float(self.model.k)
        R_kr = float(self.model.R_kr)
        L_g = float(self.model.L_g)
        L_cy = float(self.model.L_cy)

        self.progressBar.setValue(0)
        self.progressBar.setVisible(True)
        self.page_M.btn_calc.setEnabled(False)

        self._m_thread = QtCore.QThread(self)
        self._m_worker = MWorker(self.y_curve)
        self._m_worker.moveToThread(self._m_thread)
        self._m_thread.started.connect(self._m_worker.run)
        self._m_worker.progressed.connect(self.on_m_progress)
        self._m_worker.finished.connect(self.on_m_finished)
        self._m_worker.failed.connect(self.on_m_failed)
        self._m_worker.finished.connect(self._m_thread.quit)
        self._m_worker.finished.connect(self._m_worker.deleteLater)
        self._m_worker.failed.connect(self._m_thread.quit)
        self._m_worker.failed.connect(self._m_worker.deleteLater)
        self._m_thread.finished.connect(self._m_thread.deleteLater)
        self._m_thread.start()

    @QtCore.pyqtSlot(int)
    def on_m_progress(self, p):
        self.progressBar.setValue(int(p))

    @QtCore.pyqtSlot(object)
    def on_m_finished(self, M_arr):
        self.M = np.asarray(M_arr, dtype=float)
        self.progressBar.setValue(100)
        self.progressBar.setVisible(False)
        self.page_M.btn_calc.setEnabled(True)
        self.page_T.btn_calc.setEnabled(True)
        self.page_P.btn_calc.setEnabled(True)
        self.page_M.draw_fill(self.x_curve, self.y_curve, self.M, y0=0.0, cmap="turbo", refine=4, clabel="M")
        self.page_M.set_info(self._make_plot_info(self.M, "M", ""))
        self._goto(2, self.btn_page_M)

    @QtCore.pyqtSlot(str)
    def on_m_failed(self, msg):
        self.progressBar.reset()
        self.progressBar.setVisible(False)
        self.page_M.btn_calc.setEnabled(True)
        QMessageBox.critical(self, self._tr("Error calculating M", "Ошибка при расчете M"), msg)

    # ---------- Кнопки T ----------
    def on_calc_T(self):
        if self.M is None:
            QMessageBox.information(self, self._tr("No M data", "Нет M"),
                                    self._tr("Calculate M first.", "Сначала рассчитайте M."))
            return
        try:
            Tk = float(self.model.T_k)
            k_ = float(self.model.k)
            self.T = Tk * (1.0 + (k_ - 1.0) * (self.M ** 2) / 2.0) ** (-1.0)
            self.page_T.draw_fill(self.x_curve, self.y_curve, self.T, y0=0.0, cmap="turbo", refine=4,
                                  clabel=self._tr("T, K", "T, К"))
            self.page_T.set_info(self._make_plot_info(self.T, "T", "K"))
            self._goto(3, self.btn_page_T)
        except Exception as e:
            QMessageBox.critical(self, self._tr("Error calculating T", "Ошибка при расчете T"), str(e))

    # ---------- Кнопки P ----------
    def on_calc_P(self):
        if self.M is None:
            QMessageBox.information(self, self._tr("No M data", "Нет M"),
                                    self._tr("Calculate M first.", "Сначала рассчитайте M."))
            return
        try:
            p_k = float(self.model.p_k)
            k_ = float(self.model.k)
            self.P = p_k * (1.0 + (k_ - 1.0) * (self.M ** 2) / 2.0) ** (-k_ / (k_ - 1.0))
            self.page_P.draw_fill(self.x_curve, self.y_curve, self.P, y0=0.0, cmap="turbo", refine=4,
                                  clabel=self._tr("p, MPa", "p, МПа"))
            self.page_P.set_info(self._make_plot_info(self.P, "p", "MPa"))
            self._goto(4, self.btn_page_P)
        except Exception as e:
            QMessageBox.critical(self, self._tr("Error calculating P", "Ошибка при расчете P"), str(e))

    def _project_root(self):
        return Path(__file__).resolve().parent

    def _float_from_text(self, value):
        if value is None:
            return None
        text = str(value).strip().replace(",", ".")
        if not text:
            return None
        try:
            return float(text)
        except Exception:
            return None

    def _thermal_find_s_folders(self, pair_number):
        root = self._project_root()
        folders = []
        for folder in root.glob("para *"):
            if not folder.is_dir():
                continue
            match = re.match(r"^para\s+((?:\d+\s*)+)", folder.name, flags=re.IGNORECASE)
            if not match:
                continue
            numbers = [int(value) for value in re.findall(r"\d+", match.group(1))]
            if pair_number in numbers:
                folders.append(folder)
        return sorted(folders)

    def _thermal_read_csv_columns(self, csv_path):
        text = Path(csv_path).read_text(encoding="utf-8-sig", errors="ignore").splitlines()
        text = [line for line in text if line.strip()]
        if not text:
            raise ValueError("empty CSV")

        first = text[0]
        delimiter = ";" if ";" in first else ("\t" if "\t" in first else ",")
        rows = list(csv.reader(text, delimiter=delimiter))
        if not rows:
            raise ValueError("empty CSV")

        def to_float(value):
            return self._float_from_text(value)

        first_numeric = [to_float(value) for value in rows[0]]
        has_header = not any(value is not None for value in first_numeric)
        headers = rows[0] if has_header else [f"col_{i}" for i in range(len(rows[0]))]
        data_rows = rows[1:] if has_header else rows

        numeric_columns = []
        for col_index, name in enumerate(headers):
            values = []
            for row in data_rows:
                if col_index >= len(row):
                    continue
                value = to_float(row[col_index])
                if value is not None and np.isfinite(value):
                    values.append(value)
            if values:
                numeric_columns.append((str(name), values))

        if len(numeric_columns) < 2:
            raise ValueError("not enough numeric columns")
        return numeric_columns

    def _thermal_nearest_s_point(self, csv_path, target_k_m):
        columns = self._thermal_read_csv_columns(csv_path)
        normalized = {name.strip().lower().replace(" ", "").replace(",", "."): i for i, (name, _) in enumerate(columns)}

        x_idx = None
        for candidate in ("x", "k_m", "km", "k_mnearest"):
            key = candidate.strip().lower().replace(" ", "").replace(",", ".")
            if key in normalized:
                x_idx = normalized[key]
                break
        if x_idx is None:
            x_idx = 0

        s_idx = None
        for candidate in ("s", "S"):
            key = candidate.strip().lower().replace(" ", "").replace(",", ".")
            if key in normalized:
                s_idx = normalized[key]
                break
        if s_idx is None:
            s_idx = 1 if x_idx == 0 else 0

        x_values = np.asarray(columns[x_idx][1], dtype=float)
        s_values = np.asarray(columns[s_idx][1], dtype=float)
        count = min(len(x_values), len(s_values))
        if count == 0:
            raise ValueError("no numeric x/S rows")
        x_values = x_values[:count]
        s_values = s_values[:count]
        idx = int(np.argmin(np.abs(x_values - float(target_k_m))))
        return float(x_values[idx]), float(s_values[idx]), float(abs(x_values[idx] - float(target_k_m)))

    def _thermal_collect_s_values(self, target_k_m=None):
        pair_number = int(self.cbFuel.currentData() or self.model.idx or 1)
        if target_k_m is None:
            target_k_m = float(self.model.k_m)
        else:
            target_k_m = float(target_k_m)
        folders = self._thermal_find_s_folders(pair_number)
        rows = []
        for folder in folders:
            for csv_path in sorted(folder.glob("*.csv")):
                try:
                    temperature = float(csv_path.stem.replace(",", "."))
                except Exception:
                    continue
                try:
                    km_nearest, s_value, distance = self._thermal_nearest_s_point(csv_path, target_k_m)
                except Exception:
                    continue
                rows.append({
                    "T": temperature,
                    "S": s_value,
                    "file": csv_path.name,
                    "k_m_nearest": km_nearest,
                    "distance": distance,
                })
        rows.sort(key=lambda row: row["T"])
        return rows

    def _thermal_temperature_input_range(self):
        """Return the actual allowed material-temperature range for the selected pair."""
        try:
            target_k_m = self._float_from_text(self.ed_k_m.text())
            if target_k_m is None:
                target_k_m = float(self.model.k_m)
            rows = self._thermal_collect_s_values(target_k_m=target_k_m)
            temperatures = sorted({float(row["T"]) for row in rows})
            if len(temperatures) < 2:
                return None
            max_step = max(
                abs(temperatures[index + 1] - temperatures[index])
                for index in range(len(temperatures) - 1)
            )
            # The S interpolation permits extrapolation by one maximum database step.
            # The entered material temperature is 50 K above the gas-wall temperature.
            minimum = temperatures[0] - max_step + 50.0
            maximum = temperatures[-1] + max_step + 50.0
            return self.cbFuel.currentText().strip(), minimum, maximum
        except Exception:
            return None

    def _thermal_median(self, values):
        values = sorted(float(v) for v in values)
        if not values:
            raise ValueError("empty median")
        mid = len(values) // 2
        if len(values) % 2:
            return values[mid]
        return 0.5 * (values[mid - 1] + values[mid])

    def _thermal_local_slope(self, rows, side, n_points=4):
        edge_rows = rows[:min(n_points, len(rows))] if side == "lower" else rows[-min(n_points, len(rows)):]
        slopes = []
        steps = []
        for i in range(len(edge_rows) - 1):
            T1, T2 = edge_rows[i]["T"], edge_rows[i + 1]["T"]
            S1, S2 = edge_rows[i]["S"], edge_rows[i + 1]["S"]
            dT = T2 - T1
            if abs(dT) > 1e-12:
                slopes.append((S2 - S1) / dT)
                steps.append(abs(dT))
        if not slopes:
            raise ValueError("not enough S points for extrapolation")
        return self._thermal_median(slopes), sum(steps) / len(steps)

    def _thermal_interpolate_s(self, rows, target_temperature):
        rows = sorted(rows, key=lambda row: row["T"])
        if len(rows) < 2:
            pair_name = self.cbFuel.currentText().strip()
            raise ValueError(self._tr(
                f"Thermal-load calculation is unavailable for the propellant pair “{pair_name}”: "
                "the required thermodynamic-coefficient data are missing.",
                f"Расчёт тепловых нагрузок недоступен для топливной пары «{pair_name}»: "
                "отсутствуют необходимые данные термодинамического коэффициента."
            ))

        temps = [row["T"] for row in rows]
        max_step = max(abs(temps[i + 1] - temps[i]) for i in range(len(temps) - 1))
        min_T, max_T = temps[0], temps[-1]
        warning = None

        if target_temperature < min_T:
            gap = min_T - target_temperature
            warning = self._tr(
                f"T_gas_wall is below the available S database range ({min_T:g}...{max_T:g} K).",
                f"T_gas_wall ниже доступного диапазона базы S ({min_T:g}...{max_T:g} К)."
            )
            if gap > max_step:
                raise ValueError(warning)
            slope, step = self._thermal_local_slope(rows, "lower")
            T1 = min_T - step
            S1 = rows[0]["S"] + slope * (T1 - min_T)
            T2, S2 = rows[0]["T"], rows[0]["S"]
        elif target_temperature > max_T:
            gap = target_temperature - max_T
            warning = self._tr(
                f"T_gas_wall is above the available S database range ({min_T:g}...{max_T:g} K).",
                f"T_gas_wall выше доступного диапазона базы S ({min_T:g}...{max_T:g} К)."
            )
            if gap > max_step:
                raise ValueError(warning)
            slope, step = self._thermal_local_slope(rows, "upper")
            T1, S1 = rows[-1]["T"], rows[-1]["S"]
            T2 = max_T + step
            S2 = rows[-1]["S"] + slope * (T2 - max_T)
        else:
            for row in rows:
                if abs(row["T"] - target_temperature) < 1e-9:
                    return row["S"], warning
            T1 = S1 = T2 = S2 = None
            for i in range(len(rows) - 1):
                if rows[i]["T"] <= target_temperature <= rows[i + 1]["T"]:
                    T1, S1 = rows[i]["T"], rows[i]["S"]
                    T2, S2 = rows[i + 1]["T"], rows[i + 1]["S"]
                    break
            if T1 is None:
                raise ValueError("Could not choose S interpolation interval.")

        if abs(T2 - T1) < 1e-12:
            raise ValueError("Could not interpolate S: equal temperatures.")
        S_result = S2 + (S1 - S2) * (T2 - target_temperature) / (T2 - T1)
        return float(S_result), warning

    def _thermal_read_image(self, path):
        image = mpimg.imread(str(path))
        if image is None:
            raise FileNotFoundError(str(path))
        image = np.asarray(image)
        if image.ndim == 2:
            image = np.dstack([image, image, image])
        if image.shape[2] > 3:
            image = image[:, :, :3]
        if image.max() <= 1.0:
            image = image * 255.0
        return image.astype(float)

    def _thermal_group_consecutive(self, indices):
        indices = np.asarray(indices, dtype=int)
        if indices.size == 0:
            return []
        breaks = np.where(np.diff(indices) > 1)[0] + 1
        return np.split(indices, breaks)

    def _thermal_line_centers(self, scores, relative_threshold=0.35):
        if scores.size == 0 or scores.max() <= 0:
            return np.array([], dtype=int)
        indices = np.where(scores >= relative_threshold * scores.max())[0]
        groups = self._thermal_group_consecutive(indices)
        return np.array([int(round(group.mean())) for group in groups if group.size > 0], dtype=int)

    def _thermal_detect_q0_geometry(self, image):
        red = image[:, :, 0]
        green = image[:, :, 1]
        blue = image[:, :, 2]
        green_mask = (green > 80) & (green > red * 1.35) & (green > blue * 1.35)
        x_lines = self._thermal_line_centers(green_mask.sum(axis=0))
        y_lines = self._thermal_line_centers(green_mask.sum(axis=1))
        if x_lines.size < 3 or y_lines.size < 2:
            raise RuntimeError("Could not detect q0 graph grid.")
        x_left, x_right = int(x_lines.min()), int(x_lines.max())
        y_top, y_bottom = int(y_lines.min()), int(y_lines.max())
        x_middle = 0.5 * (x_left + x_right)
        x_throat = int(x_lines[np.argmin(np.abs(x_lines - x_middle))])
        return (x_left, x_right, y_top, y_bottom, x_throat), green_mask

    def _thermal_select_curve_component(self, curve_mask):
        labels, count = ndimage.label(curve_mask)
        if count <= 0:
            raise RuntimeError("Black q0 curve was not found.")
        plot_width = curve_mask.shape[1]
        candidates = []
        objects = ndimage.find_objects(labels)
        for label, obj in enumerate(objects, start=1):
            if obj is None:
                continue
            y_slice, x_slice = obj
            width = x_slice.stop - x_slice.start
            height = y_slice.stop - y_slice.start
            area = int(np.sum(labels[obj] == label))
            if width >= max(10, int(0.08 * plot_width)) and area >= 20:
                candidates.append((width * np.sqrt(area), label))
        if not candidates:
            raise RuntimeError("Could not separate q0 curve from noise.")
        return labels == max(candidates)[1]

    def _thermal_extract_q0_curve(self, image, geometry, green_mask):
        x_left, x_right, y_top, y_bottom, _ = geometry
        crop = image[y_top:y_bottom + 1, x_left:x_right + 1]
        crop_green = green_mask[y_top:y_bottom + 1, x_left:x_right + 1]
        gray = 0.299 * crop[:, :, 0] + 0.587 * crop[:, :, 1] + 0.114 * crop[:, :, 2]
        dark_mask = (gray < 135) & (~crop_green)
        dark_mask[:3, :] = 0
        dark_mask[-3:, :] = 0
        dark_mask[:, :3] = 0
        dark_mask[:, -3:] = 0
        dark_mask = ndimage.binary_closing(dark_mask, structure=np.ones((2, 2), dtype=bool))
        curve_mask = self._thermal_select_curve_component(dark_mask)

        curve_x, curve_y = [], []
        for x_local in range(curve_mask.shape[1]):
            y_candidates = np.where(curve_mask[:, x_local])[0]
            if y_candidates.size:
                curve_x.append(x_left + x_local)
                curve_y.append(y_top + float(np.median(y_candidates)))
        if len(curve_x) < 10:
            raise RuntimeError("Too few q0 curve points were found.")
        curve_x = np.asarray(curve_x, dtype=float)
        curve_y = np.asarray(curve_y, dtype=float)
        all_x = np.arange(int(curve_x.min()), int(curve_x.max()) + 1)
        all_y = np.interp(all_x, curve_x, curve_y)
        window = min(9, len(all_y) if len(all_y) % 2 else len(all_y) - 1)
        if window >= 3:
            smooth_y = np.convolve(all_y, np.ones(window) / window, mode="same")
            edge = window // 2
            smooth_y[:edge] = all_y[:edge]
            smooth_y[-edge:] = all_y[-edge:]
        else:
            smooth_y = all_y
        return all_x.astype(float), smooth_y.astype(float)

    def _thermal_build_q0_reference(self):
        if hasattr(self, "_q0_reference_cache"):
            return self._q0_reference_cache
        csv_path = self._project_root() / "q0_digitized_reference_table.csv"
        if csv_path.exists():
            rows = []
            with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f, delimiter=";")
                fieldnames = reader.fieldnames or []

                def find_column(*prefixes):
                    for name in fieldnames:
                        normalized = str(name).strip().lower()
                        for prefix in prefixes:
                            if normalized.startswith(prefix.lower()):
                                return name
                    return None

                position_col = find_column("position")
                r_ratio_col = find_column("R_ratio")
                q0_col = find_column("q0")
                xpix_col = find_column("x_pixel_q0")
                ypix_col = find_column("y_pixel_q0")
                if not all([position_col, r_ratio_col, q0_col, xpix_col, ypix_col]):
                    rows = []
                else:
                    for row in reader:
                        try:
                            branch = str(row[position_col]).strip()
                            r_ratio = float(str(row[r_ratio_col]).replace(",", "."))
                            q0_w = float(str(row[q0_col]).replace(",", "."))
                            xpix = float(str(row[xpix_col]).replace(",", "."))
                            ypix = float(str(row[ypix_col]).replace(",", "."))
                        except Exception:
                            continue
                        if branch in ("precritical", "postcritical") and 1.0 <= r_ratio <= 2.5:
                            rows.append((branch, r_ratio, q0_w / 1.163, xpix, ypix))
            if rows:
                branch_tables = {}
                for branch in ("precritical", "postcritical"):
                    branch_rows = sorted([row for row in rows if row[0] == branch], key=lambda row: row[1])
                    if not branch_rows:
                        raise RuntimeError(f"q0 branch is empty: {branch}")
                    ratios = np.asarray([row[1] for row in branch_rows], dtype=float)
                    q0 = np.asarray([row[2] for row in branch_rows], dtype=float)
                    xpix = np.asarray([row[3] for row in branch_rows], dtype=float)
                    ypix = np.asarray([row[4] for row in branch_rows], dtype=float)
                    branch_tables[branch] = (ratios, q0, xpix, ypix)
                self._q0_reference_cache = branch_tables
                return branch_tables

        image_path = self._project_root() / "q0.png"
        image = self._thermal_read_image(image_path)
        geometry, green_mask = self._thermal_detect_q0_geometry(image)
        curve_x, curve_y = self._thermal_extract_q0_curve(image, geometry, green_mask)
        x_left, x_right, y_top, y_bottom, x_throat = geometry

        rows = []
        for x_pixel, y_pixel in zip(curve_x, curve_y):
            if abs(x_pixel - x_throat) <= 1:
                r_ratio, branch = 1.0, "critical"
            elif x_pixel < x_throat:
                r_ratio = 2.5 - (x_pixel - x_left) / (x_throat - x_left) * (2.5 - 1.0)
                branch = "precritical"
            else:
                r_ratio = 1.0 + (x_pixel - x_throat) / (x_right - x_throat) * (2.5 - 1.0)
                branch = "postcritical"
            q0_value = (y_bottom - y_pixel) / (y_bottom - y_top) * 9.0
            if 1.0 <= r_ratio <= 2.5:
                rows.append((branch, float(r_ratio), float(q0_value), float(x_pixel), float(y_pixel)))

        branch_tables = {}
        for branch in ("precritical", "postcritical"):
            branch_rows = sorted([row for row in rows if row[0] == branch], key=lambda row: row[1])
            if not branch_rows:
                raise RuntimeError(f"q0 branch is empty: {branch}")
            ratios = np.asarray([row[1] for row in branch_rows], dtype=float)
            q0 = np.asarray([row[2] for row in branch_rows], dtype=float)
            xpix = np.asarray([row[3] for row in branch_rows], dtype=float)
            ypix = np.asarray([row[4] for row in branch_rows], dtype=float)
            branch_tables[branch] = (ratios, q0, xpix, ypix)
        self._q0_reference_cache = branch_tables
        return branch_tables

    def _thermal_interp_q0(self, r_ratio, branch, branch_tables):
        if branch == "critical":
            left = self._thermal_interp_q0(1.0, "precritical", branch_tables)
            right = self._thermal_interp_q0(1.0, "postcritical", branch_tables)
            return tuple(0.5 * (left[i] + right[i]) for i in range(3))
        ratios, q0, xpix, ypix = branch_tables[branch]
        clipped = float(np.clip(r_ratio, ratios.min(), ratios.max()))
        return (
            float(np.interp(clipped, ratios, q0)),
            float(np.interp(clipped, ratios, xpix)),
            float(np.interp(clipped, ratios, ypix)),
        )

    def _thermal_branch(self, index, throat_index):
        if index < throat_index:
            return "precritical"
        if index > throat_index:
            return "postcritical"
        return "critical"

    def _thermal_q_l_coefficient(self, branch, r_ratio):
        if branch == "precritical":
            return 0.2 if r_ratio >= 1.19 else 0.05
        if branch == "critical":
            return 0.05
        return 0.02 if r_ratio <= 1.5 else 0.004

    def _thermal_style_x(self, branch, r_ratio):
        if branch == "precritical":
            return (2.5 - r_ratio) / (2.5 - 1.0)
        if branch == "critical":
            return 1.0
        return 1.0 + (r_ratio - 1.0) / (2.5 - 1.0)

    def on_calc_thermal(self):
        if self.x_curve is None or self.y_curve is None:
            QMessageBox.information(self, self._tr("Parameters required", "Сначала параметры"),
                                    self._tr("Click 'Calculate parameters' first.",
                                             "Сначала нажмите «Рассчитать параметры»."))
            return

        T_wall_material_max = self._float_from_text(self.page_thermal.ed_T_wall_material_max.text())
        if T_wall_material_max is None:
            QMessageBox.warning(self, self._tr("Input", "Ввод"),
                                self._tr(
                                    "Enter the maximum fire-wall material temperature first.",
                                    "Введите предельно допустимую температуру материала огневой стенки."
                                ))
            return
        T_gas_wall = T_wall_material_max - 50.0

        try:
            for attr, ed in self._std_fields.items():
                val = self._v(ed)
                if val is not None:
                    setattr(self.model, attr, val)
            s_rows = self._thermal_collect_s_values()
            S_gas_wall, temp_warning = self._thermal_interpolate_s(s_rows, T_gas_wall)
            if temp_warning:
                QMessageBox.warning(self, self._tr("Temperature warning", "Предупреждение по температуре"), temp_warning)

            branch_tables = self._thermal_build_q0_reference()
            m = self.model
            x_all = np.asarray(self.x_curve, dtype=float)
            y_all = np.asarray(self.y_curve, dtype=float)
            indices = [
                i for i in range(len(x_all) - 1)
                if x_all[i] >= m.L_g + m.L_cy and y_all[i] <= 2.5 * m.R_kr
            ]
            if not indices:
                raise ValueError("No nozzle points found for thermal calculation.")

            x_nozzle = np.asarray([x_all[i] - x_all[indices[0] - 1] for i in indices], dtype=float)
            y_nozzle = np.asarray([y_all[i] for i in indices], dtype=float)
            R_ratio = y_nozzle / float(m.R_kr)
            throat_index = int(np.argmin(y_nozzle))
            branch_by_index = []
            for idx in range(len(R_ratio)):
                if idx < throat_index:
                    branch_by_index.append("precritical")
                elif idx == throat_index:
                    branch_by_index.append("critical")
                else:
                    branch_by_index.append("postcritical")

            p_ko, R_kro, So = 4.0, 54.5, 0.94
            kcal_h_to_w = 1.163
            all_rows = []
            for i, r_ratio in enumerate(R_ratio):
                branch = branch_by_index[i]
                q0_value, xpix, ypix = self._thermal_interp_q0(float(r_ratio), branch, branch_tables)
                q0_value_W_m2 = q0_value * kcal_h_to_w
                q_k_raw = q0_value * (float(m.p_k) / p_ko) ** 0.87 * (R_kro / float(m.R_kr)) ** 0.13 * (S_gas_wall / So)
                q_k = q_k_raw * kcal_h_to_w
                q_l_coeff = self._thermal_q_l_coefficient(branch, float(r_ratio))
                q_l = q_k * q_l_coeff
                q_sum = q_k + q_l
                all_rows.append({
                    "i": i + 1,
                    "x": float(x_nozzle[i]),
                    "y": float(y_nozzle[i]),
                    "R_ratio_geometry": float(r_ratio),
                    "position": branch,
                    "q0": q0_value,
                    "q0_recognized_W_m2": q0_value_W_m2,
                    "q_k_W_m2": q_k,
                    "q_l_W_m2": q_l,
                    "q_sum_W_m2": q_sum,
                    "q_l_coefficient": q_l_coeff,
                    "x_pixel_q0": xpix,
                    "y_pixel_q0": ypix,
                    "q0_style_x": self._thermal_style_x(branch, float(r_ratio)),
                })

            required_r_ratio_points = [
                ("precritical", 2.0),
                ("precritical", 1.8),
                ("precritical", 1.5),
                ("precritical", 1.2),
                ("critical", 1.0),
                ("postcritical", 1.2),
                ("postcritical", 1.5),
                ("postcritical", 2.0),
                ("postcritical", 2.5),
            ]

            def select_required_row(required_branch, target_r_ratio):
                if required_branch == "critical":
                    candidates = list(all_rows)
                else:
                    candidates = [row for row in all_rows if row["position"] == required_branch]
                if not candidates:
                    raise ValueError(f"No thermal points found for {required_branch}.")

                target = float(target_r_ratio)
                candidates = sorted(
                    candidates,
                    key=lambda row: (abs(row["R_ratio_geometry"] - target), row["i"]),
                )
                selected = dict(candidates[0])
                selected["required_position"] = required_branch
                selected["required_R_ratio"] = target
                selected["distance_to_required_R_ratio"] = abs(selected["R_ratio_geometry"] - target)
                return selected

            rows = []
            for required_branch, target_r_ratio in required_r_ratio_points:
                rows.append(select_required_row(required_branch, target_r_ratio))

            rows.sort(key=lambda row: row["q0_style_x"])
            cumulative = 0.0
            for i, row in enumerate(rows):
                if i == 0:
                    segment_area = 0.0
                    q_loss_segment = 0.0
                else:
                    prev = rows[i - 1]
                    segment_length_mm = ((row["x"] - prev["x"]) ** 2 + (row["y"] - prev["y"]) ** 2) ** 0.5
                    segment_area = np.pi * (row["y"] + prev["y"]) * segment_length_mm * 1e-6
                    q_mean = 0.5 * (row["q_sum_W_m2"] + prev["q_sum_W_m2"])
                    q_loss_segment = q_mean * segment_area
                cumulative += q_loss_segment
                row["Q_loss_segment_W"] = float(q_loss_segment)
                row["Q_loss_cumulative_W"] = float(cumulative)

            x_plot = np.asarray([row["q0_style_x"] for row in rows], dtype=float)
            self.page_thermal.plot.draw_lines(
                x_plot,
                [
                    ([row["q_k_W_m2"] for row in rows], "q_k"),
                    ([row["q_l_W_m2"] for row in rows], "q_l"),
                    ([row["q_sum_W_m2"] for row in rows], "q_sum"),
                ],
                xlabel="R/Rkr",
                ylabel="q [W/m^2]",
            )
            self.page_thermal.set_results(T_gas_wall, S_gas_wall, cumulative, rows)
            self._goto(5, self.btn_page_thermal)
            self.statusbar.showMessage(self._tr("Thermal-load calculation completed.", "Расчёт тепловых нагрузок выполнен."), 3000)
        except Exception as e:
            self.page_thermal.clear_results()
            QMessageBox.critical(self, self._tr("Thermal loads", "Тепловые нагрузки"), str(e))

    # Notebook-based thermal calculation.  This definition intentionally
    # replaces the former image-recognition implementation above.
    def on_calc_thermal(self):
        if self.x_curve is None or self.y_curve is None:
            QMessageBox.information(self, self._tr("Parameters required", "Сначала параметры"),
                                    self._tr("Click 'Calculate parameters' first.", "Сначала нажмите «Рассчитать параметры»."))
            return
        try:
            T_wall_material_max = self._float_from_text(self.page_thermal.ed_T_wall_material_max.text())
            if T_wall_material_max is None:
                raise ValueError(self._tr(
                    "Enter the maximum fire-wall material temperature.",
                    "Введите предельно допустимую температуру материала огневой стенки."
                ))
            T_gas_wall = T_wall_material_max - 50.0
            s_rows = self._thermal_collect_s_values()
            S_gas_wall, warning = self._thermal_interpolate_s(s_rows, T_gas_wall)

            p_ko, R_kro, So = 4.0, 54.5, 0.94
            R_ratio = np.asarray([2.0, 1.8, 1.5, 1.2, 1.0, 1.2, 1.5, 2.0, 2.5], dtype=float)
            position = np.asarray(["precritical"] * 4 + ["critical"] + ["postcritical"] * 4)
            q0 = np.asarray([2.557818, 3.058926, 4.212965, 6.465726, 8.359121,
                             5.629543, 3.150297, 1.510920, 1.070033], dtype=float) * 1.163

            exit_ratio = float(self.model.R_a / self.model.R_kr)
            index_edge = 5
            for index in range(5, len(R_ratio)):
                if exit_ratio >= R_ratio[index]:
                    index_edge = index + 1
            R_ratio, position, q0 = R_ratio[:index_edge], position[:index_edge], q0[:index_edge]
            radii = R_ratio * float(self.model.R_kr)
            x_arr = np.asarray(self.x_curve, dtype=float)
            y_arr = np.asarray(self.y_curve, dtype=float)
            x_vh = self.model.L_g + self.model.L_cy
            x_kr = self.model.L_g + self.model.L_cy + self.model.L_vh
            x_dv = self.model.L_g + self.model.L_cy + self.model.L_vh + self.model.L_c
            index_vh = int(np.argmin(np.abs(x_arr - x_vh)))
            index_kr = int(np.argmin(np.abs(x_arr - x_kr)))
            index_dv = int(np.argmin(np.abs(x_arr - x_dv)))

            def find_two_points(radius, branch):
                if branch == "precritical":
                    # The first notebook reference point R/Rkr=2 is the
                    # entrance to the convergent section, x_vh=L_g+L_cy.
                    if np.isclose(radius, radii[0]):
                        return (float(x_vh), index_vh, float(x_vh), float(radius),
                                index_vh, float(x_vh), float(radius))
                    indexes = range(index_vh, index_kr)
                elif branch == "critical":
                    return (float(x_arr[index_kr]), index_kr, float(x_arr[index_kr]),
                            float(y_arr[index_kr]), index_kr, float(x_arr[index_kr]), float(y_arr[index_kr]))
                elif branch == "postcritical":
                    indexes = range(index_kr, index_dv)
                else:
                    raise ValueError(f"Unknown nozzle branch: {branch}")

                for i in indexes:
                    if min(y_arr[i], y_arr[i + 1]) <= radius <= max(y_arr[i], y_arr[i + 1]):
                        i1, i2 = i, i + 1
                        x1, x2 = float(x_arr[i1]), float(x_arr[i2])
                        R1, R2 = float(y_arr[i1]), float(y_arr[i2])
                        x_radius = 0.5 * (x1 + x2)
                        if not np.isclose(R1, R2):
                            if branch == "precritical":
                                x_radius = x2 - (radius - R2) * (x2 - x1) / (R1 - R2)
                            else:
                                x_radius = x1 + (radius - R1) * (x2 - x1) / (R2 - R1)
                        return float(x_radius), i1, x1, R1, i2, x2, R2
                raise ValueError(f"Radius R={radius:g} mm was not found on the {branch} contour.")

            x_ratio = [find_two_points(radii[i], position[i])[0] for i in range(index_edge)]

            def area_between_points(index):
                if index == 0:
                    return 0.0
                x_radius, _, _, _, i2, x2, R2 = find_two_points(radii[index - 1], position[index - 1])
                area = np.pi * (radii[index - 1] + R2) * np.hypot(x2 - x_radius, R2 - radii[index - 1])
                i_begin = i2
                x_radius, i1, x1, R1, _, _, _ = find_two_points(radii[index], position[index])
                area += np.pi * (R1 + radii[index]) * np.hypot(x_radius - x1, radii[index] - R1)
                i_end = i1
                for i in range(i_begin, i_end):
                    area += np.pi * (y_arr[i] + y_arr[i + 1]) * np.hypot(
                        x_arr[i + 1] - x_arr[i], y_arr[i + 1] - y_arr[i]
                    )
                return float(area * 1e-6)

            S_ratio = [area_between_points(i) for i in range(index_edge)]

            q_k = q0 * (float(self.model.p_k) / p_ko) ** 0.87 * (R_kro / float(self.model.R_kr)) ** 0.13 * (S_gas_wall / So)
            q_l_coef = np.asarray([
                0.2 if branch == "precritical" and ratio >= 1.19 else
                0.05 if branch in ("precritical", "critical") else
                0.02 if ratio <= 1.5 else 0.004
                for branch, ratio in zip(position, R_ratio)
            ])
            q_l = q_k * q_l_coef
            q_sum = q_k + q_l

            Q_loss = [0.0]
            for index in range(1, index_edge):
                Q_loss.append(float(0.5 * (q_sum[index - 1] + q_sum[index]) * S_ratio[index]))
            Q_loss_cumulative = np.cumsum(Q_loss).astype(float)
            Q = float(Q_loss_cumulative[-1])
            display_position = [
                "convergent" if branch == "precritical" else
                "throat" if branch == "critical" else "divergent"
                for branch in position
            ]

            heat_load_table = pd.DataFrame({
                "R/R_t [-]": R_ratio,
                "Nozzle section": display_position,
                "x [mm]": x_ratio[:index_edge],
                "q_0 [W/m^2]": q0,
                "q_k [W/m^2]": q_k,
                "q_l [W/m^2]": q_l,
                "q_sum [W/m^2]": q_sum,
                "dA_wall [m^2]": S_ratio,
                "dQ [W]": Q_loss,
                "Q_cum [W]": Q_loss_cumulative,
            }).round({"R/R_t [-]": 5, "x [mm]": 6, "q_0 [W/m^2]": 6,
                      "q_k [W/m^2]": 6, "q_l [W/m^2]": 6, "q_sum [W/m^2]": 6,
                      "dA_wall [m^2]": 9, "dQ [W]": 9, "Q_cum [W]": 9})

            self.T_wall_material_max = T_wall_material_max
            self.T_gas_wall, self.S_gas_wall, self.Q = T_gas_wall, S_gas_wall, Q
            self.heat_load_table = heat_load_table
            self.page_thermal.set_language(self._tr)
            x_heat = np.asarray(x_ratio[:index_edge], dtype=float)
            x_min = float(np.nanmin(x_heat))
            x_max = float(np.nanmax(x_heat))
            xlim = (x_min, x_max)
            self.page_thermal.plot.draw_lines(
                x_heat,
                [(q_k, "q_k"), (q_l, "q_l"), (q_sum, "q_sum")],
                xlabel=self._tr("x [mm]", "x [\u043c\u043c]"),
                ylabel=self._tr("q [W/m^2]", "q [\u0412\u0442/\u043c^2]"),
                xlim=xlim,
                vlines=x_heat
            )
            contour_x, contour_y = self._crop_curve_by_x_range(x_arr, y_arr, x_min, x_max)
            self.page_thermal.contour_plot.draw_upper_contour(
                contour_x,
                contour_y,
                points=(x_heat, radii[:index_edge]),
                xlabel=self._tr("x [mm]", "x [\u043c\u043c]"),
                ylabel=self._tr("R [mm]", "R [\u043c\u043c]"),
                line_label=self._tr("nozzle contour", "\u043a\u043e\u043d\u0442\u0443\u0440 \u0441\u043e\u043f\u043b\u0430"),
                points_label=self._tr("thermal points", "\u0442\u043e\u0447\u043a\u0438 \u0442\u0435\u043f\u043b\u043e\u0432\u043e\u0433\u043e \u0440\u0430\u0441\u0447\u0435\u0442\u0430"),
                xlim=xlim,
                vlines=x_heat
            )
            self.page_thermal.set_results(T_gas_wall, S_gas_wall, Q, heat_load_table)
            self._goto(5, self.btn_page_thermal)
            message = self._tr("Thermal-load calculation completed.", "Расчёт тепловых нагрузок выполнен.")
            if warning:
                message += " " + str(warning)
            self.statusbar.showMessage(message, 5000)
        except Exception as error:
            self.page_thermal.clear_results()
            QMessageBox.critical(self, self._tr("Thermal loads", "Тепловые нагрузки"), str(error))

    def _find_file(self, folder, base, exts):
        for ext in exts:
            p = os.path.join(folder, f"{base}.{ext}")
            if os.path.isfile(p):
                return p
        return None

    def _read_vector(self, path):
        try:
            if path.lower().endswith(".csv"):
                try:
                    data = np.loadtxt(path, delimiter=" ", dtype=float, ndmin=1, comments=None, skiprows=1)
                    if data.size == 0:
                        data = np.loadtxt(path, delimiter=" ", dtype=float, ndmin=1, comments=None, skiprows=0)
                except Exception:
                    data = np.loadtxt(path, delimiter=" ", dtype=float, ndmin=1, comments=None, skiprows=0)
            else:
                data = np.loadtxt(path, dtype=float, ndmin=1, comments=None)
            return np.asarray(data, dtype=float)
        except Exception as e:
            raise RuntimeError(self._tr(f"Error reading {os.path.basename(path)}: {e}",
                                        f"Ошибка чтения {os.path.basename(path)}: {e}"))

    def _read_xy(self, path):
        try:
            if path.lower().endswith(".csv"):
                data = None
                for delimiter in (";", ",", " "):
                    try:
                        data = np.loadtxt(
                            path, delimiter=delimiter, dtype=float, ndmin=2,
                            comments=None, skiprows=1
                        )
                        break
                    except Exception:
                        data = None
                if data is None:
                    data = np.loadtxt(
                        path, dtype=float, ndmin=2,
                        comments=None, skiprows=1
                    )
            else:
                data = np.loadtxt(
                    path, dtype=float, ndmin=2,
                    comments=None
                )
            data = np.asarray(data, dtype=float)
            if data.ndim != 2 or data.shape[1] < 2:
                raise RuntimeError(self._tr("Two columns, x and y, were expected",
                                            "Ожидались два столбца x и y"))
            x_arr = data[:, 0]
            y_arr = data[:, 1]
            return x_arr, y_arr
        except Exception as e:
            raise RuntimeError(self._tr(f"Error reading {os.path.basename(path)}: {e}",
                                        f"Ошибка чтения {os.path.basename(path)}: {e}"))

    def _read_thermal_table(self, folder):
        csv_path = self._find_file(folder, "thermal_calculation", ["csv"])
        xlsx_path = self._find_file(folder, "thermal_calculation", ["xlsx"])
        if csv_path:
            return pd.read_csv(csv_path, sep=";", decimal=",", encoding="utf-8-sig")
        if xlsx_path:
            return pd.read_excel(xlsx_path, header=None)
        return None

    def _restore_thermal_results_from_folder(self, folder):
        table = self._read_thermal_table(folder)
        if table is None:
            return False

        required = ["x [mm]", "R/R_t [-]", "q_k [W/m^2]", "q_l [W/m^2]", "q_sum [W/m^2]"]
        if not all(name in table.columns for name in required):
            return False

        table = table.copy()
        numeric_columns = [
            "R/R_t [-]", "x [mm]", "q_0 [W/m^2]", "q_k [W/m^2]",
            "q_l [W/m^2]", "q_sum [W/m^2]", "dA_wall [m^2]",
            "dQ [W]", "Q_cum [W]"
        ]
        for column in numeric_columns:
            if column in table.columns:
                table[column] = pd.to_numeric(table[column], errors="coerce")

        self.heat_load_table = table
        self.Q = float(table["Q_cum [W]"].dropna().iloc[-1]) if "Q_cum [W]" in table.columns and not table["Q_cum [W]"].dropna().empty else None

        T_wall = None
        try:
            T_wall = self._float_from_text(self.page_thermal.ed_T_wall_material_max.text())
        except Exception:
            T_wall = None
        self.T_wall_material_max = T_wall
        self.T_gas_wall = T_wall - 50.0 if T_wall is not None else getattr(self.page_thermal, "_last_gas_wall_temperature", None)
        self.S_gas_wall = getattr(self.page_thermal, "_last_s_value", None)
        if self.T_gas_wall is not None and self.S_gas_wall is None:
            try:
                self.S_gas_wall, _ = self._thermal_interpolate_s(self._thermal_collect_s_values(), self.T_gas_wall)
            except Exception:
                self.S_gas_wall = None

        x_heat = np.asarray(table["x [mm]"], dtype=float)
        q_k = np.asarray(table["q_k [W/m^2]"], dtype=float)
        q_l = np.asarray(table["q_l [W/m^2]"], dtype=float)
        q_sum = np.asarray(table["q_sum [W/m^2]"], dtype=float)
        x_min = float(np.nanmin(x_heat))
        x_max = float(np.nanmax(x_heat))
        xlim = (x_min, x_max)

        self.page_thermal.set_language(self._tr)
        self.page_thermal.plot.draw_lines(
            x_heat,
            [(q_k, "q_k"), (q_l, "q_l"), (q_sum, "q_sum")],
            xlabel=self._tr("x [mm]", "x [\u043c\u043c]"),
            ylabel=self._tr("q [W/m^2]", "q [\u0412\u0442/\u043c^2]"),
            xlim=xlim,
            vlines=x_heat
        )

        if self.x_curve is not None and self.y_curve is not None and getattr(self.model, "R_kr", None):
            x_arr = np.asarray(self.x_curve, dtype=float)
            y_arr = np.asarray(self.y_curve, dtype=float)
            contour_x, contour_y = self._crop_curve_by_x_range(x_arr, y_arr, x_min, x_max)
            radii = np.asarray(table["R/R_t [-]"], dtype=float) * float(self.model.R_kr)
            self.page_thermal.contour_plot.draw_upper_contour(
                contour_x,
                contour_y,
                points=(x_heat, radii),
                xlabel=self._tr("x [mm]", "x [\u043c\u043c]"),
                ylabel=self._tr("R [mm]", "R [\u043c\u043c]"),
                line_label=self._tr("nozzle contour", "\u043a\u043e\u043d\u0442\u0443\u0440 \u0441\u043e\u043f\u043b\u0430"),
                points_label=self._tr("thermal points", "\u0442\u043e\u0447\u043a\u0438 \u0442\u0435\u043f\u043b\u043e\u0432\u043e\u0433\u043e \u0440\u0430\u0441\u0447\u0435\u0442\u0430"),
                xlim=xlim,
                vlines=x_heat
            )

        self.page_thermal.set_results(
            self.T_gas_wall if self.T_gas_wall is not None else 0.0,
            self.S_gas_wall if self.S_gas_wall is not None else 0.0,
            self.Q if self.Q is not None else 0.0,
            table
        )
        return True

    def _read_params(self, folder):
        p_txt = self._find_file(folder, "params", ["txt"])
        p_csv = self._find_file(folder, "params", ["csv"])
        if not p_txt and not p_csv:
            return self._read_params_from_report(folder)

        params = {}
        try:
            if p_csv:
                import csv
                with open(p_csv, "r", encoding="utf-8") as f:
                    r = csv.reader(f)
                    header = next(r, None)
                    for row in r:
                        if not row or len(row) < 2:
                            continue
                        params[str(row[0]).strip()] = str(row[1]).strip()
            else:
                with open(p_txt, "r", encoding="utf-8") as f:
                    for line in f:
                        if not line.strip():
                            continue
                        parts = line.rstrip("\n").split("\t", 1)
                        if len(parts) == 2:
                            k, v = parts[0].strip(), parts[1].strip()
                            params[k] = v
        except Exception as e:
            raise RuntimeError(self._tr(f"Error reading params: {e}", f"Ошибка чтения params: {e}"))

        return params

    def _read_params_from_report(self, folder):
        path = self._find_file(folder, "report", ["txt"])
        if not path:
            return {}

        params = {}
        begin = "LRE_NOZZLE_DESIGNER_PARAMS_BEGIN"
        end = "LRE_NOZZLE_DESIGNER_PARAMS_END"
        in_block = False

        try:
            with open(path, "r", encoding="utf-8") as f:
                for raw_line in f:
                    line = raw_line.strip()
                    if line.startswith("#"):
                        line = line[1:].strip()

                    if line == begin:
                        in_block = True
                        continue
                    if line == end:
                        break
                    if not in_block or not line:
                        continue

                    if "\t" in line:
                        key, value = line.split("\t", 1)
                    elif "=" in line:
                        key, value = line.split("=", 1)
                    else:
                        continue
                    params[key.strip()] = value.strip()
        except Exception as e:
            raise RuntimeError(self._tr(f"Error reading report parameters: {e}",
                                        f"РћС€РёР±РєР° С‡С‚РµРЅРёСЏ РїР°СЂР°РјРµС‚СЂРѕРІ report: {e}"))

        return params

    def _set_if_present(self, edit: QLineEdit, value):
        if value is None or value == "":
            return
        edit.blockSignals(True)
        edit.setText(str(value))
        edit.blockSignals(False)

    def on_load_autofill(self):
        folder = QFileDialog.getExistingDirectory(
            self, self._tr("Select a folder containing saved files", "Выберите папку с сохраненными файлами"))
        if not folder:
            return

        try:
            params = self._read_params(folder)

            fuel_name = params.get("fuel_name")
            fuel_idx = params.get("fuel_index")
            if fuel_idx is not None and str(fuel_idx).strip() != "":
                try:
                    fuel_idx_int = int(float(fuel_idx))
                    for i in range(self.cbFuel.count()):
                        if int(self.cbFuel.itemData(i)) == fuel_idx_int:
                            self.cbFuel.setCurrentIndex(i)
                            break
                except Exception:
                    pass
            elif fuel_name:
                for i in range(self.cbFuel.count()):
                    if self.cbFuel.itemText(i).strip().endswith(fuel_name.strip()):
                        self.cbFuel.setCurrentIndex(i);
                        break
            self.on_change()

            old_thrust_type = params.get("thrust_type")
            calc_mode = params.get("calc_mode")
            if calc_mode not in ("sea_level", "altitude", "vacuum"):
                calc_mode = "vacuum" if params.get("thrust_source", old_thrust_type) == "vacuum" else "sea_level"
            mode_idx = 1 if calc_mode == "vacuum" else 0
            self.cb_calc_mode.setCurrentIndex(mode_idx)

            def gi(key):
                s = params.get(key);
                return None if s in (None, "") else float(s.replace(",", "."))

            self._set_if_present(self.ed_p_k, params.get("p_k_MPa"))
            self._set_if_present(self.ed_P_0, params.get("P_0_N") or params.get("P_calc_N") or params.get("P_h_N"))
            self._set_if_present(self.ed_P_8, params.get("P_8_N"))
            self._thrust_source = "P_8" if mode_idx == 1 else "P_0"
            self.ed_z_k.setText("1")
            self._set_if_present(self.ed_T_k, params.get("T_k_K"))
            self._set_if_present(self.ed_p_a, params.get("p_e_MPa") or params.get("p_a_MPa"))

            self.on_calc_params()

            try:
                x, y, X, Y = self.model.take_x_y()
                self.page_geom.draw_geometry(self.model, x, y, X, Y)
            except Exception:
                pass

            # Сначала пробуем новый формат: один файл xyz.*, затем старый xy.*
            path_xy = self._find_file(folder, "xyz", ["csv", "txt"])
            if not path_xy:
                path_xy = self._find_file(folder, "xy", ["csv", "txt"])

            if path_xy:
                x_arr, y_arr = self._read_xy(path_xy)
                if x_arr.size >= 2 and x_arr.size == y_arr.size:
                    self.x_curve = np.asarray(x_arr, dtype=float)
                    self.y_curve = np.asarray(y_arr, dtype=float)
                    try:
                        x, y, X, Y = self.model.take_x_y()
                        self.page_geom.draw_geometry(self.model, x, y, X, Y)
                    except Exception:
                        pass
            else:
                # старый формат на всякий случай оставим
                path_x = self._find_file(folder, "x", ["csv", "txt"])
                path_y = self._find_file(folder, "y", ["csv", "txt"])
                if path_x and path_y:
                    x_arr = self._read_vector(path_x)
                    y_arr = self._read_vector(path_y)
                    if x_arr.size == y_arr.size and x_arr.size >= 2:
                        self.x_curve = np.asarray(x_arr, dtype=float)
                        self.y_curve = np.asarray(y_arr, dtype=float)
                        try:
                            x, y, X, Y = self.model.take_x_y()
                            self.page_geom.draw_geometry(self.model, x, y, X, Y)
                        except Exception:
                            pass

            path_M = self._find_file(folder, "M", ["csv", "txt"])
            path_T = self._find_file(folder, "T", ["csv", "txt"])
            path_P = self._find_file(folder, "P", ["csv", "txt"])

            drew = False
            if path_M and (self.x_curve is not None) and (self.y_curve is not None):
                self.M = self._read_vector(path_M)
                if self.M.size == self.x_curve.size:
                    self.page_M.draw_fill(self.x_curve, self.y_curve, self.M, y0=0.0, cmap="turbo", refine=4,
                                          clabel="M")
                    self.page_M.btn_calc.setEnabled(True)
                    drew = True

            if path_T and (self.x_curve is not None) and (self.y_curve is not None):
                self.T = self._read_vector(path_T)
                if self.T.size == self.x_curve.size:
                    self.page_T.draw_fill(self.x_curve, self.y_curve, self.T, y0=0.0, cmap="turbo", refine=4,
                                          clabel=self._tr("T, K", "T, К"))
                    self.page_T.btn_calc.setEnabled(True)
                    drew = True

            if path_P and (self.x_curve is not None) and (self.y_curve is not None):
                self.P = self._read_vector(path_P)
                if self.P.size == self.x_curve.size:
                    self.page_P.draw_fill(self.x_curve, self.y_curve, self.P, y0=0.0, cmap="turbo", refine=4,
                                          clabel=self._tr("p, MPa", "p, МПа"))
                    self.page_P.btn_calc.setEnabled(True)
                    drew = True

            thermal_restored = False
            try:
                thermal_restored = self._restore_thermal_results_from_folder(folder)
            except Exception:
                thermal_restored = False

            if thermal_restored:
                self._goto(5, self.btn_page_thermal)
            elif drew:
                if self.M is not None and self.x_curve is not None and self.M.size == self.x_curve.size:
                    self._goto(2, self.btn_page_M)
                elif self.T is not None:
                    self._goto(3, self.btn_page_T)
                elif self.P is not None:
                    self._goto(4, self.btn_page_P)
            else:
                self._goto(1, self.btn_page_main)

            QMessageBox.information(self, self._tr("Done", "Готово"),
                                    self._tr("Parameters and data loaded.", "Параметры и данные загружены."))

            self.ed_p_a.setReadOnly(False)
            self.ed_p_a.setEnabled(True)
            self.ed_p_a.setFocusPolicy(Qt.StrongFocus)
            self._set_pa_validator(self.min_pa if self.min_pa is not None else 0.0)

            self._overridden.discard("p_a")
            self.timer.start()

        except Exception as e:
            QMessageBox.critical(self, self._tr("Auto-fill", "Автозаполнение"),
                                 self._tr(f"Could not load data:\n{e}", f"Не удалось загрузить данные:\n{e}"))

    # ---------- Сохранение результатов ----------
    def on_save_results(self):
        def fmt_ru(val):
            if val is None:
                return ""
            if isinstance(val, (int, float, np.integer, np.floating)):
                return f"{float(val):.9g}".replace(".", ",")
            return str(val).replace(".", ",")

        if self.x_curve is None or self.y_curve is None:
            QMessageBox.warning(
                self, self._tr("No data", "Нет данных"),
                self._tr("No calculated nozzle contour (x and y) is available.\n"
                         "Click 'Calculate parameters' first.",
                         "Нет рассчитанного контура сопла (x и y).\n"
                         "Сначала нажмите «Рассчитать параметры».")
            )
            return

        have_M = self.M is not None and len(self.M) == len(self.x_curve)
        have_T = self.T is not None and len(self.T) == len(self.x_curve)
        have_P = self.P is not None and len(self.P) == len(self.x_curve)
        thermal_table = getattr(self, "heat_load_table", None)
        if thermal_table is None and hasattr(self, "page_thermal"):
            thermal_table = getattr(self.page_thermal, "_last_table_frame", None)
        if thermal_table is not None:
            self.heat_load_table = thermal_table

        if getattr(self, "T_wall_material_max", None) is None and hasattr(self, "page_thermal"):
            self.T_wall_material_max = getattr(self.page_thermal, "_last_max_temperature", None)
        if getattr(self, "T_gas_wall", None) is None and hasattr(self, "page_thermal"):
            self.T_gas_wall = getattr(self.page_thermal, "_last_gas_wall_temperature", None)
        if getattr(self, "S_gas_wall", None) is None and hasattr(self, "page_thermal"):
            self.S_gas_wall = getattr(self.page_thermal, "_last_s_value", None)
        if getattr(self, "Q", None) is None and hasattr(self, "page_thermal"):
            self.Q = getattr(self.page_thermal, "_last_q_value", None)

        have_thermal = (
            getattr(self, "heat_load_table", None) is not None
            and len(getattr(self, "heat_load_table")) > 0
            and getattr(self, "T_gas_wall", None) is not None
            and getattr(self, "S_gas_wall", None) is not None
            and getattr(self, "Q", None) is not None
        )

        base_dir = QFileDialog.getExistingDirectory(
            self, self._tr("Select a location for the new folder", "Выберите место для новой папки"))
        if not base_dir:
            return

        default_name = "LRE_results_" + datetime.now().strftime("%Y%m%d_%H%M%S")
        folder_name, ok = QInputDialog.getText(
            self, self._tr("Folder name", "Имя папки"), self._tr("Enter a new folder name:", "Введите имя новой папки:"),
            QLineEdit.Normal, default_name
        )
        if not ok or not folder_name.strip():
            return

        target_dir = os.path.join(base_dir, folder_name.strip())

        try:
            os.makedirs(target_dir, exist_ok=False)
        except FileExistsError:
            reply = QMessageBox.question(
                self, self._tr("Folder already exists", "Папка уже существует"),
                self._tr(f"The folder '{folder_name}' already exists.\nOverwrite the files?",
                         f"Папка «{folder_name}» уже существует.\nСохранить файлы с перезаписью?"),
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return

        fmt_items = [
            "TXT (xyz.txt, M.txt, T.txt, P.txt, report.txt)",
            "CSV (xyz.csv, M.csv, T.csv, P.csv, report.txt)"
        ]
        dlg = QDialog(self)
        dlg.setWindowTitle(self._tr("File Format", "Формат файлов"))

        layout = QVBoxLayout(dlg)

        label = QLabel(self._tr("Select a save format:", "Выберите формат сохранения:"))
        layout.addWidget(label)

        combo = QComboBox()
        combo.addItems(fmt_items)
        combo.setView(QListView())
        combo.setMinimumHeight(28)
        layout.addWidget(combo)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        layout.addWidget(buttons)

        if dlg.exec_() != QDialog.Accepted:
            return

        choice = combo.currentText()
        if not ok:
            return

        files_saved = []

        try:
            if choice.startswith("TXT"):
                xyz = np.column_stack([
                    np.asarray(self.x_curve, dtype=float),
                    np.asarray(self.y_curve, dtype=float),
                    np.zeros(len(self.x_curve), dtype=float)
                ])
                np.savetxt(
                    os.path.join(target_dir, "xyz.txt"),
                    xyz, fmt="%.9g"  # по умолчанию разделитель — пробел
                )
                files_saved.append("xyz.txt")

                if have_M:
                    np.savetxt(os.path.join(target_dir, "M.txt"),
                               np.asarray(self.M, dtype=float), fmt="%.9g")
                    files_saved.append("M.txt")
                if have_T:
                    np.savetxt(os.path.join(target_dir, "T.txt"),
                               np.asarray(self.T, dtype=float), fmt="%.9g")
                    files_saved.append("T.txt")
                if have_P:
                    np.savetxt(os.path.join(target_dir, "P.txt"),
                               np.asarray(self.P, dtype=float), fmt="%.9g")
                    files_saved.append("P.txt")

                # with open(os.path.join(target_dir, "report.txt"), "w", encoding="utf-8") as f:
                #     f.write(self._report_text())
                # files_saved.append("report.txt")


            else:
                xyz = np.column_stack([
                    np.asarray(self.x_curve, dtype=float),
                    np.asarray(self.y_curve, dtype=float),
                    np.zeros(len(self.x_curve), dtype=float)
                ])
                np.savetxt(
                    os.path.join(target_dir, "xyz.csv"),
                    xyz,
                    fmt="%.9g",
                    delimiter=";",
                    header="x;y;z",
                    comments=""
                )

                files_saved.append("xyz.csv")

                if have_M:
                    np.savetxt(os.path.join(target_dir, "M.csv"),
                               np.asarray(self.M, dtype=float),
                               fmt="%.9g", delimiter=",", header="M", comments="")
                    files_saved.append("M.csv")
                if have_T:
                    np.savetxt(os.path.join(target_dir, "T.csv"),
                               np.asarray(self.T, dtype=float),
                               fmt="%.9g", delimiter=",", header="T", comments="")
                    files_saved.append("T.csv")
                if have_P:
                    np.savetxt(os.path.join(target_dir, "P.csv"),
                               np.asarray(self.P, dtype=float),
                               fmt="%.9g", delimiter=",", header="P", comments="")
                    files_saved.append("P.csv")

            # with open(os.path.join(target_dir, "results_table.csv"), "w",
            #           newline="", encoding="utf-8-sig") as f:
            #     w = csv.writer(f, delimiter=";")
            #     w.writerow(["Параметр", "Значение", "Единица"])
            #     for key, value, unit in self._collect_results_table():
            #         w.writerow([key, fmt_ru(value), unit])
            # files_saved.append("results_table.csv")

            with open(os.path.join(target_dir, "report.txt"), "w", encoding="utf-8") as f:
                f.write(self._report_text_for_save())
            files_saved.append("report.txt")

            try:
                xg, yg, Xg, Yg = self.model.take_x_y()
                self.page_geom.draw_geometry(self.model, xg, yg, Xg, Yg)
                self.page_geom.plot.fig.savefig(
                    os.path.join(target_dir, "geometry.png"),
                    dpi=200, bbox_inches="tight"
                )
                files_saved.append("geometry.png")
            except Exception:
                pass

            try:
                if have_M:
                    self.page_M.draw_fill(self.x_curve, self.y_curve, self.M,
                                          y0=0.0, cmap="turbo", refine=4, clabel="M")
                    self.page_M.plot.fig.savefig(
                        os.path.join(target_dir, "M.png"),
                        dpi=200, bbox_inches="tight"
                    )
                    files_saved.append("M.png")
            except Exception:
                pass

            try:
                if have_T:
                    self.page_T.draw_fill(self.x_curve, self.y_curve, self.T,
                                          y0=0.0, cmap="turbo", refine=4, clabel=self._tr("T, K", "T, К"))
                    self.page_T.plot.fig.savefig(
                        os.path.join(target_dir, "T.png"),
                        dpi=200, bbox_inches="tight"
                    )
                    files_saved.append("T.png")
            except Exception:
                pass

            try:
                if have_P:
                    self.page_P.draw_fill(self.x_curve, self.y_curve, self.P,
                                          y0=0.0, cmap="turbo", refine=4, clabel=self._tr("p, MPa", "p, МПа"))
                    self.page_P.plot.fig.savefig(
                        os.path.join(target_dir, "P.png"),
                        dpi=200, bbox_inches="tight"
                    )
                    files_saved.append("P.png")
            except Exception:
                pass

            if have_thermal:
                thermal_files = self._save_thermal_results(target_dir)
                files_saved.extend(thermal_files)

        except Exception as e:
            QMessageBox.critical(self, self._tr("Save error", "Ошибка сохранения"),
                                 self._tr(f"Could not save files:\n{e}", f"Не удалось сохранить файлы:\n{e}"))
            return

        msg = self._tr("Saved files:\n  - ", "Сохранены файлы:\n  - ") + "\n  - ".join(files_saved)
        missing = []
        if not have_M:
            missing.append("M")
        if not have_T:
            missing.append("T")
        if not have_P:
            missing.append("P")
        if missing:
            msg += self._tr("\n\nThe following quantities were not calculated and were not saved: ",
                            "\n\nСледующие величины не были рассчитаны и поэтому не сохранены: ") + ", ".join(missing)

        QMessageBox.information(self, self._tr("Done", "Готово"),
                                msg + self._tr(f"\n\nFolder:\n{target_dir}", f"\n\nПапка:\n{target_dir}"))

    def _save_thermal_results(self, target_dir):
        from openpyxl import Workbook
        from openpyxl.drawing.image import Image as XLImage
        from openpyxl.styles import PatternFill, Alignment, Font, Border, Side
        from openpyxl.utils import get_column_letter

        png_name = "thermal_heat_flux.png"
        xlsx_name = "thermal_calculation.xlsx"
        csv_name = "thermal_calculation.csv"
        png_path = os.path.join(target_dir, png_name)
        xlsx_path = os.path.join(target_dir, xlsx_name)
        csv_path = os.path.join(target_dir, csv_name)

        table = self.heat_load_table
        if not isinstance(table, pd.DataFrame):
            table = pd.DataFrame(table)
        self.heat_load_table = table

        table.to_csv(csv_path, index=False, sep=";", decimal=",", encoding="utf-8-sig")

        self.page_thermal.plot.fig.savefig(png_path, dpi=200, bbox_inches="tight")

        wb = Workbook()
        ws = wb.active
        ws.title = "Тепловой расчёт"
        ws.sheet_view.showGridLines = True

        title_fill = PatternFill("solid", fgColor="2B66A4")
        section_fill = PatternFill("solid", fgColor="D9EEF3")
        header_fill = PatternFill("solid", fgColor="5B9BD5")
        maximum_fill = PatternFill("solid", fgColor="FFF0B3")
        thin = Side(style="thin", color="B7C9DD")
        border = Border(left=thin, right=thin, top=thin, bottom=thin)

        ws.merge_cells("A1:J1")
        ws["A1"] = "Тепловой расчёт"
        ws["A1"].fill = title_fill
        ws["A1"].font = Font(bold=True, color="FFFFFF", size=14)
        ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
        ws.row_dimensions[1].height = 24
        ws.unmerge_cells("A1:J1")
        ws["A1"] = "Параметр"
        ws["B1"] = "Значение"
        ws["C1"] = "Единица"

        ws["A3"] = "Параметр"
        ws["B3"] = "Значение"
        ws["C3"] = "Единица"
        T_wall_material_max = getattr(self, "T_wall_material_max", None)
        if T_wall_material_max is None and hasattr(self, "page_thermal"):
            T_wall_material_max = getattr(self.page_thermal, "_last_max_temperature", None)
        if T_wall_material_max is None:
            T_wall_material_max = float(self.T_gas_wall) + 50.0

        summary = [
            ("Предельно допустимая температура материала огневой стенки", float(T_wall_material_max), "K"),
            ("Температура газовой стенки", float(self.T_gas_wall), "K"),
            ("Термодинамический коэффициент", float(self.S_gas_wall), "-"),
            ("Суммарная тепловая нагрузка", float(self.Q), "W"),
        ]
        for row, values in enumerate(summary, start=2):
            for col, value in enumerate(values, start=1):
                ws.cell(row=row, column=col, value=value)
        for cell in ws[1]:
            if cell.column <= 3:
                cell.fill = section_fill
                cell.font = Font(bold=True)
                cell.alignment = Alignment(horizontal="center")
                cell.border = border
        for row in range(2, 6):
            for col in range(1, 4):
                ws.cell(row=row, column=col).border = border
            ws.cell(row=row, column=2).number_format = "0.000000000"

        table_start = 7
        parameter_labels = self.page_thermal._table_parameter_labels
        display_columns = [name for name in parameter_labels if name in table.columns]
        point_count = len(table.index)

        maximum_index = None
        if "q_sum [W/m^2]" in table.columns and point_count:
            try:
                maximum_index = int(np.nanargmax(np.asarray(table["q_sum [W/m^2]"], dtype=float)))
            except Exception:
                maximum_index = None

        parameter_header = self.page_thermal._table_parameter_caption
        point_header = self.page_thermal._table_point_caption
        cell = ws.cell(row=table_start, column=1, value=parameter_header)
        cell.fill = header_fill
        cell.font = Font(bold=True, color="FFFFFF")
        cell.alignment = Alignment(horizontal="left", vertical="center")
        cell.border = border

        for point_index in range(point_count):
            caption = f"{point_header} {point_index + 1}"
            if point_index == maximum_index:
                caption += " ★"
            cell = ws.cell(row=table_start, column=point_index + 2, value=caption)
            cell.fill = maximum_fill if point_index == maximum_index else header_fill
            cell.font = Font(bold=True, color="000000" if point_index == maximum_index else "FFFFFF")
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = border

        for row_offset, column_name in enumerate(display_columns, start=1):
            label_cell = ws.cell(
                row=table_start + row_offset,
                column=1,
                value=parameter_labels[column_name],
            )
            label_cell.fill = section_fill
            label_cell.font = Font(bold=True)
            label_cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
            label_cell.border = border

            for point_index, value in enumerate(table[column_name].tolist()):
                if isinstance(value, np.generic):
                    value = value.item()
                cell = ws.cell(row=table_start + row_offset, column=point_index + 2, value=value)
                if point_index == maximum_index:
                    cell.fill = maximum_fill
                cell.border = border
                cell.alignment = Alignment(horizontal="left" if isinstance(value, str) else "right")
                if isinstance(value, (int, float)):
                    cell.number_format = "0.000000000"

        ws.column_dimensions["A"].width = 30
        for col in range(2, point_count + 2):
            ws.column_dimensions[get_column_letter(col)].width = 14
        ws.row_dimensions[table_start].height = 20
        for row_offset, column_name in enumerate(display_columns, start=1):
            ws.row_dimensions[table_start + row_offset].height = (
                32 if "\n" in parameter_labels[column_name] else 22
            )

        graph = XLImage(png_path)
        graph.width = 720
        graph.height = 480
        graph_row = table_start + len(display_columns) + 2
        ws.add_image(graph, f"A{graph_row}")
        ws.page_setup.orientation = "landscape"
        ws.page_setup.fitToWidth = 1
        ws.sheet_properties.pageSetUpPr.fitToPage = True
        wb.save(xlsx_path)
        return [xlsx_name, csv_name, png_name]

    def save_results_table_xlsx(self, path):
        from openpyxl import Workbook
        from openpyxl.styles import PatternFill, Alignment, Font, Border, Side
        from openpyxl.utils import get_column_letter

        wb = Workbook()
        ws = wb.active
        ws.title = self._tr("Results", "Результаты")

        header_fill = PatternFill("solid", fgColor="FFFFFF")
        section_fill = PatternFill("solid", fgColor="D9EEF3")

        thin_gray = Side(style="thin", color="D9D9D9")
        thin_black = Side(style="thin", color="000000")

        ws.append([self._tr("Parameter", "Параметр"), self._tr("Value", "Значение"),
                   self._tr("Unit", "Единица")])

        current_section = None

        for section, param, value, unit in self._collect_results_table():
            if section != current_section:
                row_idx = ws.max_row + 1
                ws.append([section, "", ""])
                ws.merge_cells(
                    start_row=row_idx,
                    start_column=1,
                    end_row=row_idx,
                    end_column=3
                )
                current_section = section

            ws.append([param, value, unit])

        max_row = ws.max_row
        max_col = 3

        section_names = [
            self._tr("Input Parameters", "Входные параметры"),
            self._tr("Specific Impulse and Flow Rates", "Удельные импульсы и расходы"),
            self._tr("Geometry Parameters", "Геометрические параметры")
        ]

        for row in range(1, max_row + 1):
            is_header = row == 1
            is_section = ws.cell(row=row, column=1).value in section_names

            for col in range(1, max_col + 1):
                cell = ws.cell(row=row, column=col)

                cell.border = Border(
                    left=thin_black,
                    right=thin_black,
                    top=thin_black if is_header or is_section else thin_gray,
                    bottom=thin_black if row == max_row or is_header or is_section else thin_gray
                )

                cell.alignment = Alignment(
                    horizontal="center" if is_section else "left",
                    vertical="center"
                )

                if is_header:
                    cell.fill = header_fill
                    cell.font = Font(bold=True)

                if is_section:
                    cell.fill = section_fill

        for col_idx in range(1, max_col + 1):
            max_len = 0
            col_letter = get_column_letter(col_idx)

            for row_idx in range(1, max_row + 1):
                cell = ws.cell(row=row_idx, column=col_idx)

                if cell.coordinate in ws.merged_cells:
                    continue

                value = "" if cell.value is None else str(cell.value)
                max_len = max(max_len, len(value))

            ws.column_dimensions[col_letter].width = max_len + 3

        ws.column_dimensions["B"].width = max(ws.column_dimensions["B"].width, 18)
        ws.column_dimensions["C"].width = max(ws.column_dimensions["C"].width, 12)

        wb.save(path)

    def _collect_results_table(self):
        inputs = self._tr("Input Parameters", "Входные параметры")
        impulses = self._tr("Specific Impulse and Flow Rates", "Удельные импульсы и расходы")
        geometry = self._tr("Geometry Parameters", "Геометрические параметры")
        mpa = self._tr("MPa", "МПа")
        kelvin = self._tr("K", "К")
        gas_unit = self._tr("J/(kg K)", "Дж/(кг К)")
        isp_unit = self._tr("m/s", "м/с")
        flow_unit = self._tr("kg/s", "кг/с")
        mm = self._tr("mm", "мм")
        return [
            [inputs, self._tr("Oxidizer", "Окислитель"), self._tr("Liquid oxygen", "Жидкий кислород"), ""],
            [inputs, self._tr("Fuel", "Горючее"), self._tr("Kerosene", "Керосин"), ""],
            [inputs, self._tr("Engine design mode", "Расчетный режим двигателя"), self.cb_calc_mode.currentText(), ""],
            [inputs, self._tr("Sea-level thrust P_SL", "Тяга на уровне моря P_SL"), self.model.P_0, self._tr("N", "Н")],
            [inputs, self._tr("Vacuum thrust P_inf", "Тяга в вакууме P_inf"), self.model.P_8, self._tr("N", "Н")],
            [inputs, self._tr("Chamber pressure p_c", "Давление в камере сгорания p_c"), self.model.p_k, mpa],
            [inputs, self._tr("Chamber temperature T_c", "Температура продуктов в камере T_c"), self.model.T_k, kelvin],
            [inputs, self._tr("Nozzle exit pressure p_e", "Давление на срезе сопла p_e"), self.model.p_a, mpa],
            [inputs, self._tr("Specific heat ratio gamma", "Показатель адиабаты γ"), self.model.k, ""],
            [inputs, self._tr("Specific gas constant R_g", "Удельная газовая постоянная R_g"), self.model.R, gas_unit],

            [impulses, self._tr("Reduced reference specific impulse J_red", "Приведённый опорный удельный импульс J_red"),
             self.model.J_pr_ud_st, isp_unit],
            [impulses, self._tr("Design specific impulse J_design", "Удельный импульс на расчётном режиме J_design"),
             self.model.J_r_ud, isp_unit],
            [impulses, self._tr("Vacuum specific impulse J_inf", "Удельный импульс в вакууме J_inf"),
             self.model.J_8_ud, isp_unit],
            [impulses, self._tr("Sea-level specific impulse J_SL", "Удельный импульс на уровне моря J_SL"),
             self.model.J_0_ud, isp_unit],
            [impulses, self._tr("Total propellant flow rate", "Суммарный расход топлива"),
             self.model.m_, flow_unit],
            [impulses, self._tr("Fuel flow rate", "Расход горючего"), self.model.m_g, flow_unit],
            [impulses, self._tr("Oxidizer flow rate", "Расход окислителя"), self.model.m_ok, flow_unit],

            [geometry, self._tr("Nozzle throat diameter D_t", "Диаметр критического сечения D_t"),
             self.model.D_kr, mm],
            [geometry, self._tr("Nozzle expansion ratio epsilon=A_e/A_t", "Степень расширения сопла ε=A_e/A_t"),
             self.model.fa, ""],
            [geometry, self._tr("Nozzle exit diameter D_e", "Диаметр среза сопла D_e"), self.model.D_a, mm],
            [geometry, self._tr("Combustion chamber diameter D_c", "Диаметр камеры сгорания D_c"), self.model.D_k, mm],
            [geometry, self._tr("Divergent nozzle length L_div", "Длина расширяющейся части сопла L_div"), self.model.L_c, mm],
            [geometry, self._tr("Chamber-nozzle assembly length L_total", "Полная длина камеры и сопла L_total"), self.model.L_dv, mm],
        ]

    # ---------- прочее ----------

    def _add_edit(self, grid: QGridLayout, row: int, col: int, label: str) -> QLineEdit:
        grid.addWidget(QLabel(label), row, col)
        ed = QLineEdit();
        grid.addWidget(ed, row, col + 1)
        return ed

    def _add_edit_unit(self, grid: QGridLayout, row: int, col: int, label: str, unit: str = None) -> QLineEdit:
        grid.addWidget(QLabel(label), row, col)
        wrap = QWidget();
        h = QHBoxLayout(wrap);
        h.setContentsMargins(0, 0, 0, 0);
        h.setSpacing(6)
        ed = QLineEdit();
        h.addWidget(ed, 1)
        if unit:
            u = QLabel(unit);
            u.setStyleSheet("color:#888;")
            h.addWidget(u, 0, Qt.AlignRight | Qt.AlignVCenter)
        grid.addWidget(wrap, row, col + 1)
        return ed

    def _add_unit_suffix(self, ed: QLineEdit, unit_text: str):
        lab = QLabel(unit_text);
        lab.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lab.setStyleSheet("color:#888; margin-right:0px;")
        act = QWidgetAction(ed);
        act.setDefaultWidget(lab)
        ed.addAction(act, QLineEdit.TrailingPosition)
        if not hasattr(ed, "_unit_actions"): ed._unit_actions = []
        ed._unit_actions.append(act)

    def on_change(self, *args):
        idx = self.cbFuel.currentIndex()
        fuel_idx = self.cbFuel.itemData(idx) or 1
        self.model.set_fuel(fuel_idx)

        with QtCore.QSignalBlocker(self.ed_k_m): self.ed_k_m.setText(
            "" if self.model.k_m is None else f"{self.model.k_m:.6g}")
        with QtCore.QSignalBlocker(self.ed_R):   self.ed_R.setText(
            "" if self.model.R is None else f"{self.model.R:.6g}")
        with QtCore.QSignalBlocker(self.ed_k):   self.ed_k.setText(
            "" if self.model.k is None else f"{self.model.k:.6g}")
        with QtCore.QSignalBlocker(self.ed_Tst): self.ed_Tst.setText(
            "" if self.model.T_st is None else f"{self.model.T_st:.6g}")
        with QtCore.QSignalBlocker(self.ed_Jst): self.ed_Jst.setText(
            "" if self.model.J_st_ud is None else f"{self.model.J_st_ud:.6g}")

        self._overridden.clear()
        self.timer.start()

    def _set_pa_validator(self, min_val: float):
        self.min_pa = min_val
        upper = max(float(min_val), NOZZLE_EXIT_PRESSURE_MAX_MPA)
        v = QDoubleValidator(min_val, upper, 6, self)
        v.setNotation(QDoubleValidator.StandardNotation)
        v.setLocale(self._locale)
        self.ed_p_a.setValidator(v)

    def _enforce_p_e_bounds(self, show_warning=False):
        s = self.ed_p_a.text().strip()
        if not s:
            return None
        try:
            val = float(s.replace(',', '.'))
        except ValueError:
            if self.min_pa is not None:
                self._set_if_diff(self.ed_p_a, self.min_pa)
                return self.min_pa
            return None

        new_val = val
        if self.min_pa is not None and new_val < self.min_pa:
            new_val = self.min_pa
        if new_val > NOZZLE_EXIT_PRESSURE_MAX_MPA:
            new_val = NOZZLE_EXIT_PRESSURE_MAX_MPA
            if show_warning:
                QMessageBox.warning(
                    self,
                    self._tr("Nozzle exit pressure", "\u0414\u0430\u0432\u043b\u0435\u043d\u0438\u0435 \u043d\u0430 \u0441\u0440\u0435\u0437\u0435 \u0441\u043e\u043f\u043b\u0430"),
                    self._tr(
                        "Nozzle exit pressure was limited to 0.10856 MPa. Higher values are not used because 0.10856 MPa is taken as the maximum atmospheric pressure at Earth surface.",
                        "\u0414\u0430\u0432\u043b\u0435\u043d\u0438\u0435 \u043d\u0430 \u0441\u0440\u0435\u0437\u0435 \u0441\u043e\u043f\u043b\u0430 \u043e\u0433\u0440\u0430\u043d\u0438\u0447\u0435\u043d\u043e \u0437\u043d\u0430\u0447\u0435\u043d\u0438\u0435\u043c 0.10856 \u041c\u041f\u0430. \u0411\u043e\u043b\u0435\u0435 \u0432\u044b\u0441\u043e\u043a\u043e\u0435 \u0437\u043d\u0430\u0447\u0435\u043d\u0438\u0435 \u043d\u0435 \u0438\u0441\u043f\u043e\u043b\u044c\u0437\u0443\u0435\u0442\u0441\u044f, \u0442\u0430\u043a \u043a\u0430\u043a 0.10856 \u041c\u041f\u0430 \u043f\u0440\u0438\u043d\u044f\u0442\u043e \u043a\u0430\u043a \u043c\u0430\u043a\u0441\u0438\u043c\u0430\u043b\u044c\u043d\u043e\u0435 \u0430\u0442\u043c\u043e\u0441\u0444\u0435\u0440\u043d\u043e\u0435 \u0434\u0430\u0432\u043b\u0435\u043d\u0438\u0435 \u0443 \u043f\u043e\u0432\u0435\u0440\u0445\u043d\u043e\u0441\u0442\u0438 \u0417\u0435\u043c\u043b\u0438."
                    )
                )
        if new_val != val:
            self._set_if_diff(self.ed_p_a, new_val)
        return new_val

    def _on_Tk_finished(self):
        if self._validing_Tk: return
        self._validing_Tk = True
        try:
            s = self.ed_T_k.text().strip()
            if not s: return
            try:
                tk = float(s.replace(',', '.'))
                self._last_auto_Tk = tk
            except Exception:
                self.ed_T_k.blockSignals(True)
                if self._last_auto_Tk is not None and np.isfinite(self._last_auto_Tk):
                    self.ed_T_k.setText(f"{self._last_auto_Tk:.6g}")
                else:
                    self.ed_T_k.clear()
                self.ed_T_k.blockSignals(False)
                QMessageBox.information(
                    self, "T_k",
                    self._tr("Invalid input. The previously calculated (or last valid) T_k has been restored.",
                             "Некорректный ввод. Возвращено ранее вычисленное (или последнее корректное) T_k.")
                )
        finally:
            self._validing_Tk = False

    def _v(self, ed: QLineEdit):
        s = ed.text().strip().replace(',', '.')
        try:
            return float(s) if s else None
        except Exception:
            return None

    def _set_if_diff(self, ed: QLineEdit, val, fmt="%.10g"):
        if val is None or not np.isfinite(val): return
        new = fmt % float(val)
        if ed.text().replace(',', '.') != new:
            with QtCore.QSignalBlocker(ed):
                ed.setText(new)

    def recompute(self):
        m = self.model
        k_m = self._v(self.ed_k_m);
        R = self._v(self.ed_R);
        k_ = self._v(self.ed_k)
        T_st = self._v(self.ed_Tst);
        J_st = self._v(self.ed_Jst)
        if k_m is not None: m.k_m = k_m
        if R is not None: m.R = R
        if k_ is not None: m.k = k_
        if T_st is not None: m.T_st = T_st
        if J_st is not None: m.J_st_ud = J_st

        p_k = self._v(self.ed_p_k)
        thrust_source, thrust_value = self._current_thrust_input()
        P_calc = thrust_value
        coefJ = COEF_J_DEFAULT
        z_k = 1.0
        self.ed_z_k.setText("1")

        T_k = self._v(self.ed_T_k);
        p_e = self._v(self.ed_p_a)
        p_h = self._current_p_h()
        Jpr = self._v(self.ed_Jpr);
        Jr = self._v(self.ed_Jr);
        J0 = self._v(self.ed_J0)

        if not all(v is not None for v in (p_k, thrust_value, z_k)):
            return
        if p_e is not None and p_e > NOZZLE_EXIT_PRESSURE_MAX_MPA:
            return

        if self._auto_allowed("T_k"):
            Tk_auto = m.auto_Tk(p_k) if p_k is not None else None
            if Tk_auto is not None and np.isfinite(Tk_auto):
                T_k = Tk_auto
                self._set_if_diff(self.ed_T_k, T_k)

        if self._auto_allowed("J_pr_ud_st") and m.J_st_ud is not None:
            Jpr = coefJ * m.J_st_ud
            self._set_if_diff(self.ed_Jpr, Jpr)

            # --- J_r_ud ---
        if self._auto_allowed("J_r_ud") and None not in (p_k, p_e, T_k, m.R, m.k):
            k1 = (m.k - 1) / m.k
            eps = (p_e / p_k) if (p_k and p_e) else None
            if eps is not None and Jpr is not None:
                Jr = Jpr * (0.67 - 0.016 * p_k + 0.163 * np.sqrt(p_k)) * np.sqrt(
                    (1 - eps ** k1) * p_k ** k1 / (p_k ** k1 - 0.0981 ** k1))
                self._set_if_diff(self.ed_Jr, Jr)

            # --- J_0_ud ---
        if self._auto_allowed("J_0_ud") and None not in (Jr, T_k, p_k, p_e, m.R, m.k) and p_e > 0:
            k1 = (m.k - 1) / m.k
            J8 = Jr + m.R * T_k * (p_e / p_k) ** k1 / Jr
            J0 = J8 - m.R * T_k * (p_e / p_k) ** k1 / Jr * (m.p / p_e)
            self._set_if_diff(self.ed_J0, J0)

        if None in (T_k, p_e, p_h) or p_k <= 0 or p_e <= 0 or p_e >= p_k or thrust_value <= 0 or z_k <= 0:
            return
        try:
            P_calc = self._resolve_design_thrust(p_k, thrust_value, thrust_source, coefJ, z_k, T_k, p_e, p_h)
            m.compute_geometry(p_k, P_calc, coefJ, z_k, T_k, p_e, p_h=p_h, calc_mode=self._calc_mode)
        except Exception:
            return
        self._set_if_diff(self.ed_P_0, m.P_0)
        self._set_if_diff(self.ed_P_8, m.P_8)

        if "J_pr_ud_st" in self._overridden and Jpr is not None: m.J_pr_ud_st = Jpr
        if "J_r_ud" in self._overridden and Jr is not None: m.J_r_ud = Jr
        if "J_0_ud" in self._overridden and J0 is not None:
            m.J_0_ud = J0
            m.P_0 = m.m_ * z_k * m.J_0_ud
            self._set_if_diff(self.ed_P_0, m.P_0)
        self._update_nozzle_status()


# ----------------------------------- main ----------------------------------- #
if __name__ == "__main__":

    # --- High DPI для разных масштабов экрана ---
    QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)

    # === Единый базовый шрифт ===
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    w = Window()


    def _apply_initial_theme():
        try:
            settings = QtCore.QSettings("LRE", "NozzleDesigner")
            theme = settings.value("ui/theme", "light")
        except Exception:
            theme = "light"
        if theme not in ("light", "dark"):
            theme = "light"
        w._apply_palette(theme)
        w._update_theme_button(theme)


    QtCore.QTimer.singleShot(0, _apply_initial_theme)

    w.resize(1200, 780)
    w.show()
    sys.exit(app.exec_())

