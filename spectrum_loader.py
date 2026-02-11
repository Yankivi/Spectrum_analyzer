import os
import json
import numpy as np


def load_and_reconstruct_spectra(file_path):
    spectra = []

    if not os.path.exists(file_path):
        return spectra

    if not file_path.lower().endswith(".json"):
        return spectra

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return spectra

    try:
        common_opts = data["ExperimentOptions"]["CommonOptions"]
        values_block = data["Values"][0]["Values"]
    except Exception:
        return spectra

    n_points = len(values_block)
    if n_points == 0:
        return spectra

    phase = data.get("PhaseRadians", 0.0)
    center_field = common_opts.get("CenterMagneticField")
    sweep_width = common_opts.get("SweepWidth")

    # Каналы
    a_values = np.array([p["Points"][1] for p in values_block], dtype=float)
    b_values = np.array([p["Points"][0] for p in values_block], dtype=float)

    # Фазовая реконструкция
    y = np.cos(phase) * b_values + np.sin(phase) * a_values
    y = -y

    # Ось поля
    if sweep_width is not None and center_field is not None and n_points > 1:
        step = sweep_width / (n_points - 1)
        x = center_field - sweep_width / 2 + np.arange(n_points) * step
    else:
        x = np.arange(n_points)

    # Peak-to-peak
    peak_to_peak = float(np.max(y) - np.min(y)) if y.size else 0.0

    # Noise и SNR
    noise_level = data.get("NoiseLevel")
    if isinstance(noise_level, (int, float)) and noise_level != 0:
        snr = peak_to_peak / noise_level
    else:
        snr = None

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
        "signal_level": peak_to_peak,   # ← только это поле для формы
        "snr": snr,
    }

    spectra.append((x, y, os.path.basename(file_path), params))

    return spectra
