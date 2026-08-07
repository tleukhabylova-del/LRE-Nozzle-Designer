"""Application palette and stylesheet configuration."""

from PyQt5.QtGui import QColor, QPalette
from PyQt5.QtWidgets import QApplication


def apply_window_palette(window, mode: str):
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

        # Apply these four colors together with the shared text color.
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

        # Colors for drop-down lists in the light theme.
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

        /* Primary purple button (when objectName="primaryButton" is set). */
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



        /* Colored scroll bars with a purple handle. */
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

    window.setStyleSheet(base_styles)

    # Apply the same theme to the Matplotlib plots.
    if hasattr(window, "page_geom"):
        try:
            window._set_plot_theme(mode)
        except Exception:
            pass
    if hasattr(window, "lbl_nozzle_status"):
        window._update_nozzle_status()
