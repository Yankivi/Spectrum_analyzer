import wx
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
from matplotlib.backends.backend_wxagg import NavigationToolbar2WxAgg as NavigationToolbar
from matplotlib.widgets import SpanSelector
from spectrum_loader import load_and_reconstruct_spectra


class EPRApp(wx.Frame):
    def __init__(self, parent, title):
        super(EPRApp, self).__init__(parent, title=title, size=(1500, 1000))

        self.spectra = []  # Список словарей: {id, x, y, filename, params}
        self.displayed_spectra = set()  # Набор id отображаемых спектров
        self.next_spectrum_id = 1
        self.toolbar = None
        self.span_selector = None
        self.range_selection_enabled = False
        self.selection_mode = None  # None | "integral" | "delta"
        self.hover_annotation = None
        self.hover_threshold_px = 12

        self.CreateStatusBar()
        self.SetStatusText("Готово")

        panel = wx.Panel(self)
        root_layout = wx.BoxSizer(wx.VERTICAL)

        controls_row = wx.BoxSizer(wx.HORIZONTAL)
        self.load_button = wx.Button(panel, label="Загрузить спектры")
        self.load_button.Bind(wx.EVT_BUTTON, self.load_spectrum)
        controls_row.Add(self.load_button, 0, wx.ALL, 5)

        self.delete_button = wx.Button(panel, label="Удалить спектр")
        self.delete_button.Bind(wx.EVT_BUTTON, self.delete_spectrum)
        controls_row.Add(self.delete_button, 0, wx.ALL, 5)

        self.baseline_button = wx.Button(panel, label="Применить базовую линию")
        self.baseline_button.Bind(wx.EVT_BUTTON, self.apply_baseline_to_selected)
        controls_row.Add(self.baseline_button, 0, wx.ALL, 5)

        self.undo_baseline_button = wx.Button(panel, label="Отменить базовую линию")
        self.undo_baseline_button.Bind(wx.EVT_BUTTON, self.undo_baseline_for_selected)
        controls_row.Add(self.undo_baseline_button, 0, wx.ALL, 5)

        self.select_integral_range_button = wx.Button(panel, label="Выбрать область интеграла")
        self.select_integral_range_button.Bind(wx.EVT_BUTTON, self.toggle_integral_range_selection)
        controls_row.Add(self.select_integral_range_button, 0, wx.ALL, 5)

        self.clear_integral_range_button = wx.Button(panel, label="Очистить область интеграла")
        self.clear_integral_range_button.Bind(wx.EVT_BUTTON, self.clear_integral_range_for_selected)
        controls_row.Add(self.clear_integral_range_button, 0, wx.ALL, 5)

        self.integral_button = wx.Button(panel, label="Применить интеграл")
        self.integral_button.Bind(wx.EVT_BUTTON, self.apply_integral_to_selected)
        controls_row.Add(self.integral_button, 0, wx.ALL, 5)

        self.undo_integral_button = wx.Button(panel, label="Отменить интеграл")
        self.undo_integral_button.Bind(wx.EVT_BUTTON, self.undo_integral_for_selected)
        controls_row.Add(self.undo_integral_button, 0, wx.ALL, 5)

        self.select_delta_range_button = wx.Button(panel, label="Выбрать область Δ")
        self.select_delta_range_button.Bind(wx.EVT_BUTTON, self.toggle_delta_range_selection)
        controls_row.Add(self.select_delta_range_button, 0, wx.ALL, 5)

        self.delta_button = wx.Button(panel, label="Рассчитать Δ")
        self.delta_button.Bind(wx.EVT_BUTTON, self.calculate_delta_for_selected)
        controls_row.Add(self.delta_button, 0, wx.ALL, 5)
        root_layout.Add(controls_row, 0, wx.LEFT | wx.RIGHT | wx.TOP, 5)

        content_row = wx.BoxSizer(wx.HORIZONTAL)

        left_col = wx.BoxSizer(wx.VERTICAL)
        list_label = wx.StaticText(panel, label="Спектры (галочка = отображается)")
        list_label.SetFont(list_label.GetFont().Bold())
        left_col.Add(list_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 5)

        self.spectrum_list = wx.CheckListBox(panel)
        self.spectrum_list.Bind(wx.EVT_CHECKLISTBOX, self.on_toggle_spectrum)
        self.spectrum_list.Bind(wx.EVT_LISTBOX, self.on_select_spectrum)
        left_col.Add(self.spectrum_list, 1, wx.EXPAND | wx.ALL, 5)

        content_row.Add(left_col, 1, wx.EXPAND)

        right_col = wx.BoxSizer(wx.VERTICAL)
        self.canvas_panel = wx.Panel(panel)
        self.canvas = None
        self.figure = None
        self.ax = None
        right_col.Add(self.canvas_panel, 3, wx.EXPAND | wx.ALL, 5)

        params_box = wx.StaticBox(panel, label="Параметры выбранного спектра")
        params_sizer = wx.StaticBoxSizer(params_box, wx.VERTICAL)

        self.params_grid = wx.FlexGridSizer(rows=0, cols=2, vgap=4, hgap=12)
        self.params_grid.AddGrowableCol(1, 1)
        self.param_labels = {}
        self.param_order = [
            ("center_field", "Center field"),
            ("sweep_width", "Sweep width"),
            ("points", "Points"),
            ("sweep_time", "Sweep time"),
            ("modulation_amplitude", "Modulation amplitude"),
            ("attenuation", "Attenuation"),
            ("noise_level", "Noise level"),
            ("signal_level", "Signal level"),
            ("snr", "SNR"),
            ("baseline_status", "Baseline correction"),
            ("integral_status", "Integral"),
            ("integral_range", "Integral range"),
            ("integral_value", "Integral value"),
            ("delta_range", "Delta range"),
            ("delta_height", "Delta height"),
            ("delta_weight", "Delta weight"),
        ]

        for key, title in self.param_order:
            name = wx.StaticText(panel, label=f"{title}:")
            value = wx.StaticText(panel, label="N/A")
            self.params_grid.Add(name, 0, wx.ALIGN_LEFT)
            self.params_grid.Add(value, 0, wx.ALIGN_LEFT | wx.EXPAND)
            self.param_labels[key] = value

        params_sizer.Add(self.params_grid, 1, wx.EXPAND | wx.ALL, 8)
        right_col.Add(params_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)

        content_row.Add(right_col, 3, wx.EXPAND)
        root_layout.Add(content_row, 1, wx.EXPAND)

        panel.SetSizer(root_layout)
        self.Show()

    def load_spectrum(self, event):
        wildcard = "JSON Files (*.json)|*.json|All Files (*.*)|*.*"
        file_dialog = wx.FileDialog(
            self,
            "Открыть файл",
            wildcard=wildcard,
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST | wx.FD_MULTIPLE,
        )

        if file_dialog.ShowModal() == wx.ID_OK:
            load_errors = []
            for file_path in file_dialog.GetPaths():
                loaded, error = load_and_reconstruct_spectra(file_path)
                if error:
                    load_errors.append(f"{file_path}: {error}")
                    continue

                for x, y, filename, params in loaded:
                    spectrum_id = self.next_spectrum_id
                    self.next_spectrum_id += 1
                    self.spectra.append(
                        {
                            "id": spectrum_id,
                            "x": x,
                            "y": y.copy(),
                            "raw_y": y.copy(),
                            "filename": filename,
                            "params": params,
                            "baseline_applied": False,
                            "integral_order": 0,
                            "integral_history": [],
                            "integration_range": None,
                            "last_integral_value": None,
                            "delta_range": None,
                            "delta_height": None,
                            "delta_weight": None,
                        }
                    )
                    self.displayed_spectra.add(spectrum_id)

            self.update_spectrum_list()
            self.render_displayed_spectra()

            if self.spectra:
                selected = len(self.spectra) - 1
                self.spectrum_list.SetSelection(selected)
                self.show_spectrum_info(self.spectra[selected])

            if load_errors:
                wx.MessageBox(
                    "Не удалось загрузить некоторые файлы:\n\n" + "\n".join(load_errors),
                    "Ошибки загрузки",
                    wx.OK | wx.ICON_WARNING,
                )

    def ensure_canvas(self):
        if self.canvas is None:
            self.figure, self.ax = plt.subplots(figsize=(8, 5))
            self.canvas = FigureCanvas(self.canvas_panel, -1, self.figure)

            self.toolbar = NavigationToolbar(self.canvas)
            self.toolbar.Realize()

            self.span_selector = SpanSelector(
                self.ax,
                self.on_select_integration_range,
                "horizontal",
                useblit=True,
                props={"facecolor": "orange", "alpha": 0.2},
                interactive=False,
            )
            self.span_selector.set_active(False)

            self.canvas.mpl_connect("motion_notify_event", self.on_plot_hover)

            canvas_layout = wx.BoxSizer(wx.VERTICAL)
            canvas_layout.Add(self.canvas, 1, wx.EXPAND)
            canvas_layout.Add(self.toolbar, 0, wx.EXPAND)
            self.canvas_panel.SetSizer(canvas_layout)
            self.canvas_panel.Layout()
            return

        if self.figure is None:
            self.figure = self.canvas.figure

        if self.ax is None or self.ax not in self.figure.axes:
            if self.figure.axes:
                self.ax = self.figure.axes[0]
            else:
                self.ax = self.figure.add_subplot(111)

    def hide_hover_details(self):
        if self.hover_annotation is not None and self.hover_annotation.get_visible():
            self.hover_annotation.set_visible(False)
            self.canvas.draw_idle()
        self.SetStatusText("Готово")

    def setup_hover_annotation(self):
        self.hover_annotation = self.ax.annotate(
            "",
            xy=(0, 0),
            xytext=(10, 10),
            textcoords="offset points",
            bbox={"boxstyle": "round,pad=0.3", "fc": "white", "alpha": 0.85},
        )
        self.hover_annotation.set_visible(False)

    def on_plot_hover(self, event):
        if self.canvas is None or self.ax is None or self.hover_annotation is None:
            return

        if event.inaxes != self.ax or event.x is None or event.y is None:
            self.hide_hover_details()
            return

        closest = None
        closest_distance = None

        for line in self.ax.get_lines():
            x_data = np.asarray(line.get_xdata(), dtype=float)
            y_data = np.asarray(line.get_ydata(), dtype=float)
            if x_data.size == 0:
                continue

            points_pixels = self.ax.transData.transform(np.column_stack((x_data, y_data)))
            deltas = points_pixels - np.array([event.x, event.y])
            dist2 = np.einsum("ij,ij->i", deltas, deltas)
            idx = int(np.argmin(dist2))
            current_distance = float(np.sqrt(dist2[idx]))

            if closest is None or current_distance < closest_distance:
                closest = (line, idx)
                closest_distance = current_distance

        if closest is None or closest_distance is None or closest_distance > self.hover_threshold_px:
            self.hide_hover_details()
            return

        line, idx = closest
        x_value = float(line.get_xdata()[idx])
        y_value = float(line.get_ydata()[idx])
        label = line.get_label()

        self.hover_annotation.xy = (x_value, y_value)
        self.hover_annotation.set_text(f"{label}\nX: {x_value:.3f}\nY: {y_value:.3f}")
        self.hover_annotation.set_visible(True)
        self.SetStatusText(f"{label} | X={x_value:.3f}, Y={y_value:.3f}")
        self.canvas.draw_idle()

    def update_spectrum_list(self, selected_index=None):
        self.spectrum_list.Clear()
        for index, spectrum in enumerate(self.spectra):
            title = spectrum["filename"]
            if spectrum.get("baseline_applied"):
                title += " [BL]"
            order = spectrum.get("integral_order", 0)
            if order > 0:
                title += f" [I{order}]"
            self.spectrum_list.Append(title)
            self.spectrum_list.Check(index, spectrum["id"] in self.displayed_spectra)

        if selected_index is not None and 0 <= selected_index < len(self.spectra):
            self.spectrum_list.SetSelection(selected_index)

    def render_displayed_spectra(self):
        self.ensure_canvas()
        self.ax.clear()

        for spectrum in self.spectra:
            if spectrum["id"] in self.displayed_spectra:
                self.ax.plot(spectrum["x"], spectrum["y"], label=spectrum["filename"])

        self.ax.set_xlabel("Магнитное поле (mT)")
        self.ax.set_ylabel("Интенсивность сигнала (a.u.)")
        self.ax.set_title("ЭПР-спектры")
        self.ax.grid(True)

        if self.displayed_spectra:
            self.ax.legend()

        self.setup_hover_annotation()
        self.SetStatusText("Готово")

        self.canvas.draw()

    def format_param(self, value, precision=3):
        if value is None:
            return "N/A"
        if isinstance(value, float):
            return f"{value:.{precision}f}"
        if isinstance(value, int):
            return str(value)
        return str(value)

    def show_spectrum_info(self, spectrum):
        params = spectrum.get("params", {})
        for key, _ in self.param_order:
            value = params.get(key)
            if key == "baseline_status":
                value = "Applied" if spectrum.get("baseline_applied") else "Not applied"
            elif key == "integral_status":
                value = f"Order {spectrum.get('integral_order', 0)}"
            elif key == "integral_range":
                x_range = spectrum.get("integration_range")
                value = f"{x_range[0]:.3f} .. {x_range[1]:.3f}" if x_range is not None else "Not selected"
            elif key == "integral_value":
                value = spectrum.get("last_integral_value")
            elif key == "delta_range":
                d_range = spectrum.get("delta_range")
                value = f"{d_range[0]:.3f} .. {d_range[1]:.3f}" if d_range is not None else "Not selected"
            elif key == "delta_height":
                value = spectrum.get("delta_height")
            elif key == "delta_weight":
                value = spectrum.get("delta_weight")
            precision = 0 if key == "points" else 3
            self.param_labels[key].SetLabel(self.format_param(value, precision=precision))
        self.Layout()

    def get_selected_spectrum(self):
        selection = self.spectrum_list.GetSelection()
        if selection == wx.NOT_FOUND or selection >= len(self.spectra):
            return None, None
        return selection, self.spectra[selection]

    def toggle_integral_range_selection(self, event):
        self.ensure_canvas()
        if self.span_selector is None:
            return

        activate = not (self.range_selection_enabled and self.selection_mode == "integral")
        self.range_selection_enabled = activate
        self.selection_mode = "integral" if activate else None
        self.span_selector.set_active(activate)

        self.select_integral_range_button.SetLabel("Отменить выбор области" if activate else "Выбрать область интеграла")
        self.select_delta_range_button.SetLabel("Выбрать область Δ")
        self.SetStatusText("Выберите область интегрирования на графике (drag мышью)" if activate else "Готово")

    def on_select_integration_range(self, xmin, xmax):
        if not self.range_selection_enabled:
            return

        selection, spectrum = self.get_selected_spectrum()
        if spectrum is None:
            wx.MessageBox("Сначала выберите спектр в списке.", "Нет выбранного спектра", wx.OK | wx.ICON_INFORMATION)
            return

        if xmin == xmax:
            return

        left, right = (xmin, xmax) if xmin < xmax else (xmax, xmin)
        if self.selection_mode == "integral":
            spectrum["integration_range"] = (left, right)
            self.SetStatusText(f"Область интеграла выбрана: {left:.3f} .. {right:.3f}")
        elif self.selection_mode == "delta":
            spectrum["delta_range"] = (left, right)
            self.SetStatusText(f"Область Δ выбрана: {left:.3f} .. {right:.3f}")
        else:
            return

        self.range_selection_enabled = False
        self.selection_mode = None
        self.span_selector.set_active(False)
        self.select_integral_range_button.SetLabel("Выбрать область интеграла")
        self.select_delta_range_button.SetLabel("Выбрать область Δ")

        self.update_spectrum_list(selected_index=selection)
        self.render_displayed_spectra()
        self.show_spectrum_info(spectrum)

    def clear_integral_range_for_selected(self, event):
        selection, spectrum = self.get_selected_spectrum()
        if spectrum is None:
            wx.MessageBox("Сначала выберите спектр в списке.", "Нет выбранного спектра", wx.OK | wx.ICON_INFORMATION)
            return

        if self.range_selection_enabled and self.selection_mode == "integral":
            self.range_selection_enabled = False
            self.selection_mode = None
            if self.span_selector is not None:
                self.span_selector.set_active(False)
            self.select_integral_range_button.SetLabel("Выбрать область интеграла")

        self.update_spectrum_list(selected_index=selection)
        self.render_displayed_spectra()
        self.show_spectrum_info(spectrum)
        self.SetStatusText("Область интеграла очищена")

    def integrate_over_range(self, x, y, x_range):
        left, right = x_range
        mask = (x >= left) & (x <= right)
        indices = np.where(mask)[0]
        if indices.size < 2:
            return None

        x_seg = x[indices]
        y_seg = y[indices]
        dx = np.diff(x_seg)
        cumulative = np.concatenate(([0.0], np.cumsum((y_seg[:-1] + y_seg[1:]) * 0.5 * dx)))

        result = y.copy()
        result[indices] = cumulative
        return result, float(cumulative[-1])

    def apply_integral_to_selected(self, event):
        selection, spectrum = self.get_selected_spectrum()
        if spectrum is None:
            wx.MessageBox("Сначала выберите спектр в списке.", "Нет выбранного спектра", wx.OK | wx.ICON_INFORMATION)
            return

        x_range = spectrum.get("integration_range")
        if x_range is None:
            wx.MessageBox(
                "Сначала выберите область кнопкой 'Выбрать область интеграла'.",
                "Не выбрана область",
                wx.OK | wx.ICON_INFORMATION,
            )
            return

        order = spectrum.get("integral_order", 0)
        if order >= 2:
            wx.MessageBox("Интеграл уже применён дважды для этого спектра.", "Достигнут предел", wx.OK | wx.ICON_INFORMATION)
            return

        y = spectrum["y"]
        integrated_result = self.integrate_over_range(spectrum["x"], y, x_range)
        if integrated_result is None:
            wx.MessageBox(
                "В выбранной области недостаточно точек для интегрирования.",
                "Ошибка",
                wx.OK | wx.ICON_WARNING,
            )
            return

        integrated, integral_value = integrated_result

        spectrum["integral_history"].append({
            "y": y.copy(),
            "order": order,
            "last_integral_value": spectrum.get("last_integral_value"),
        })
        spectrum["y"] = integrated
        spectrum["integral_order"] = order + 1
        spectrum["last_integral_value"] = integral_value

        self.update_signal_metrics(spectrum)
        self.update_spectrum_list(selected_index=selection)
        self.render_displayed_spectra()
        self.show_spectrum_info(spectrum)
        self.SetStatusText(f"Интеграл I{spectrum['integral_order']}: {integral_value:.3f}")

    def undo_integral_for_selected(self, event):
        selection, spectrum = self.get_selected_spectrum()
        if spectrum is None:
            wx.MessageBox("Сначала выберите спектр в списке.", "Нет выбранного спектра", wx.OK | wx.ICON_INFORMATION)
            return

        history = spectrum.get("integral_history", [])
        if not history:
            wx.MessageBox("Для выбранного спектра нет применённого интеграла.", "Отмена не требуется", wx.OK | wx.ICON_INFORMATION)
            return

        last_state = history.pop()
        spectrum["y"] = last_state["y"]
        spectrum["integral_order"] = last_state["order"]
        spectrum["last_integral_value"] = last_state.get("last_integral_value")

        self.update_signal_metrics(spectrum)
        self.update_spectrum_list(selected_index=selection)
        self.render_displayed_spectra()
        self.show_spectrum_info(spectrum)
        self.SetStatusText("Интеграл отменён")


    def toggle_delta_range_selection(self, event):
        self.ensure_canvas()
        if self.span_selector is None:
            return

        activate = not (self.range_selection_enabled and self.selection_mode == "delta")
        self.range_selection_enabled = activate
        self.selection_mode = "delta" if activate else None
        self.span_selector.set_active(activate)

        self.select_delta_range_button.SetLabel("Отменить выбор Δ" if activate else "Выбрать область Δ")
        self.select_integral_range_button.SetLabel("Выбрать область интеграла")
        self.SetStatusText("Выберите область для Δ (drag мышью)" if activate else "Готово")

    def calculate_delta_for_selected(self, event):
        selection, spectrum = self.get_selected_spectrum()
        if spectrum is None:
            wx.MessageBox("Сначала выберите спектр в списке.", "Нет выбранного спектра", wx.OK | wx.ICON_INFORMATION)
            return

        d_range = spectrum.get("delta_range")
        if d_range is None:
            wx.MessageBox("Сначала выберите область кнопкой 'Выбрать область Δ'.", "Не выбрана область", wx.OK | wx.ICON_INFORMATION)
            return

        x = spectrum["x"]
        y = spectrum["y"]
        left, right = d_range
        mask = (x >= left) & (x <= right)
        idx = np.where(mask)[0]
        if idx.size < 2:
            wx.MessageBox("В выбранной области недостаточно точек для расчёта Δ.", "Ошибка", wx.OK | wx.ICON_WARNING)
            return

        x_seg = x[idx]
        y_seg = y[idx]
        spectrum["delta_height"] = float(np.max(y_seg) - np.min(y_seg))
        spectrum["delta_weight"] = float(np.trapezoid(y_seg, x_seg)) if hasattr(np, "trapezoid") else float(np.trapz(y_seg, x_seg))

        self.update_spectrum_list(selected_index=selection)
        self.render_displayed_spectra()
        self.show_spectrum_info(spectrum)
        self.SetStatusText(f"Δheight={spectrum['delta_height']:.3f}, Δweight={spectrum['delta_weight']:.3f}")

    def clear_spectrum_info(self):
        for key, _ in self.param_order:
            self.param_labels[key].SetLabel("N/A")
        self.Layout()

    def on_select_spectrum(self, event):
        selection = event.GetSelection()
        if selection == wx.NOT_FOUND or selection >= len(self.spectra):
            self.clear_spectrum_info()
            return

        self.show_spectrum_info(self.spectra[selection])

    def on_toggle_spectrum(self, event):
        selection = event.GetSelection()
        if selection == wx.NOT_FOUND or selection >= len(self.spectra):
            return

        spectrum_id = self.spectra[selection]["id"]
        if self.spectrum_list.IsChecked(selection):
            self.displayed_spectra.add(spectrum_id)
        else:
            self.displayed_spectra.discard(spectrum_id)

        self.render_displayed_spectra()
        self.show_spectrum_info(self.spectra[selection])


    def update_signal_metrics(self, spectrum):
        params = spectrum.get("params", {})
        y = spectrum.get("y")
        signal_level = float(y.max() - y.min()) if y is not None and len(y) else 0.0
        noise_level = params.get("noise_level")
        snr = signal_level / noise_level if noise_level not in (None, 0) else None
        params["signal_level"] = signal_level
        params["snr"] = snr

    def apply_baseline_to_selected(self, event):
        selection = self.spectrum_list.GetSelection()
        if selection == wx.NOT_FOUND or selection >= len(self.spectra):
            wx.MessageBox("Сначала выберите спектр в списке.", "Нет выбранного спектра", wx.OK | wx.ICON_INFORMATION)
            return

        spectrum = self.spectra[selection]
        x = spectrum["x"]
        y = spectrum.get("raw_y", spectrum["y"])

        if len(x) < 2 or len(y) < 2:
            wx.MessageBox("Недостаточно точек для построения базовой линии.", "Ошибка", wx.OK | wx.ICON_WARNING)
            return

        baseline = y[0] + (y[-1] - y[0]) * (x - x[0]) / (x[-1] - x[0]) if x[-1] != x[0] else y[0]
        spectrum["y"] = y - baseline
        spectrum["baseline_applied"] = True
        spectrum["integral_order"] = 0
        spectrum["integral_history"] = []
        spectrum["last_integral_value"] = None

        self.update_signal_metrics(spectrum)
        self.update_spectrum_list(selected_index=selection)
        self.render_displayed_spectra()
        self.show_spectrum_info(spectrum)

    def undo_baseline_for_selected(self, event):
        selection = self.spectrum_list.GetSelection()
        if selection == wx.NOT_FOUND or selection >= len(self.spectra):
            wx.MessageBox("Сначала выберите спектр в списке.", "Нет выбранного спектра", wx.OK | wx.ICON_INFORMATION)
            return

        spectrum = self.spectra[selection]
        if not spectrum.get("baseline_applied"):
            wx.MessageBox(
                "Для выбранного спектра базовая линия ещё не применялась.",
                "Отмена не требуется",
                wx.OK | wx.ICON_INFORMATION,
            )
            return

        spectrum["y"] = spectrum["raw_y"].copy()
        spectrum["baseline_applied"] = False
        spectrum["integral_order"] = 0
        spectrum["integral_history"] = []
        spectrum["last_integral_value"] = None

        self.update_signal_metrics(spectrum)
        self.update_spectrum_list(selected_index=selection)
        self.render_displayed_spectra()
        self.show_spectrum_info(spectrum)

    def delete_spectrum(self, event):
        selection = self.spectrum_list.GetSelection()
        if selection == wx.NOT_FOUND or selection >= len(self.spectra):
            return

        spectrum_id = self.spectra[selection]["id"]
        self.displayed_spectra.discard(spectrum_id)
        del self.spectra[selection]

        self.update_spectrum_list()
        self.render_displayed_spectra()

        if self.spectra:
            new_selection = min(selection, len(self.spectra) - 1)
            self.spectrum_list.SetSelection(new_selection)
            self.show_spectrum_info(self.spectra[new_selection])
        else:
            self.clear_spectrum_info()


if __name__ == '__main__':
    app = wx.App(False)
    frame = EPRApp(None, "EPR Spectrum Viewer")
    app.MainLoop()