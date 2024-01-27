# Import necessary modules
import sys  # System-specific parameters and functions
from os import path  # Functions to manipulate file paths
import numpy as np  # Numerical operations library
import pandas as pd
from PyQt6 import QtWidgets
from PyQt6.QtWidgets import *  # PyQt6 GUI components
from PyQt6.QtCore import *  # Core PyQt6 classes
from PyQt6.uic import loadUiType 
import pyqtgraph as pg
from PyQt6.QtGui import QKeySequence, QShortcut
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet
import scipy.signal as signal
import random
import pickle


# Load the UI file (returns class types for UI and base class)
FORM_CLASS, _ = loadUiType(path.join(path.dirname(__file__), "design.ui"))

class MainApp(QMainWindow, FORM_CLASS):
    # Initialization method
    def __init__(self, parent=None):
        super(MainApp, self).__init__(parent)
        QMainWindow.__init__(self)

        # Load and set up UI defined in mainwindow-2.ui
        self.setupUi(self)
        self.setWindowTitle("Multi-Port, Multi-Channel Signal Viewer")
        self.setFixedSize(self.size())

        # Create PlotWidgets for graphs
        self.plot_widget1 = pg.PlotWidget()
        self.plot_widget2 = pg.PlotWidget()
        self.graph1Layout.addWidget(self.plot_widget1)
        self.graph2Layout.addWidget(self.plot_widget2)

        # Initialize PyQtGraph plots
        self.init_pyqtgraph1()
        self.init_pyqtgraph2()

        self.verticalScrollBar_graph1.setEnabled(False)
        self.verticalScrollBar_graph1.setValue(self.verticalScrollBar_graph1.maximum())

        self.verticalScrollBar_graph2.setEnabled(False)
        self.verticalScrollBar_graph2.setValue(self.verticalScrollBar_graph2.maximum())

        self.cineSpeedScoller.setValue(50)
        self.update_interval_ms = 200  # Interval for signal updates in milliseconds

        # For graph 1
        self.signal_data_graph1 = []
        self.is_playing_graph1 = False
        self.current_index_graph1 = 0
        self.play_state_graph1 = False
        self.zoom_factor_graph1 = 1.0
        self.playback_speed_graph1 = 1.0
        self.update_interval_graph1 = 300

        # For graph 2
        self.signal_data_graph2 = []
        self.is_playing_graph2 = False
        self.current_index_graph2 = 0
        self.play_state_graph2 = False
        self.zoom_factor_graph2 = 1.0
        self.playback_speed_graph2 = 1.0
        self.update_interval_graph2 = 300


        # Initialize variables for selected channels and graph states
        self.lastSelectedComboBox = None  # Keeps track of the last selected combo box. Initialized to None.
        self.graph1Files = []  # List to store file paths for graph 1
        self.graph2Files = []  # List to store file paths for graph 2
        self.currentGraph = None  # Start with no default graph selected
        self.graph1ChannelNames = []  # List to store channel names for graph 1
        self.graph2ChannelNames = []  # List to store channel names for graph 2
        self.graph1ChannelMapping = {}  # Dictionary to store mapping for graph 1 (channel name to file path)
        self.graph2ChannelMapping = {}  # Dictionary to store mapping for graph 2 (channel name to file path)
        self.hidden_channels_graph1 = []  # List to store hidden channels for graph 1
        self.hidden_channels_graph2 = []  # List to store hidden channels for graph 2
        self.checkbox_states_graph1 = {}
        self.checkbox_states_graph2 = {}
        self.graph1Statistics = {}  # Container for graph 1 statistics
        self.graph2Statistics = {}  # Container for graph 2 statistics

        # Connect GUI elements to methods
        self.channelsComboBox.setCurrentIndex(-1)
        self.browseButton.clicked.connect(self.open_file)
        self.graph1Radio.toggled.connect(lambda: self.updateCurrentGraph(1))
        self.graph2Radio.toggled.connect(lambda: self.updateCurrentGraph(2))
        self.channelsComboBox.currentIndexChanged.connect(self.onChannelSelectionChanged)
        self.editChannelNameButton.clicked.connect(self.editChannelNameButtonClicked)
        self.play_pauseButton.clicked.connect(self.toggle_play_pause_signal)
        self.rewindButton.clicked.connect(self.rewind_signal)
        self.zoomInButton.clicked.connect(self.zoom_in_signal)
        self.zoomOutButton.clicked.connect(self.zoom_out_signal)
        self.selectChannelColorButton.clicked.connect(self.select_channel_color)
        self.verticalScrollBar_graph1.valueChanged.connect(self.vertical_scroll_graph1)
        self.verticalScrollBar_graph2.valueChanged.connect(self.vertical_scroll_graph2)
        self.hideChannelCheckBox.stateChanged.connect(self.hide_channel)
        self.cineSpeedScoller.valueChanged.connect(self.update_playback_speed)
        self.pdfButton.clicked.connect(self.exportPDF)
        self.linkgraphsCheckbox.stateChanged.connect(self.link_graphs)
        self.channelsComboBox.currentIndexChanged.connect(self.update_legend_for_current_channel)


        # Define keyboard shortcuts for zooming in and out
        zoom_in_shortcut = QShortcut(QKeySequence("+"), self)
        zoom_out_shortcut = QShortcut(QKeySequence("-"), self)

        zoom_in_shortcut.activated.connect(self.zoom_in_signal)
        zoom_out_shortcut.activated.connect(self.zoom_out_signal)

        self.colors_graph1 = ['r', 'g', 'b', 'y', 'm', 'c']  # Define colors for graph 1 signals
        self.colors_graph2 = ['m', 'y', 'c', 'r', 'g', 'b']  # Define colors for graph 2 signals

        self.timer_graph1 = self.create_timer()
        self.timer_graph2 = self.create_timer()
        self.timer = self.create_timer()

        self.legend_items_dict_graph1 = {}
        self.legend_items_dict_graph2 = {}

    def init_pyqtgraph1(self):
        self.plot_widget1.setBackground('k')  # Set the background color to black
        # self.plot1 = self.plot_widget1.plot(pen='c', width=2)  # Create a plot for graph 1 with cyan color and a width of 2
        self.view_box1 = self.plot_widget1.getViewBox()
        self.view_box1.setLimits(xMin=0)  # Set the initial visible limits for graph 1
        self.view_box1.setMouseEnabled(x=False, y=False)  # Allow panning in the x-direction only
        self.view_box1.setRange(xRange=[0, 10], yRange=[0,1], padding=0.05)  # Set the initial range (visible window) for graph 1
        self.plot_widget1.plotItem.getViewBox().scaleBy((6, 1))
        self.legend1 = self.plot_widget1.addLegend()

    def init_pyqtgraph2(self):
        self.plot_widget2.setBackground('k')  # Set the background color to black
        # self.plot2 = self.plot_widget2.plot(pen='c', width=2)  # Create a plot for graph 2 with cyan color and a width of 2
        self.view_box2 = self.plot_widget2.getViewBox()
        self.view_box2.setLimits(xMin=0)  # Set the initial visible limits for graph 2
        self.view_box2.setMouseEnabled(x=False, y=False)  # Allow panning in the x-direction only
        self.view_box2.setRange(xRange=[0, 10], yRange=[0,1], padding=0.05)  # Set the initial range (visible window) for graph 2
        self.plot_widget2.plotItem.getViewBox().scaleBy((6, 1))
        self.legend2 = self.plot_widget2.addLegend()


    def open_file(self):
        if not (self.graph1Radio.isChecked() or self.graph2Radio.isChecked()):
            # Display an error message if neither graph 1 nor graph 2 radio button is checked
            QMessageBox.critical(self, "Error", "Please choose Graph 1 or Graph 2 before browsing a file.")
            return

        file_name, _ = QFileDialog.getOpenFileName(self, "Open Signal File", "", "Signal Files (*.pkl);;All Files (*)")

        if file_name:
            if self.currentGraph == 1:
                self.verticalScrollBar_graph1.setEnabled(True)
                with open(file_name, 'rb') as file:
                    ecg_data = pickle.load(file)
                self.graph1Files.append(file_name)
                new_channel_name = f"Channel {len(self.graph1Files) + 1}"
                self.view_box1.setMouseEnabled(x=True, y=True)
            elif self.currentGraph == 2:
                self.verticalScrollBar_graph2.setEnabled(True)
                with open(file_name, 'rb') as file:
                    ecg_data = pickle.load(file)
                self.graph2Files.append(file_name)
                new_channel_name = f"Channel {len(self.graph2Files) + 1}"
                self.view_box2.setMouseEnabled(x=True, y=True)

            self.channelsComboBox.setCurrentIndex(self.channelsComboBox.findText(new_channel_name))  # Set the current index to the newly added channel
            self.load_signal_for_graph(ecg_data, self.graph1ChannelMapping if self.currentGraph == 1 else self.graph2ChannelMapping)
            self.timer.start(self.update_interval_ms)
            self.updateChannelsComboBox()
            self.update_legend_for_current_channel()

            # Automatically play the signal
            self.is_playing_graph1 = True
            self.is_playing_graph2 = True
            self.play_pauseButton.setText("Pause")


    def load_signal_for_graph(self, signal_data, graph_files):
        new_channel_name = f"Channel {len(graph_files) + 1}"
        self.channelsComboBox.addItem(new_channel_name)

        if self.currentGraph == 1:
            self.signal_data_graph1.append(signal_data)
            self.current_index_graph1 = 0
            self.graph1ChannelNames.append(new_channel_name)
            self.graph1ChannelMapping[new_channel_name] = signal_data
        elif self.currentGraph == 2:
            self.signal_data_graph2.append(signal_data)
            self.current_index_graph2 = 0
            self.graph2ChannelNames.append(new_channel_name)
            self.graph2ChannelMapping[new_channel_name] = signal_data

        self.updateChannelMapping()

    def vertical_scroll_graph1(self):
        max_magnitude = max(np.max(np.abs(signal)) for signal in self.signal_data_graph1)
        scrollbar_value = self.verticalScrollBar_graph1.value()
        vertical_offset = 1.0 - (scrollbar_value - self.verticalScrollBar_graph1.minimum()) / (self.verticalScrollBar_graph1.maximum() - self.verticalScrollBar_graph1.minimum())
        self.view_box1.setYRange(vertical_offset * max_magnitude, vertical_offset * max_magnitude + max_magnitude)

    def vertical_scroll_graph2(self):
        max_magnitude = max(np.max(np.abs(signal)) for signal in self.signal_data_graph2)
        scrollbar_value = self.verticalScrollBar_graph2.value()
        vertical_offset = 1.0 - (scrollbar_value - self.verticalScrollBar_graph2.minimum()) / (self.verticalScrollBar_graph2.maximum() - self.verticalScrollBar_graph2.minimum())
        self.view_box2.setYRange(vertical_offset * max_magnitude, vertical_offset * max_magnitude + max_magnitude)
        
    def update_playback_speed(self, value):
        # Define your desired range for speed control (adjust as needed)
        min_speed = 0.25  # Minimum playback speed
        max_speed = 2  # Maximum playback speed

        # Calculate the speed multiplier within the defined range
        speed_multiplier = min_speed + (max_speed - min_speed) * (value / 100.0)
        if self.linkgraphsCheckbox.isChecked():
            # Synchronize both graphs' playback speed
            self.playback_speed_graph1 = speed_multiplier
            self.playback_speed_graph2 = speed_multiplier
            self.update_interval_graph1 = int(self.update_interval_ms / speed_multiplier)
            self.update_interval_graph2 = int(self.update_interval_ms / speed_multiplier)
            # Synchronize both sliders
            self.cineSpeedScoller.setValue(value)
        else:
            if self.currentGraph == 1:
                self.playback_speed_graph1 = speed_multiplier
                self.update_interval_graph1 = int(self.update_interval_ms / speed_multiplier)
            elif self.currentGraph == 2:
                self.playback_speed_graph2 = speed_multiplier
                self.update_interval_graph2 = int(self.update_interval_ms / speed_multiplier)

    def calculate_slider_value(self, playback_speed):
        # Define your desired range for speed control (adjust as needed)
        min_speed = 0.1  # Minimum play back speed
        max_speed = 2  # Maximum playback speed

        # Calculate the slider value based on the playback speed
        slider_value = int(((playback_speed - min_speed) / (max_speed - min_speed)) * 100.0)

        return slider_value

    def link_graphs(self):
        if self.linkgraphsCheckbox.isChecked():
            self.play_pauseButton.setText("Pause")
            self.browseButton.setEnabled(False)
            self.cineSpeedScoller.setValue(50)

            self.current_index_graph1 = 0
            self.timer_graph1.start()
            self.is_playing_graph1 = True
            self.playback_speed_graph1 = 1.0
            
            self.current_index_graph2 = 0
            self.timer_graph2.start()
            self.is_playing_graph2 = True
            self.playback_speed_graph2 = 1.0

        else:
            self.browseButton.setEnabled(True)
            self.timer_graph1.stop()
            self.timer_graph2.stop()

    def plot_signal_graphs_linked(self):
        self.plot_widget1.clear()
        self.plot_widget2.clear()

        if self.signal_data_graph1:
            min_value = float('inf')
            max_value = float('-inf')

            for i, signal_data in enumerate(self.signal_data_graph1):
                start = max(0, self.current_index_graph1 - int(1000 * self.zoom_factor_graph1))
                end = min(len(signal_data), self.current_index_graph1 + int(1000 * self.zoom_factor_graph1))
                data_to_plot_graph1 = signal_data[start:self.current_index_graph1 + 1]

                if len(data_to_plot_graph1) > 0:
                    # Skip hidden channels
                    if i in self.hidden_channels_graph1:
                        continue

                    min_value = min(min_value, np.min(data_to_plot_graph1))
                    max_value = max(max_value, np.max(data_to_plot_graph1))

                    self.plot_widget1.plot(data_to_plot_graph1, pen=pg.mkPen(self.colors_graph1[i]))

            if min_value != float('inf') and max_value != float('-inf'):
                self.plot_widget1.setYRange(min_value, max_value)
            else:
                self.plot_widget1.setYRange(0, 1)

        else:
            self.plot_widget1.setYRange(0, 1)

        view_box_g1 = self.plot_widget1.getViewBox()
        current_view_g1 = view_box_g1.viewRange()[0]
        view_width_g1 = current_view_g1[1] - current_view_g1[0]
        new_view_x_g1 = [self.current_index_graph1 - view_width_g1 * 0.5, self.current_index_graph1 + view_width_g1 * 0.5]
        view_box_g1.setXRange(new_view_x_g1[0], new_view_x_g1[1], padding=0)

        if self.signal_data_graph2:
            min_value = float('inf')
            max_value = float('-inf')

            for i, signal_data in enumerate(self.signal_data_graph2):
                start = max(0, self.current_index_graph2 - int(1000 * self.zoom_factor_graph2))
                end = min(len(signal_data), self.current_index_graph2 + int(1000 * self.zoom_factor_graph2))
                data_to_plot_graph2 = signal_data[start:self.current_index_graph2 + 1]

                if len(data_to_plot_graph2) > 0:
                    # Skip hidden channels
                    if i in self.hidden_channels_graph2:
                        continue

                    min_value = min(min_value, np.min(data_to_plot_graph2))
                    max_value = max(max_value, np.max(data_to_plot_graph2))

                    self.plot_widget2.plot(data_to_plot_graph2, pen=pg.mkPen(self.colors_graph2[i]))

            if min_value != float('inf') and max_value != float('-inf'):
                self.plot_widget2.setYRange(min_value, max_value)
            else:
                self.plot_widget2.setYRange(0, 1)

        else:
            self.plot_widget2.setYRange(0, 1)

        view_box_g2 = self.plot_widget2.getViewBox()
        current_view_g2 = view_box_g2.viewRange()[0]
        view_width_g2 = current_view_g2[1] - current_view_g2[0]
        new_view_x_g2 = [self.current_index_graph2 - view_width_g2 * 0.5, self.current_index_graph2 + view_width_g2 * 0.5]
        view_box_g2.setXRange(new_view_x_g2[0], new_view_x_g2[1], padding=0)

    def plot_signal(self, plot_widget):
        plot_widget.clear()

        if self.currentGraph == 1:
            signal_data_list = self.signal_data_graph1
            current_index = self.current_index_graph1
            zoom_factor = self.zoom_factor_graph1
            colors = self.colors_graph1
            hidden_channels = self.hidden_channels_graph1
        elif self.currentGraph == 2:
            signal_data_list = self.signal_data_graph2
            current_index = self.current_index_graph2
            zoom_factor = self.zoom_factor_graph2
            colors = self.colors_graph2
            hidden_channels = self.hidden_channels_graph2
        else:
            return  # Do nothing if no graph is selected

        if signal_data_list:
            min_value = float('inf')
            max_value = float('-inf')

            for i, signal_data in enumerate(signal_data_list):
                start = max(0, current_index - int(1000 * zoom_factor))
                end = min(len(signal_data), current_index + int(1000 * zoom_factor))
                data_to_plot_temp = signal_data[start:current_index + 1]

                if len(data_to_plot_temp) > 0:
                    # Skip hidden channels
                    if i in hidden_channels:
                        continue

                    min_value = min(min_value, np.min(data_to_plot_temp))
                    max_value = max(max_value, np.max(data_to_plot_temp))

                    plot_widget.plot(data_to_plot_temp, pen=pg.mkPen(colors[i]))

            if min_value != float('inf') and max_value != float('-inf'):
                plot_widget.setYRange(min_value, max_value)
            else:
                plot_widget.setYRange(0, 1)

        else:
            plot_widget.setYRange(0, 1)

        view_box = plot_widget.getViewBox()
        current_view = view_box.viewRange()[0]
        view_width = current_view[1] - current_view[0]
        new_view_x = [current_index - view_width * 0.5, current_index + view_width * 0.5]
        view_box.setXRange(new_view_x[0], new_view_x[1], padding=0)

    def create_timer(self):
        timer = QTimer()
        timer.timeout.connect(self.timerEvent)
        # timer.start(self.update_interval_ms)
        return timer

    def timerEvent(self):
        if self.linkgraphsCheckbox.isChecked():
                self.timer_graph1.setInterval(self.update_interval_graph1)
                self.timer_graph2.setInterval(self.update_interval_graph2)
                if self.is_playing_graph1 and self.is_playing_graph2:
                    self.plot_signal_graphs_linked()
                    self.current_index_graph1 += 1
                    self.current_index_graph2 += 1
        else:
            # Continue handling the timerEvent as before for individual graphs
            if self.currentGraph == 1:
                self.timer.setInterval(self.update_interval_graph1)
                if self.is_playing_graph1:
                    self.plot_signal(self.plot_widget1)
                    self.current_index_graph1 += 1
            elif self.currentGraph == 2:
                self.timer.setInterval(self.update_interval_graph2)
                if self.is_playing_graph2:
                    self.plot_signal(self.plot_widget2)
                    self.current_index_graph2 += 1

    def zoom_in_signal(self):
        if self.linkgraphsCheckbox.isChecked():
            # Simultaneously control both graphs
            self.plot_widget1.plotItem.getViewBox().scaleBy((0.9, 1))
            self.plot_widget2.plotItem.getViewBox().scaleBy((0.9, 1))
        else:
            if self.graph1Radio.isChecked():
                self.plot_widget1.plotItem.getViewBox().scaleBy((0.9, 1))  # Zoom in horizontally for graph 1
            elif self.graph2Radio.isChecked():
                self.plot_widget2.plotItem.getViewBox().scaleBy((0.9, 1))  # Zoom in horizontally for graph 2

    def zoom_out_signal(self):
        if self.linkgraphsCheckbox.isChecked():
            # Simultaneously control both graphs
            self.plot_widget1.plotItem.getViewBox().scaleBy((1.1, 1))
            self.plot_widget2.plotItem.getViewBox().scaleBy((1.1, 1))
        else:
            if self.graph1Radio.isChecked():
                self.plot_widget1.plotItem.getViewBox().scaleBy((1.1, 1))  # Zoom out horizontally for graph 1
            elif self.graph2Radio.isChecked():
                self.plot_widget2.plotItem.getViewBox().scaleBy((1.1, 1))  # Zoom out horizontally for graph 2

    def toggle_play_pause_signal(self):

        if self.linkgraphsCheckbox.isChecked():
            self.is_playing_graph1 = not self.is_playing_graph1
            self.is_playing_graph2 = not self.is_playing_graph2
            self.update_play_pause_button(self.is_playing_graph1)
        else:
            if self.currentGraph == 1:
                self.is_playing_graph1 = not self.is_playing_graph1
                self.update_play_pause_button(self.is_playing_graph1)
            elif self.currentGraph == 2:
                self.is_playing_graph2 = not self.is_playing_graph2
                self.update_play_pause_button(self.is_playing_graph2)

    def update_play_pause_button(self, is_playing):
        if is_playing:
            self.play_pauseButton.setText("Pause")
        else:
            self.play_pauseButton.setText("Resume")

    def rewind_signal(self):
        if self.linkgraphsCheckbox.isChecked():
            # Simultaneously control both graphs
            self.current_index_graph1 = 0
            self.current_index_graph2 = 0
            self.plot_signal(self.plot_widget1)
            self.plot_signal(self.plot_widget2)
            self.is_playing_graph1 = True
            self.is_playing_graph2 = True
            self.play_pauseButton.setText("Pause")
        else:
            # Individual control for each graph
            if self.graph1Radio.isChecked():
                self.current_index_graph1 = 0
                self.plot_signal(self.plot_widget1)
                self.is_playing_graph1 = True
                self.play_pauseButton.setText("Pause")
            elif self.graph2Radio.isChecked():
                self.current_index_graph2 = 0
                self.plot_signal(self.plot_widget2)
                self.is_playing_graph2 = True
                self.play_pauseButton.setText("Pause")

    def select_channel_color(self):
        # Get the current channel name
        current_channel_name = self.channelsComboBox.currentText()

        # Determine which graph is currently active
        if self.currentGraph == 1:
            colors = self.colors_graph1
            legend_items_dict = self.legend_items_dict_graph1
        elif self.currentGraph == 2:
            colors = self.colors_graph2
            legend_items_dict = self.legend_items_dict_graph2
        else:
            return

        selected_index = self.channelsComboBox.currentIndex()  # Get the index of the selected channel

        # Open a color dialog to let the user choose a new color
        new_color = QColorDialog.getColor()

        if new_color.isValid():  # Check if a valid color is chosen
            # Update the color in the list for the current graph
            colors[selected_index] = new_color

            # Update the color of the legend item directly
            legend_item = legend_items_dict.get(current_channel_name)
            if legend_item:
                pen = pg.mkPen(new_color)
                legend_item.setPen(pen)

        # Update the legend immediately after changing the channel color
        self.update_legend_for_current_channel()

    def update_channel_color(self, index, color, colors_list, plot_widget):
        # Update the color of the selected channel in the list
        if 0 <= index < len(colors_list):
            colors_list[index] = color.name()

        # Update the plot with the new color
        self.plot_signal(plot_widget)

    def hide_channel(self, state):
        selected_channel = self.channelsComboBox.currentText()

        if selected_channel:
            # Determine the current graph and the appropriate checkbox states dictionary
            if self.currentGraph == 1:
                checkbox_states = self.checkbox_states_graph1
                hidden_channels = self.hidden_channels_graph1
                channel_names = self.graph1ChannelNames
                plot_widget = self.plot_widget1
            elif self.currentGraph == 2:
                checkbox_states = self.checkbox_states_graph2
                hidden_channels = self.hidden_channels_graph2
                channel_names = self.graph2ChannelNames
                plot_widget = self.plot_widget2

            # Update the checkbox state in the dictionary
            checkbox_states[selected_channel] = state

            # Update the hidden channels list based on the checkbox state
            channel_index = channel_names.index(selected_channel)
            if state:
                hidden_channels.append(channel_index)
            else:
                hidden_channels.remove(channel_index)
            self.plot_signal(plot_widget)

    def updateChannelsComboBox(self):
        self.channelsComboBox.clear()  # Clear the items in the channelsComboBox

        if self.currentGraph == 1:  # If the current graph is 1
            self.channelsComboBox.addItems(self.graph1ChannelNames)  # Add channel names for graph 1
        elif self.currentGraph == 2:  # If the current graph is 2
            self.channelsComboBox.addItems(self.graph2ChannelNames)  # Add channel names for graph 2

        self.channelsComboBox.currentIndexChanged.connect(self.update_legend_for_current_channel)

    def onChannelSelectionChanged(self, index):
        selected_channel = self.channelsComboBox.currentText()

        if selected_channel:
            # Get the current graph and the appropriate checkbox states dictionary
            if self.currentGraph == 1:
                file_path = self.graph1ChannelMapping.get(selected_channel)
                checkbox_states = self.checkbox_states_graph1
            elif self.currentGraph == 2:
                file_path = self.graph2ChannelMapping.get(selected_channel)
                checkbox_states = self.checkbox_states_graph2

            if file_path:
                self.enterFilePathLineEdit.setText(file_path)

                # Update the checkbox state based on the dictionary or set to unchecked
                checkbox_state = checkbox_states.get(selected_channel, False)
                self.hideChannelCheckBox.blockSignals(True)  # Block signals temporarily
                self.hideChannelCheckBox.setChecked(checkbox_state)
                self.hideChannelCheckBox.blockSignals(False)  # Unblock signals

    def updateChannelMapping(self):
        if self.currentGraph == 1:  # If the current graph is 1
            self.graph1ChannelMapping = {channel_name: file_path for channel_name, file_path in zip(self.graph1ChannelNames, self.graph1Files)}  # Update channel mapping for graph 1
        elif self.currentGraph == 2:  # If the current graph is 2
            self.graph2ChannelMapping = {channel_name: file_path for channel_name, file_path in zip(self.graph2ChannelNames, self.graph2Files)}  # Update channel mapping for graph 2

    def updateCurrentGraph(self, graph):
        if self.currentGraph == graph:
            return
        self.currentGraph = graph
        self.updateChannelsComboBox()

        if self.currentGraph == 1:
           if not self.signal_data_graph1:
               self.play_pauseButton.setText("Play / Pause")
           else:
                self.cineSpeedScoller.setValue(self.calculate_slider_value(self.playback_speed_graph1))
                self.update_play_pause_button(self.is_playing_graph1)
        elif self.currentGraph == 2:
            if not self.signal_data_graph2:
                self.play_pauseButton.setText("Play / Pause")
                self.cineSpeedScoller.setValue(self.calculate_slider_value(self.playback_speed_graph2))
            else:
                self.cineSpeedScoller.setValue(self.calculate_slider_value(self.playback_speed_graph2))
                self.update_play_pause_button(self.is_playing_graph2)

    def editChannelNameButtonClicked(self):
        new_channel_name = self.editChannelNameLineEdit.text().strip()  # Get the new channel name entered by the user

        if new_channel_name:  # If a new channel name is provided
            selected_index = self.channelsComboBox.currentIndex()  # Get the index of the selected channel

            if selected_index >= 0:  # If a channel is selected
                current_channel_name = self.channelsComboBox.currentText()  # Get the current channel name

                if self.currentGraph == 1:
                    # Update the channel name in the list for graph 1
                    self.graph1ChannelNames[selected_index] = new_channel_name
                    self.graph1ChannelMapping[new_channel_name] = self.graph1ChannelMapping.pop(current_channel_name, None)

                    # Update the displayed channel name in the channelsComboBox
                    self.channelsComboBox.setItemText(selected_index, new_channel_name)

                    # Update the legend item name directly
                    legend_item = self.legend_items_dict_graph1.get(current_channel_name)
                    if legend_item:
                        legend_item.opts['name'] = new_channel_name

                elif self.currentGraph == 2:
                    # Update the channel name in the list for graph 2
                    self.graph2ChannelNames[selected_index] = new_channel_name
                    self.graph2ChannelMapping[new_channel_name] = self.graph2ChannelMapping.pop(current_channel_name, None)

                    # Update the displayed channel name in the channelsComboBox
                    self.channelsComboBox.setItemText(selected_index, new_channel_name)

                    # Update the legend item name directly
                    legend_item = self.legend_items_dict_graph2.get(current_channel_name)
                    if legend_item:
                        legend_item.opts['name'] = new_channel_name

            # Clear the text in the editChannelNameLineEdit
            self.editChannelNameLineEdit.clear()

        # Update the legend immediately after editing
        self.update_legend_for_current_channel()



    def update_legend_for_current_channel(self):

        # Determine which graph is currently active
        if self.currentGraph == 1:
            legend = self.legend1
            colors = self.colors_graph1
            channel_names = self.graph1ChannelNames
            legend_items_dict = self.legend_items_dict_graph1
        elif self.currentGraph == 2:
            legend = self.legend2
            colors = self.colors_graph2
            channel_names = self.graph2ChannelNames
            legend_items_dict = self.legend_items_dict_graph2
        else:
            return

        # Clear existing items from the legend
        legend.clear()

        # Update the legend items dictionary
        legend_items_dict.clear()

        # Iterate over channel names and update the legend
        for i, channel_name in enumerate(channel_names):
            color = colors[i]
            pen = pg.mkPen(color)

            # Create a new item for each channel and add it to the legend
            item = pg.PlotDataItem(pen=pen, name=channel_name)
            legend.addItem(item, channel_name)

            # Update the legend items dictionary
            legend_items_dict[channel_name] = item

    def calculate_statistics(self, file_path):
        # Read the data from the file
        if file_path.endswith('.dat'):
            data = pd.read_csv(file_path, delimiter='\t')  # Assuming data is tab-separated
        elif file_path.endswith('.csv'):
            data = pd.read_csv(file_path)  # Assuming data is comma-separated
        else:
            raise ValueError("Unsupported file format. Only .dat and .csv files are supported.")

        # Calculate statistics for each column (signal)
        statistics = {}
        for column in data.columns:
            mean = data[column].mean()
            std_dev = data[column].std()
            duration = len(data)  # Assuming each row corresponds to a time point
            min_value = data[column].min()
            max_value = data[column].max()

            statistics[column] = {
                'Mean': mean,
                'Standard Deviation': std_dev,
                'Duration': duration,
                'Min Value': min_value,
                'Max Value': max_value
            }

        return statistics

    def generateStats(self):
        # Store the current selection
        temp_selection = 1 if self.graph1Radio.isChecked() else 2

        # Toggle to graph 1
        self.graph1Radio.setChecked(True)

        # Gather statistics for graph 1
        statistics_container1 = {}  # Create an empty container to hold statistics
        for index in range(self.channelsComboBox.count()):
            channel_name = self.channelsComboBox.itemText(index)
            file_path = self.graph1ChannelMapping.get(channel_name)

            if file_path:
                # Calculate statistics
                statistics1 = self.calculate_statistics(file_path)

                # Create a dictionary to hold information about the channel
                channel_info = {
                    'Name': channel_name,
                    'Graph': 1,
                    'Statistics': statistics1
                }

                # Add the channel info to the container
                statistics_container1[channel_name] = channel_info

        # Update graph 1 statistics
        self.graph1Statistics = statistics_container1

        # Toggle to graph 2
        self.graph2Radio.setChecked(True)

        # Gather statistics for graph 2
        statistics_container2 = {}  # Create an empty container to hold statistics
        for index in range(self.channelsComboBox.count()):
            channel_name = self.channelsComboBox.itemText(index)
            file_path = self.graph2ChannelMapping.get(channel_name)

            if file_path:
                # Calculate statistics
                statistics2 = self.calculate_statistics(file_path)

                # Create a dictionary to hold information about the channel
                channel_info = {
                    'Name': channel_name,
                    'Graph': 2,
                    'Statistics': statistics2
                }

                # Add the channel info to the container
                statistics_container2[channel_name] = channel_info

        # Update graph 2 statistics
        self.graph2Statistics = statistics_container2
        
        print(f"Graph 1 Statistics: {self.graph1Statistics}")
        print(f"Graph 2 Statistics: {self.graph2Statistics}")

        # Return to the original selection
        if temp_selection == 1:
            self.graph1Radio.setChecked(True)
        else:
            self.graph2Radio.setChecked(True)

    def generateSnapshots(self):
        # Store the current selection
        temp_selection = 1 if self.graph1Radio.isChecked() else 2

        # Toggle to the first graph
        self.graph1Radio.setChecked(True)

        # Get the snapshots of plot_widget1 and plot_widget2
        image1 = self.plot_widget1.grab()
        image1.save('image1.png', 'png')  # Save the QPixmap as a PNG file

        image2 = self.plot_widget2.grab()
        image2.save('image2.png', 'png')  # Save the QPixmap as a PNG file

        # Return to the original selection
        if temp_selection == 1:
            self.graph1Radio.setChecked(True)
        else:
            self.graph2Radio.setChecked(True)

        return 'image1.png', 'image2.png'  # Return the file paths

    def generateTables(self,graph1Statistics, graph2Statistics):

        # Define the data for the tables
        data1 = [['Channel', 'Graph', 'Mean', 'Std Dev', 'Duration', 'Min Value', 'Max Value']]
        data2 = [['Channel', 'Graph', 'Mean', 'Std Dev', 'Duration', 'Min Value', 'Max Value']]

        for channel, stats in graph1Statistics.items():
            channel_stats = stats.get('Statistics', {}).get('0.000000', {})  # Extract statistics for channel '0.000000'
            data1.append([
                channel,
                stats['Graph'],
                f"{channel_stats.get('Mean', 0):.4f}",
                f"{channel_stats.get('Standard Deviation', 0):.4f}",
                channel_stats.get('Duration', ''),
                f"{channel_stats.get('Min Value', 0):.4f}",
                f"{channel_stats.get('Max Value', 0):.4f}"
            ])

        for channel, stats in graph2Statistics.items():
            channel_stats = stats.get('Statistics', {}).get('0.000000', {})  # Extract statistics for channel '0.000000'
            data2.append([
                channel,
                stats['Graph'],
                f"{channel_stats.get('Mean', 0):.4f}",
                f"{channel_stats.get('Standard Deviation', 0):.4f}",
                channel_stats.get('Duration', ''),
                f"{channel_stats.get('Min Value', 0):.4f}",
                f"{channel_stats.get('Max Value', 0):.4f}"
            ])


        # Create the tables and style them
        table1 = Table(data1)
        table1.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                                ('GRID', (0, 0), (-1, -1), 1, colors.black)]))

        table2 = Table(data2)
        table2.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                                ('GRID', (0, 0), (-1, -1), 1, colors.black)]))

        # print("Graph 1 Statistics:")
        # print(graph1Statistics)

        # print("Graph 2 Statistics:")
        # print(graph2Statistics)
        return table1,table2

    def generatePDF(self, snapshot1_path, table1, snapshot2_path, table2, file_name):
        doc = SimpleDocTemplate(file_name, pagesize=letter, leftMargin=inch, rightMargin=inch, topMargin=inch, bottomMargin=inch)
        elements = []

        # Add a title and logo
        title_style = getSampleStyleSheet()['Title']
        title = Paragraph("<b>ICU MultiVital Signal Monitor</b>", title_style)

        logo = Image("https://imgur.com/Wk4nR0m.png", width=1*inch, height=1*inch)  # Adjust width and height as needed

        # Create a container to hold the title and logo
        title_and_logo = Table([[title, logo]], colWidths=[6*inch, 2*inch])  # Adjust the colWidths as needed

        # Set the alignment and vertical alignment for title and logo
        title_and_logo.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),  # Center the content horizontally
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # Center the content vertically
        ]))

        
        side_header_style = getSampleStyleSheet()['Normal'].clone('SideHeaderStyle')
        side_header_style.fontName = 'Helvetica-Bold'
        side_header_style.fontSize = 14
        side_header_style.alignment = 0
        bullet_point = '<bullet>&diams;</bullet>'
        
        # Add the title and logo to the PDF elements
        elements.append(title_and_logo)

        # Add some space between the title and logo and the content below
        elements.extend([Spacer(0, 60)])

        h1_text = f'<b>{bullet_point}</b> <u>Graph #01 Signal-Display And Statistics</u>'
        h1 = Paragraph(h1_text, side_header_style)       
        h2_text = f'<b>{bullet_point}</b> <u>Graph #02 Signal-Display And Statistics</u>'
        h2 = Paragraph(h2_text, side_header_style)
        
        
        # Set the position of the side header
        h1.leftIndent = -1 * inch  # Adjust as needed
        h2.leftIndent = -1 * inch  # Adjust as needed
    
    def exportPDF(self):
        self.generateStats()     
        table1, table2 = self.generateTables(self.graph1Statistics, self.graph2Statistics)
        snapshot1, snapshot2 = self.generateSnapshots()
        file_name, _ = QFileDialog.getSaveFileName(self, "Save PDF File", "", "PDF Files (*.pdf);;All Files (*)")

        if file_name:
            self.generatePDF(snapshot1, table1, snapshot2, table2, file_name)

def main():
    app = QApplication(sys.argv)  # Create an application instance
    window = MainApp()  # Create an instance of the MainApp class
    window.show()  # Display the main window
    app.exec()  # Start the application event loop

if __name__ == "__main__":
    main()
