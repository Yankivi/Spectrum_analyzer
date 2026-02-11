import wx
import matplotlib.pyplot as plt
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
from spectrum_loader import load_and_reconstruct_spectra


class EPRApp(wx.Frame):
    def __init__(self, parent, title):
        super(EPRApp, self).__init__(parent, title=title, size=(1500, 1000))

        self.spectra = []  # Список словарей: {id, x, y, filename, params}
        self.displayed_spectra = set()  # Набор id отображаемых спектров
        self.next_spectrum_id = 1

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
                        {"id": spectrum_id, "x": x, "y": y.copy(), "raw_y": y.copy(), "filename": filename, "params": params}
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
            canvas_layout = wx.BoxSizer(wx.VERTICAL)
            canvas_layout.Add(self.canvas, 1, wx.EXPAND)
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

    def update_spectrum_list(self, selected_index=None):
        self.spectrum_list.Clear()
        for index, spectrum in enumerate(self.spectra):
            self.spectrum_list.Append(spectrum["filename"])
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
            precision = 0 if key == "points" else 3
            self.param_labels[key].SetLabel(self.format_param(value, precision=precision))
        self.Layout()

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

        self.update_signal_metrics(spectrum)
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