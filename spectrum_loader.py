import os
import json
import numpy as np


def load_and_reconstruct_spectra(file_path):
    spectra = []

    if not file_path.endswith(".json"):
        return spectra, "Неподдерживаемый формат файла"

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        return spectra, f"Ошибка чтения JSON: {exc}"

    try:
        common_opts = data["ExperimentOptions"]["CommonOptions"]
        center_field = common_opts.get("CenterMagneticField")
        sweep_width = common_opts.get("SweepWidth")
        if center_field is None or sweep_width is None:
            return spectra, "Отсутствуют CenterMagneticField или SweepWidth"

        values = data.get("Values") or []
        if not values or "Values" not in values[0]:
            return spectra, "Отсутствуют массивы Values"

        points = values[0]["Values"]
        if not points:
            return spectra, "В спектре нет точек"

        phase = data.get("PhaseRadians", 0.0)
        n_points = len(points)
        i_array = np.arange(n_points)

        a_values = np.array([p["Points"][1] for p in points], dtype=float)
        b_values = np.array([p["Points"][0] for p in points], dtype=float)
        y = np.cos(phase) * b_values + np.sin(phase) * a_values

        step = sweep_width / (n_points - 1) if n_points > 1 else 0
        x = center_field - sweep_width / 2 + i_array * step

    except (KeyError, IndexError, TypeError, ValueError) as exc:
        return spectra, f"Некорректная структура спектра: {exc}"

    noise_level = data.get("NoiseLevel")
    signal_level = float(np.max(y) - np.min(y)) if y.size else 0.0
    snr = signal_level / noise_level if noise_level not in (None, 0) else None

    attenuation = None
    mw_parameter = common_opts.get("MwParameter")
    if isinstance(mw_parameter, dict):
        attenuation = mw_parameter.get("AttenuationDb")

    params = {
        "center_field": center_field,
        "sweep_width": sweep_width,
        "points": common_opts.get("PointsCount", n_points),
        "sweep_time": common_opts.get("Time"),
        "modulation_amplitude": common_opts.get("ModulationAmplitude"),
        "attenuation": attenuation,
        "noise_level": noise_level,
        "signal_level": signal_level,
        "snr": snr,
    }

    spectra.append((x, y, os.path.basename(file_path), params))
    return spectra, None