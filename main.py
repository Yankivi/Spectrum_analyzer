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
        layout = wx.BoxSizer(wx.VERTICAL)

        self.load_button = wx.Button(panel, label="Загрузить спектры")
        self.load_button.Bind(wx.EVT_BUTTON, self.load_spectrum)
        layout.Add(self.load_button, 0, wx.ALL, 5)

        self.delete_button = wx.Button(panel, label="Удалить спектр")
        self.delete_button.Bind(wx.EVT_BUTTON, self.delete_spectrum)
        layout.Add(self.delete_button, 0, wx.ALL, 5)

        # Чекбокс управляет видимостью, клик по строке показывает параметры.
        self.spectrum_list = wx.CheckListBox(panel)
        self.spectrum_list.Bind(wx.EVT_CHECKLISTBOX, self.on_toggle_spectrum)
        self.spectrum_list.Bind(wx.EVT_LISTBOX, self.on_select_spectrum)
        layout.Add(self.spectrum_list, 1, flag=wx.EXPAND | wx.ALL, border=5)

        self.canvas_panel = wx.Panel(panel)
        self.canvas = None
        self.figure = None
        self.ax = None
        layout.Add(self.canvas_panel, 3, flag=wx.EXPAND | wx.ALL, border=5)

        self.spectrum_info = wx.StaticText(panel, label="Параметры спектра: не выбран")
        layout.Add(self.spectrum_info, 0, wx.ALL, 5)

        panel.SetSizer(layout)
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
            for file_path in file_dialog.GetPaths():
                loaded = load_and_reconstruct_spectra(file_path)
                for x, y, filename, params in loaded:
                    spectrum_id = self.next_spectrum_id
                    self.next_spectrum_id += 1
                    self.spectra.append(
                        {"id": spectrum_id, "x": x, "y": y, "filename": filename, "params": params}
                    )
                    self.displayed_spectra.add(spectrum_id)

            self.update_spectrum_list()
            self.render_displayed_spectra()

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
        if isinstance(value, (int, float)):
            return f"{value:.{precision}f}"
        return str(value)

    def show_spectrum_info(self, spectrum):
        params = spectrum.get("params", {})
        info_text = (
            f"Параметры спектра: {spectrum['filename']}\n"
            f"Center field: {self.format_param(params.get('center_field'))}\n"
            f"Sweep width: {self.format_param(params.get('sweep_width'))}\n"
            f"Points: {self.format_param(params.get('points'), precision=0)}\n"
            f"Sweep time: {self.format_param(params.get('sweep_time'))}\n"
            f"Modulation amplitude: {self.format_param(params.get('modulation_amplitude'))}\n"
            f"Attenuation: {self.format_param(params.get('attenuation'))}\n"
            f"Noise level: {self.format_param(params.get('noise_level'))}\n"
            f"Signal level: {self.format_param(params.get('signal_level'))}\n"
            f"SNR: {self.format_param(params.get('snr'))}"
        )
        self.spectrum_info.SetLabel(info_text)

    def on_select_spectrum(self, event):
        selection = event.GetSelection()
        if selection == wx.NOT_FOUND or selection >= len(self.spectra):
            self.spectrum_info.SetLabel("Параметры спектра: не выбран")
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
            self.spectrum_info.SetLabel("Параметры спектра: не выбран")


if __name__ == '__main__':
    app = wx.App(False)
    frame = EPRApp(None, "EPR Spectrum Viewer")
    app.MainLoop()