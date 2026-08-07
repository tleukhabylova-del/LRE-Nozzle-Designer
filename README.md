# LRE Nozzle Designer

**LRE Nozzle Designer** is a desktop application for calculating liquid rocket engine parameters and nozzle geometry, plotting calculated distributions, and estimating thermal loads. The user interface is available in English and Russian.

## Features

- propellant-pair selection;
- engine and nozzle-geometry calculations;
- nozzle geometry, pressure, temperature, and Mach-number plots;
- combustion-chamber and nozzle-wall thermal-load calculations;
- export of results to text, CSV, and Excel files;
- light and dark interface themes.

## Requirements

- Windows 10 or 11;
- Python 3.12;
- the packages listed in `requirements.txt`.

## Installation

1. Download or clone the repository.
2. Open PowerShell in the project directory.
3. Create a virtual environment:

   ```powershell
   py -3.12 -m venv .venv
   ```

4. Activate it:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

5. Install the dependencies:

   ```powershell
   python -m pip install --upgrade pip
   python -m pip install -r requirements.txt
   ```

## Running the application

```powershell
python main.py
```

## Project structure

- `main.py` contains the main PyQt application window and coordinates the calculation workflow.
- `lre_tool/` contains calculation models, plotting, persistence, validation, styling, dialogs, and UI-page modules.
- `pair */` directories contain reference data used by the thermal-load calculation.
- `ARCHITECTURE.md` describes the module boundaries and refactoring rules.

Thermal reference CSV files are named after the corresponding gas-wall temperature in kelvins, for example `600.csv`.

## Engineering notice

This application performs engineering calculations. Before practical use, verify its results independently and against relevant technical documentation.

## Author

[tleukhabylova-del](https://github.com/tleukhabylova-del)
