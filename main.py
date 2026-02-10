import wx
import matplotlib.pyplot as plt
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
from spectrum_loader import load_and_reconstruct_spectra  # Импортируем функцию загрузки спектров


class EPRApp(wx.Frame):
    def __init__(self, parent, title):
        super(EPRApp, self).__init__(parent, title=title, size=(1500, 1000))

        self.spectra = []  # Список словарей: {id, x, y, filename}
        self.displayed_spectra = set()  # Набор id отображаемых спектров
        self.next_spectrum_id = 1

        # Основной макет
        panel = wx.Panel(self)
        layout = wx.BoxSizer(wx.VERTICAL)

        # Кнопки для загрузки и обработки спектров
        self.load_button = wx.Button(panel, label="Загрузить спектры")
        self.load_button.Bind(wx.EVT_BUTTON, self.load_spectrum)
        layout.Add(self.load_button, 0, wx.ALL, 5)

        # Кнопка для удаления спектра
        self.delete_button = wx.Button(panel, label="Удалить спектр")
        self.delete_button.Bind(wx.EVT_BUTTON, self.delete_spectrum)
        layout.Add(self.delete_button, 0, wx.ALL, 5)

        # Список загруженных спектров (клик по строке переключает отображение)
        self.spectrum_list = wx.ListBox(panel)
        self.spectrum_list.Bind(wx.EVT_LISTBOX, self.on_select_spectrum)
        layout.Add(self.spectrum_list, 1, flag=wx.EXPAND | wx.ALL, border=5)

        # Раздел для отображения графика
        self.canvas_panel = wx.Panel(panel)
        self.canvas = None  # Здесь будет храниться график
        self.ax = None  # Оси для графика

        layout.Add(self.canvas_panel, 3, flag=wx.EXPAND | wx.ALL, border=5)

        # Раздел с параметрами спектра
        self.spectrum_info = wx.StaticText(panel, label="Параметры спектра")
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
            file_paths = file_dialog.GetPaths()

            for file_path in file_paths:
                loaded = load_and_reconstruct_spectra(file_path)
                for x, y, filename in loaded:
                    spectrum_id = self.next_spectrum_id
                    self.next_spectrum_id += 1
                    self.spectra.append({"id": spectrum_id, "x": x, "y": y, "filename": filename})
                    self.displayed_spectra.add(spectrum_id)

            self.update_spectrum_list()
            self.render_displayed_spectra()

    def ensure_canvas(self):
        if self.canvas is None:
            fig, self.ax = plt.subplots(figsize=(8, 5))
            self.canvas = FigureCanvas(self.canvas_panel, -1, fig)
            canvas_layout = wx.BoxSizer(wx.VERTICAL)
            canvas_layout.Add(self.canvas, 1, wx.EXPAND)
            self.canvas_panel.SetSizer(canvas_layout)
        else:
            self.ax = self.canvas.GetFigure().axes[0]

    def update_spectrum_list(self, selected_index=None):
        self.spectrum_list.Clear()
        for spectrum in self.spectra:
            marker = "●" if spectrum["id"] in self.displayed_spectra else "○"
            self.spectrum_list.Append(f"{marker} {spectrum['filename']}")

        if selected_index is not None and 0 <= selected_index < len(self.spectra):
            self.spectrum_list.SetSelection(selected_index)

    def render_displayed_spectra(self):
        self.ensure_canvas()
        self.ax.clear()

        if self.spectra:
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

    def on_select_spectrum(self, event):
        selection = event.GetSelection()
        if selection == wx.NOT_FOUND or selection >= len(self.spectra):
            return

        spectrum_id = self.spectra[selection]["id"]
        if spectrum_id in self.displayed_spectra:
            self.displayed_spectra.remove(spectrum_id)
        else:
            self.displayed_spectra.add(spectrum_id)

        self.update_spectrum_list(selected_index=selection)
        self.render_displayed_spectra()

    def delete_spectrum(self, event):
        selection = self.spectrum_list.GetSelection()
        if selection == wx.NOT_FOUND or selection >= len(self.spectra):
            return

        spectrum_id = self.spectra[selection]["id"]
        if spectrum_id in self.displayed_spectra:
            self.displayed_spectra.remove(spectrum_id)

        del self.spectra[selection]
        self.update_spectrum_list()
        self.render_displayed_spectra()


if __name__ == '__main__':
    app = wx.App(False)
    frame = EPRApp(None, "EPR Spectrum Viewer")
    app.MainLoop()
