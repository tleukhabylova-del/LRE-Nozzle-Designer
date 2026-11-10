# LRE Nozzle Designer Architecture

The application is being separated into small, verifiable modules. Structural refactoring must preserve the formulas and observable application behavior.

## Current modules

- `main.py` — PyQt application window, workflow coordination, and application entry point. It remains the largest file.
- `lre_tool/constants.py` — constants and propellant-pair reference data.
- `lre_tool/model.py` — engineering model, nozzle geometry, and the `GeometryState` object.
- `lre_tool/mach.py` — Mach-number distribution calculations along the nozzle.
- `lre_tool/plotting.py` — plots and nozzle drawings.
- `lre_tool/pages.py` — plot pages and the thermal-analysis UI.
- `lre_tool/persistence.py` — report and table reading plus Excel result export.
- `lre_tool/thermal.py` — interpolation and supporting thermal-analysis formulas.
- `lre_tool/styles.py` — light and dark theme palettes and style sheets.
- `lre_tool/dialogs.py` — propellant-pair viewing and editing dialog.
- `lre_tool/validators.py` — numeric input with either a decimal point or comma.
- `lre_tool/inverse.py` — existing-nozzle performance calculations and shared thrust-versus-altitude data.
- `lre_tool/inverse_dialog.py` — existing-nozzle analysis dialog.
- `lre_tool/altitude_dialog.py` — the shared altitude chart for main and existing-nozzle calculations.

## Refactoring rules

1. Every extraction must be accompanied by checks before and after the change.
2. Calculation functions receive their inputs explicitly instead of relying on global variables.
3. A single step changes either structure or behavior, not both.
4. Changes are published to GitHub only after local application verification.
