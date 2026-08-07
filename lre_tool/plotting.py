"""Reusable Matplotlib widget for charts and nozzle geometry."""

import numpy as np

from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QCursor
from PyQt5.QtWidgets import QToolTip, QVBoxLayout, QWidget

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.collections import PolyCollection
from matplotlib.colors import Normalize
from matplotlib.figure import Figure
import matplotlib.cm as cm
from mpl_toolkits.axes_grid1 import make_axes_locatable

from .model import Model


def crop_curve_by_x_range(x_arr, y_arr, x_min, x_max):
    x_arr = np.asarray(x_arr, dtype=float)
    y_arr = np.asarray(y_arr, dtype=float)
    mask = np.isfinite(x_arr) & np.isfinite(y_arr)
    x_arr = x_arr[mask]
    y_arr = y_arr[mask]
    if x_arr.size == 0 or y_arr.size == 0:
        return x_arr, y_arr
    order = np.argsort(x_arr)
    x_arr, y_arr = x_arr[order], y_arr[order]
    x_min, x_max = sorted((float(x_min), float(x_max)))
    x_min = max(x_min, float(x_arr[0]))
    x_max = min(x_max, float(x_arr[-1]))
    inner = (x_arr >= x_min) & (x_arr <= x_max)
    x_crop, y_crop = x_arr[inner], y_arr[inner]
    y_left = float(np.interp(x_min, x_arr, y_arr))
    y_right = float(np.interp(x_max, x_arr, y_arr))
    if x_crop.size == 0 or not np.isclose(x_crop[0], x_min):
        x_crop, y_crop = np.insert(x_crop, 0, x_min), np.insert(y_crop, 0, y_left)
    if x_crop.size == 0 or not np.isclose(x_crop[-1], x_max):
        x_crop, y_crop = np.append(x_crop, x_max), np.append(y_crop, y_right)
    return x_crop, y_crop


class PlotWidget(QWidget):
    def __init__(self, title="", geometry_state=None):
        super().__init__()
        self.geometry_state = geometry_state
        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 8, 8, 8)

        self.fig = Figure(figsize=(6, 4), dpi=100)
        self.canvas = FigureCanvas(self.fig)
        lay.addWidget(self.canvas)

        self.ax = self.fig.add_subplot(111)
        self.title = title
        self._responsive_margins = False
        self._layout_update_pending = False

        # Use the light theme by default.
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

    # --- Plot theme switching ---
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
        # Plot borders.
        for sp in self.ax.spines.values():
            sp.set_color(self.fg_color)
        # Axes, labels, and title.
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
        self._hover_x = None
        self._hover_y = None
        self._hover_val = None
        self._hover_label = ""
        self._hover_unit = ""
        self.canvas.draw_idle()

    def draw_fill(self, x_arr, y_arr, val_arr, y0=0.0, cmap="turbo", refine=2, clabel=""):
        self.clear()
        x_arr = np.asarray(x_arr);
        y_arr = np.asarray(y_arr);
        val_arr = np.asarray(val_arr)

        idx = np.argsort(x_arr)
        x, y, T = x_arr[idx], y_arr[idx], val_arr[idx]

        try:
            x0_nozzle = float(self.geometry_state.L_g + self.geometry_state.L_cy)
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

        # Match the color bar to the active theme.
        cb.outline.set_edgecolor(self.fg_color)
        cb.ax.tick_params(color=self.fg_color)
        for lab in cb.ax.get_yticklabels():
            lab.set_color(self.fg_color)

        # Nozzle contour.
        self.ax.plot(x, y, color=self.fg_color, lw=0.8)
        self.ax.set_aspect("equal", adjustable="box")
        self.ax.set_title(self.title)
        self.ax.set_xlim(float(x.min()), float(x.max()) * 1.01)

        try:
            y_top = float(max(self.geometry_state.R_k, self.geometry_state.R_a))
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

    # --- Consolidated and corrected draw_geometry implementation ---
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

        L_g, L_cy = model.L_g, model.L_cy
        L_vh, L_c, L_dv = model.L_vh, model.L_c, model.L_dv
        D_k, D_kr, D_a = model.D_k, model.D_kr, model.D_a

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

        # Diameters.
        draw_v_dim(ax, (x2 + x3) / 2, -y2, y2, "Ø " + str(round(D_k, 2)), loc="center")
        draw_v_dim(ax, x4, -y4, y4, "Ø " + str(round(D_kr, 2)), loc="center")
        draw_v_dim(ax, x5, -y5, y5, "Ø " + str(round(D_a, 2)), loc="left")

        # Individual section lengths.
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
