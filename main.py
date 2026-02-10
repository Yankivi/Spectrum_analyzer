import wx
import matplotlib.pyplot as plt
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
from spectrum_loader import load_and_reconstruct_spectra  # Импортируем функцию загрузки спектров


class EPRApp(wx.Frame):
    def __init__(self, parent, title):
        super(EPRApp, self).__init__(parent, title=title, size=(1500, 1000))

        self.spectra = []  # Список загруженных спектров
        self.displayed_spectra = []  # Список отображаемых спектров (тех, которые уже отрисованы)

        # Основной макет
        panel = wx.Panel(self)
        layout = wx.BoxSizer(wx.VERTICAL)

        # Кнопки для загрузки и обработки спектров
        self.load_button = wx.Button(panel, label="Загрузить спектры")
        self.load_button.Bind(wx.EVT_BUTTON, self.load_spectrum)
        layout.Add(self.load_button, 0, wx.ALL, 5)

        # Кнопка для удаления спектра
        self.delete_button = wx.Button(panel, label="Удалить спектры")
        self.delete_button.Bind(wx.EVT_BUTTON, self.delete_spectrum)
        layout.Add(self.delete_button, 0, wx.ALL, 5)

        # Список загруженных спектров (с возможностью мульти-выбора)
        self.spectrum_list = wx.ListBox(panel, style=wx.LB_MULTIPLE)
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
        # Фильтр для выбора .json файлов
        wildcard = "JSON Files (*.json)|*.json|All Files (*.*)|*.*"  # Фильтры для файлов
        file_dialog = wx.FileDialog(self, "Открыть файл", wildcard=wildcard,
                                    style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST | wx.FD_MULTIPLE)

        if file_dialog.ShowModal() == wx.ID_OK:
            file_paths = file_dialog.GetPaths()  # Получаем все выбранные файлы

            # Загружаем спектры только для выбранных файлов
            for file_path in file_paths:
                spectra = load_and_reconstruct_spectra(file_path)
                self.spectra.extend(spectra)

            self.update_spectrum_list()
            if self.spectra:
                # Показываем все загруженные спектры, чтобы не требовать мультивыбор вручную.
                self.replot_selected_spectra(range(len(self.spectra)))

    def update_spectrum_list(self):
        self.spectrum_list.Clear()
        for _, _, filename in self.spectra:
            self.spectrum_list.Append(filename)

    def ensure_canvas(self):
        if self.canvas is None:
            fig, self.ax = plt.subplots(figsize=(8, 5))
            self.canvas = FigureCanvas(self.canvas_panel, -1, fig)
            canvas_layout = wx.BoxSizer(wx.VERTICAL)
            canvas_layout.Add(self.canvas, 1, wx.EXPAND)
            self.canvas_panel.SetSizer(canvas_layout)
        else:
            self.ax = self.canvas.GetFigure().axes[0]

    def plot_spectrum(self, spectrum_data):
        x, y, filename = spectrum_data
        self.ax.plot(x, y, label=filename)

    def replot_selected_spectra(self, selections):
        selections = list(selections)
        if not selections:
            self.clear_plot()
            return

        self.ensure_canvas()
        self.ax.clear()
        self.displayed_spectra = []

        for selection in selections:
            spectrum_data = self.spectra[selection]
            self.plot_spectrum(spectrum_data)
            self.displayed_spectra.append(spectrum_data[2])

        self.ax.set_xlabel("Магнитное поле (mT)")
        self.ax.set_ylabel("Интенсивность сигнала (a.u.)")
        self.ax.set_title("ЭПР-спектры")
        self.ax.legend()
        self.ax.grid(True)
        self.canvas.draw()

    def clear_plot(self):
        if self.ax is not None:
            self.ax.clear()
            self.canvas.draw()
        self.displayed_spectra = []

    def on_select_spectrum(self, event):
        # Получаем все индексы выбранных спектров
        selections = self.spectrum_list.GetSelections()
        self.replot_selected_spectra(selections)

    def delete_spectrum(self, event):
        # Получаем индексы всех выбранных спектров
        selections = self.spectrum_list.GetSelections()  # Список всех выбранных элементов

        if selections:  # Если есть выбранные спектры
            # Удаляем спектры из списка
            for selection in sorted(selections, reverse=True):  # Удаляем по порядку (от последнего к первому)
                del self.spectra[selection]  # Удаляем спектр из списка
                self.spectrum_list.Delete(selection)  # Удаляем из списка на экране

            self.update_spectrum_list()  # Обновляем список после удаления
            self.clear_plot()


if __name__ == '__main__':
    app = wx.App(False)
    frame = EPRApp(None, "EPR Spectrum Viewer")
    app.MainLoop()
