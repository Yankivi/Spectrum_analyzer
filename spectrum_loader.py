import os
import json
import numpy as np

def load_and_reconstruct_spectra(file_path):
    spectra = []

    # Загружаем только один файл, переданный в функцию
    if file_path.endswith(".json"):
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        phase = data.get("PhaseRadians", 0.0)
        common_opts = data["ExperimentOptions"]["CommonOptions"]
        center_field = common_opts["CenterMagneticField"]
        sweep_width = common_opts["SweepWidth"]

        points = data["Values"][0]["Values"]
        N = len(points)
        i_array = np.arange(N)

        # Восстановление координат через фазу
        A = np.array([p["Points"][1] for p in points])
        B = np.array([p["Points"][0] for p in points])
        y = np.cos(phase) * B + np.sin(phase) * A
        y = -y
        step = sweep_width / (N - 1) if N > 1 else 0
        x = center_field - sweep_width / 2 + i_array * step

        spectra.append((x, y, os.path.basename(file_path)))

    return spectra