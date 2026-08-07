"""Pure helper calculations used by the thermal-analysis workflow."""

import numpy as np


def median(values):
    values = sorted(float(value) for value in values)
    if not values:
        raise ValueError("empty median")
    middle = len(values) // 2
    if len(values) % 2:
        return values[middle]
    return 0.5 * (values[middle - 1] + values[middle])


def local_slope(rows, side, n_points=4):
    count = min(n_points, len(rows))
    edge_rows = rows[:count] if side == "lower" else rows[-count:]
    slopes = []
    steps = []
    for index in range(len(edge_rows) - 1):
        temperature_1, temperature_2 = edge_rows[index]["T"], edge_rows[index + 1]["T"]
        value_1, value_2 = edge_rows[index]["S"], edge_rows[index + 1]["S"]
        temperature_step = temperature_2 - temperature_1
        if abs(temperature_step) > 1e-12:
            slopes.append((value_2 - value_1) / temperature_step)
            steps.append(abs(temperature_step))
    if not slopes:
        raise ValueError("not enough S points for extrapolation")
    return median(slopes), sum(steps) / len(steps)


def interpolate_s(rows, target_temperature, translate, pair_name):
    rows = sorted(rows, key=lambda row: row["T"])
    if len(rows) < 2:
        raise ValueError(translate(
            f"Thermal-load calculation is unavailable for the propellant pair “{pair_name}”: "
            "the required thermodynamic-coefficient data are missing.",
            f"Расчёт тепловых нагрузок недоступен для топливной пары «{pair_name}»: "
            "отсутствуют необходимые данные термодинамического коэффициента.",
        ))

    temperatures = [row["T"] for row in rows]
    maximum_step = max(
        abs(temperatures[index + 1] - temperatures[index])
        for index in range(len(temperatures) - 1)
    )
    minimum_temperature, maximum_temperature = temperatures[0], temperatures[-1]
    warning = None

    if target_temperature < minimum_temperature:
        gap = minimum_temperature - target_temperature
        warning = translate(
            f"T_gas_wall is below the available S database range "
            f"({minimum_temperature:g}...{maximum_temperature:g} K).",
            f"T_gas_wall ниже доступного диапазона базы S "
            f"({minimum_temperature:g}...{maximum_temperature:g} К).",
        )
        if gap > maximum_step:
            raise ValueError(warning)
        slope, step = local_slope(rows, "lower")
        temperature_1 = minimum_temperature - step
        value_1 = rows[0]["S"] + slope * (temperature_1 - minimum_temperature)
        temperature_2, value_2 = rows[0]["T"], rows[0]["S"]
    elif target_temperature > maximum_temperature:
        gap = target_temperature - maximum_temperature
        warning = translate(
            f"T_gas_wall is above the available S database range "
            f"({minimum_temperature:g}...{maximum_temperature:g} K).",
            f"T_gas_wall выше доступного диапазона базы S "
            f"({minimum_temperature:g}...{maximum_temperature:g} К).",
        )
        if gap > maximum_step:
            raise ValueError(warning)
        slope, step = local_slope(rows, "upper")
        temperature_1, value_1 = rows[-1]["T"], rows[-1]["S"]
        temperature_2 = maximum_temperature + step
        value_2 = rows[-1]["S"] + slope * (temperature_2 - maximum_temperature)
    else:
        for row in rows:
            if abs(row["T"] - target_temperature) < 1e-9:
                return row["S"], warning
        temperature_1 = value_1 = temperature_2 = value_2 = None
        for index in range(len(rows) - 1):
            if rows[index]["T"] <= target_temperature <= rows[index + 1]["T"]:
                temperature_1, value_1 = rows[index]["T"], rows[index]["S"]
                temperature_2, value_2 = rows[index + 1]["T"], rows[index + 1]["S"]
                break
        if temperature_1 is None:
            raise ValueError("Could not choose S interpolation interval.")

    if abs(temperature_2 - temperature_1) < 1e-12:
        raise ValueError("Could not interpolate S: equal temperatures.")
    result = value_2 + (value_1 - value_2) * (
        temperature_2 - target_temperature
    ) / (temperature_2 - temperature_1)
    return float(result), warning


def group_consecutive(indices):
    indices = np.asarray(indices, dtype=int)
    if indices.size == 0:
        return []
    breaks = np.where(np.diff(indices) > 1)[0] + 1
    return np.split(indices, breaks)


def line_centers(scores, relative_threshold=0.35):
    if scores.size == 0 or scores.max() <= 0:
        return np.array([], dtype=int)
    indices = np.where(scores >= relative_threshold * scores.max())[0]
    groups = group_consecutive(indices)
    return np.array(
        [int(round(group.mean())) for group in groups if group.size > 0], dtype=int
    )


def interp_q0(r_ratio, branch, branch_tables):
    if branch == "critical":
        left = interp_q0(1.0, "precritical", branch_tables)
        right = interp_q0(1.0, "postcritical", branch_tables)
        return tuple(0.5 * (left[index] + right[index]) for index in range(3))
    ratios, q0, x_pixels, y_pixels = branch_tables[branch]
    clipped = float(np.clip(r_ratio, ratios.min(), ratios.max()))
    return (
        float(np.interp(clipped, ratios, q0)),
        float(np.interp(clipped, ratios, x_pixels)),
        float(np.interp(clipped, ratios, y_pixels)),
    )


def nozzle_branch(index, throat_index):
    if index < throat_index:
        return "precritical"
    if index > throat_index:
        return "postcritical"
    return "critical"


def radiative_coefficient(branch, radius_ratio):
    if branch == "precritical":
        return 0.2 if radius_ratio >= 1.19 else 0.05
    if branch == "critical":
        return 0.05
    return 0.02 if radius_ratio <= 1.5 else 0.004


def styled_branch_x(branch, radius_ratio):
    if branch == "precritical":
        return (2.5 - radius_ratio) / (2.5 - 1.0)
    if branch == "critical":
        return 1.0
    return 1.0 + (radius_ratio - 1.0) / (2.5 - 1.0)
