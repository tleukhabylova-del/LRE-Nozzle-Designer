"""Mach-number calculation along the nozzle contour."""

from collections import defaultdict

import numpy as np
from PyQt5 import QtCore
from scipy.optimize import fsolve, minimize_scalar

from .model import GeometryState


def calculate_mach(y, geometry_state: GeometryState, m=10, progress_cb=None):
    """Return the original Mach-number distribution for a nozzle contour."""
    x = geometry_state.x
    if x is None or len(x) != len(y):
        x = np.arange(len(y), dtype=float)
        geometry_state.x = x

    k = geometry_state.k
    R_kr = geometry_state.R_kr
    L_g = geometry_state.L_g
    L_cy = geometry_state.L_cy
    if any(value is None for value in (k, R_kr, L_g, L_cy)):
        raise RuntimeError("Nozzle geometry must be calculated before Mach number.")

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
        n = len(arr)
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


class MWorker(QtCore.QObject):
    """Run the Mach-number calculation without blocking the interface."""

    progressed = QtCore.pyqtSignal(int)
    finished = QtCore.pyqtSignal(object)
    failed = QtCore.pyqtSignal(str)

    def __init__(self, y_arr, geometry_state):
        super().__init__()
        self._y = np.asarray(y_arr, dtype=float)
        self._geometry_state = geometry_state

    @QtCore.pyqtSlot()
    def run(self):
        try:
            def callback(progress):
                self.progressed.emit(int(progress))

            result = calculate_mach(
                self._y, self._geometry_state, progress_cb=callback
            )
            self.finished.emit(np.asarray(result, dtype=float))
        except Exception as error:
            self.failed.emit(str(error))
