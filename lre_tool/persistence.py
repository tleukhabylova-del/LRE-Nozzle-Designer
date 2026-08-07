"""Reading and writing application result files without GUI dependencies."""

import numpy as np
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter


def read_report_parameters(path):
    """Read the machine-readable parameter block embedded in a text report."""
    params = {}
    begin = "LRE_NOZZLE_DESIGNER_PARAMS_BEGIN"
    end = "LRE_NOZZLE_DESIGNER_PARAMS_END"
    in_block = False
    with open(path, "r", encoding="utf-8") as report:
        for raw_line in report:
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
    return params


def read_thermal_table_xlsx(path, parameter_labels):
    """Restore the thermal table written by the application."""
    raw = pd.read_excel(path, header=None)
    label_to_column = {
        str(label).replace("\n", " ").strip(): column
        for column, label in parameter_labels.items()
    }
    label_to_column.update({
        str(column).replace("\n", " ").strip(): column
        for column in parameter_labels
    })

    table_start = None
    for idx in range(len(raw.index)):
        first = str(raw.iloc[idx, 0]).strip()
        if first in ("Parameter", "Параметр"):
            values = [str(value).strip() for value in raw.iloc[idx].tolist() if pd.notna(value)]
            if any(value.startswith("Point") or value.startswith("Точка") for value in values):
                table_start = idx
                break
    if table_start is None:
        return None

    rows = {}
    for idx in range(table_start + 1, len(raw.index)):
        label = raw.iloc[idx, 0]
        if pd.isna(label):
            continue
        column = label_to_column.get(str(label).replace("\n", " ").strip())
        if column is not None:
            rows[column] = raw.iloc[idx, 1:].dropna().tolist()
    return pd.DataFrame(rows) if rows else None


def read_thermal_summary_xlsx(path, float_parser):
    """Read the four summary values at the beginning of a thermal workbook."""
    raw = pd.read_excel(path, header=None)
    values = []
    for idx in range(min(len(raw.index), 8)):
        if raw.shape[1] < 2:
            break
        value = float_parser(raw.iloc[idx, 1])
        if value is not None and np.isfinite(value):
            values.append(value)
    if len(values) < 4:
        return {}
    return {
        "T_wall_material_max": values[0],
        "T_gas_wall": values[1],
        "S_gas_wall": values[2],
        "Q": values[3],
    }


def write_results_table_xlsx(path, rows, headers, section_names):
    """Write the consolidated engineering-results workbook."""
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = headers[3]
    header_fill = PatternFill("solid", fgColor="FFFFFF")
    section_fill = PatternFill("solid", fgColor="D9EEF3")
    thin_gray = Side(style="thin", color="D9D9D9")
    thin_black = Side(style="thin", color="000000")
    sheet.append(list(headers[:3]))

    current_section = None
    for section, parameter, value, unit in rows:
        if section != current_section:
            row_index = sheet.max_row + 1
            sheet.append([section, "", ""])
            sheet.merge_cells(start_row=row_index, start_column=1, end_row=row_index, end_column=3)
            current_section = section
        sheet.append([parameter, value, unit])

    max_row = sheet.max_row
    for row in range(1, max_row + 1):
        is_header = row == 1
        is_section = sheet.cell(row=row, column=1).value in section_names
        for column in range(1, 4):
            cell = sheet.cell(row=row, column=column)
            cell.border = Border(
                left=thin_black,
                right=thin_black,
                top=thin_black if is_header or is_section else thin_gray,
                bottom=thin_black if row == max_row or is_header or is_section else thin_gray,
            )
            cell.alignment = Alignment(
                horizontal="center" if is_section else "left", vertical="center"
            )
            if is_header:
                cell.fill = header_fill
                cell.font = Font(bold=True)
            if is_section:
                cell.fill = section_fill

    for column_index in range(1, 4):
        maximum = 0
        letter = get_column_letter(column_index)
        for row_index in range(1, max_row + 1):
            cell = sheet.cell(row=row_index, column=column_index)
            if cell.coordinate in sheet.merged_cells:
                continue
            maximum = max(maximum, len("" if cell.value is None else str(cell.value)))
        sheet.column_dimensions[letter].width = maximum + 3
    sheet.column_dimensions["B"].width = max(sheet.column_dimensions["B"].width, 18)
    sheet.column_dimensions["C"].width = max(sheet.column_dimensions["C"].width, 12)
    workbook.save(path)
