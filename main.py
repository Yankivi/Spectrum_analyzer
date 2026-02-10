import wx
import os
import matplotlib.pyplot as plt
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
from spectrum_loader import load_and_reconstruct_spectra  # Импортируем функцию загрузки спектров
import numpy as np


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
                folder_path = os.path.dirname(file_path)  # Получаем путь к папке с файлом
                spectra = load_and_reconstruct_spectra(file_path)
                self.spectra.extend(spectra)

            self.update_spectrum_list()
            if self.spectra:
                self.plot_spectrum(self.spectra[0])  # Отобразить первый спектр

    def update_spectrum_list(self):
        self.spectrum_list.Clear()
        for _, _, filename in self.spectra:
            self.spectrum_list.Append(filename)

    def plot_spectrum(self, spectrum_data):
        x, y, filename = spectrum_data

        # Проверяем, был ли этот спектр уже отрисован
        if filename in self.displayed_spectra:
            # Если спектр уже был на графике, ничего не делаем
            print(f"Spectra {filename} already displayed.")
            return

        # Если это новый спектр, добавляем его на график
        if self.canvas is None:
            # Если canvas не был инициализирован, создаём новый график
            fig, self.ax = plt.subplots(figsize=(8, 5))  # Создаём фигуру и оси
            self.canvas = FigureCanvas(self.canvas_panel, -1, fig)
        else:
            # Если график уже есть, используем существующие оси
            self.ax = self.canvas.GetFigure().axes[0]

        # Добавляем данные спектра на график
        self.ax.plot(x, y, label=filename)
        self.ax.set_xlabel("Магнитное поле (mT)")
        self.ax.set_ylabel("Интенсивность сигнала (a.u.)")
        self.ax.set_title("ЭПР-спектры")
        self.ax.legend()
        self.ax.grid(True)

        # Добавляем спектр в список отображаемых
        self.displayed_spectra.append(filename)
        self.canvas.draw()

    def on_select_spectrum(self, event):
        # Получаем все индексы выбранных спектров
        selections = self.spectrum_list.GetSelections()

        if selections:  # Если есть хотя бы один выбранный спектр
            for selection in selections:
                spectrum_data = self.spectra[selection]
                self.plot_spectrum(spectrum_data)  # Отображаем спектр на том же графике

    def delete_spectrum(self, event):
        # Получаем индексы всех выбранных спектров
        selections = self.spectrum_list.GetSelections()  # Список всех выбранных элементов

        if selections:  # Если есть выбранные спектры
            # Удаляем спектры из списка
            for selection in sorted(selections, reverse=True):  # Удаляем по порядку (от последнего к первому)
                del self.spectra[selection]  # Удаляем спектр из списка
                self.spectrum_list.Delete(selection)  # Удаляем из списка на экране

            self.update_spectrum_list()  # Обновляем список после удаления
            self.displayed_spectra = []  # Очищаем список отображаемых спектров


if __name__ == '__main__':
    app = wx.App(False)
    frame = EPRApp(None, "EPR Spectrum Viewer")
    app.MainLoop()
