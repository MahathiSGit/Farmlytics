from qgis.PyQt.QtWidgets import QAction, QWidget, QVBoxLayout, QLabel, QScrollArea, QCheckBox, QInputDialog, QPushButton, QMessageBox, QDialog, QDialogButtonBox, QTableWidget, QTableWidgetItem, QStyleFactory
from qgis.PyQt.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QStyleFactory
from qgis.PyQt.QtWidgets import QComboBox, QFormLayout, QGroupBox
from PyQt5.QtWidgets import QAbstractItemView
from qgis.PyQt.QtWidgets import QDialog, QVBoxLayout, QDialogButtonBox, QLabel, QDateEdit
from qgis.PyQt.QtCore import QDate
from qgis.utils import iface
from qgis.PyQt.QtCore import QDate
from qgis.PyQt.QtWidgets import QCheckBox
from qgis.PyQt.QtCore import Qt
from qgis.core import QgsVectorLayer, QgsFeatureRequest
from qgis.gui import QgsMapToolIdentifyFeature
from matplotlib.dates import date2num
from qgis.utils import iface
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtWidgets import QApplication
from qgis.core import QgsProject
from qgis.PyQt.QtWidgets import QHBoxLayout
from datetime import timedelta
import os
import matplotlib.dates as mdates
from qgis.PyQt.QtCore import QDateTime
import plotly.graph_objects as go
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from datetime import datetime
import plotly.graph_objects as go
import webbrowser
import tempfile
import os, platform
from .mplcursors import mplcursors
from PyQt5.QtWidgets import QFileDialog
import pandas as pd
import platform
from qgis.PyQt.QtGui import QFont
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QSizePolicy
)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt
from qgis.PyQt.QtGui import QFont
import platform
class Farmlytics:
    def __init__(self, iface):
        self.iface = iface
        self.action = None
        self.selected_layer = None
        self.map_tool = None
        self.active_dialog=None
        self.fig=None
        self.canvas=None
        self.ax=None
        self.compare_checkboxes = {}   
        self.graph_lines = {}   
        self.added_farms = set()
        self.active_farm_plots = {} 
        self.farm_id_to_color = {}  
        self.my_dialog = QDialog()
        self.table_dialog = QDialog()
        self.table_dialog.setStyleSheet("font-family: 'San Francisco'; font-size: 14pt; font-weight: normal;")
        self.my_dialog.setStyleSheet("font-family: 'San Francisco'; font-size: 14pt; font-weight: normal;")
        self.graph_with_export_layout = QVBoxLayout()
        self.my_dialog.setStyleSheet("font-family: 'San Francisco'; font-size: 14pt; font-weight: normal;")
        self.main_layout = QVBoxLayout()
        self.my_dialog.setStyleSheet("font-family: 'San Francisco'; font-size: 14pt; font-weight: normal;")
        self.content_layout = QHBoxLayout()
        self.my_dialog.setStyleSheet("font-family: 'San Francisco'; font-size: 14pt; font-weight: normal;")
        self.dialog = QDialog()
        self.my_dialog.setStyleSheet("font-family: 'San Francisco'; font-size: 14pt; font-weight: normal;")
        self.farm_id_to_feature = {}        
        # # self.my_dialog.setFixedSize(1000, 8000)
        # # self.table_dialog.resize(1000, 800)
        # self.my_dialog.setMinimumSize(1000, 8000)
        # self.table_dialog.setMinimumSize(1000, 1000)
        self.my_dialog.resize(1000, 800)        # Optional: default size
        self.my_dialog.setMinimumSize(1000, 800) # Prevent it from shrinking too much

        self.table_dialog.resize(1200, 800)
        self.table_dialog.setMinimumSize(1200, 800)
        
        if self.table_dialog is None:
                    self.table_dialog = QDialog()

    def initGui(self):
        icon_path = os.path.join(os.path.dirname(__file__), "icon.png")
        self.action = QAction(QIcon(icon_path), "Farmlytics", self.iface.mainWindow())
        self.action.triggered.connect(self.select_layer)
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu("&Farm Info", self.action)


    def unload(self):
        if self.selected_layer:
            self.selected_layer.removeSelection()

        # Remove plugin menu and icon
        self.iface.removePluginMenu("&Farm Info", self.action)
        self.iface.removeToolBarIcon(self.action)

        # Close and clean up dialog windows
        for dlg_attr in ['dialog', 'my_dialog', 'table_dialog']:
            if hasattr(self, dlg_attr):
                dlg = getattr(self, dlg_attr)
                if dlg:
                    try:
                        dlg.close()
                        dlg.deleteLater()
                    except RuntimeError:
                        pass  # Dialog may already be deleted
                    setattr(self, dlg_attr, None)

        # Remove and delete dock widget if it exists
        if hasattr(self, 'dock_widget') and self.dock_widget:
            self.iface.removeDockWidget(self.dock_widget)
            self.dock_widget.deleteLater()
            self.dock_widget = None

    def select_layer(self):
        layers = [layer for layer in self.iface.mapCanvas().layers() if isinstance(layer, QgsVectorLayer)]
        if not layers:
            self.iface.messageBar().pushWarning("Error", "No vector layers available.")
            return

        layer_names = [layer.name() for layer in layers]
        layer_name, ok = QInputDialog.getItem(None, "Select Layer", "Layer:", layer_names, 0, False)
        if not ok:
            return

        self.selected_layer = next(l for l in layers if l.name() == layer_name)
        from qgis.core import QgsProject

        layer_tree = QgsProject.instance().layerTreeRoot()
        for layer in layers:
            node = layer_tree.findLayer(layer.id()) 
            if node:
                node.setItemVisibilityChecked(layer == self.selected_layer)

        self.iface.mapCanvas().setSelectionColor(Qt.yellow)
        self.iface.messageBar().pushMessage("Info", "Click on a farm feature to view details.")
        self.map_tool = QgsMapToolIdentifyFeature(self.iface.mapCanvas())
        self.map_tool.setLayer(self.selected_layer)
        self.map_tool.featureIdentified.connect(self.on_feature_identified)
        self.iface.mapCanvas().setMapTool(self.map_tool)


    def on_feature_identified(self, feature):
        start_date_py = self.get_startdate(feature)
        end_date_py = self.get_enddate(feature)
        min_qdate = QDate(start_date_py.year, start_date_py.month, start_date_py.day) if not isinstance(start_date_py, QDate) else start_date_py
        max_qdate = QDate(end_date_py.year, end_date_py.month, end_date_py.day) if not isinstance(end_date_py, QDate) else end_date_py

        if self.active_dialog is not None:
            try:
                self.active_dialog.close()
            except RuntimeError:
                pass
            self.active_dialog = None

        table_dialog = QDialog()
        table_dialog.setWindowTitle("Farm Details")
        table_dialog.finished.connect(lambda: self.selected_layer.removeSelection())
        table_dialog.finished.connect(self.clear_added_farms)

        self.table = QTableWidget()

       
        attributes_to_show = ["Farm_ID", "crop", "Area", "harvest_date"]
        max_cycles = 0
        for field_name in feature.fields().names():
            if "Cycle" in field_name and "_SOS" in field_name:
                try:
                    num = int(field_name.split("Cycle")[1].split("_")[0])
                    max_cycles = max(max_cycles, num)
                except:
                    continue
        for i in range(1, max_cycles + 1):
            attributes_to_show.extend([
                f"Cycle {i} SOS", f"Cycle {i} EOS", f"Cycle {i} Duration",
                f"Cycle {i} Peak NDVI", f"Cycle {i} Peak Date"
            ])
        attributes_to_show.extend(["Completed Cycles", "Incomplete Cycles"])


        self.table.setColumnCount(len(attributes_to_show))
        self.table.setHorizontalHeaderLabels(attributes_to_show)
        self.table.setRowCount(1)

        completed, incomplete = self.cycles_count(feature)
        sos_dates = self.get_sosdates(feature)
        eos_dates = self.get_eosdates(feature)
        durations = self.get_duration(feature)
        peaks = self.get_peak_info(feature)

        for col, attr in enumerate(attributes_to_show):
            value = ""
            if attr == "Completed Cycles":
                value = str(len(completed))
            elif attr == "Incomplete Cycles":
                value = str(len(incomplete))
            elif "Cycle" in attr:
                parts = attr.split()
                cycle_num = int(parts[1])
                key = parts[2]
                try:
                    if key == "SOS":
                        value = str(sos_dates[cycle_num - 1].strftime("%Y-%m-%d")) if cycle_num <= len(sos_dates) else "NA"
                    elif key == "EOS":
                        value = str(eos_dates[cycle_num - 1].strftime("%Y-%m-%d")) if cycle_num <= len(eos_dates) else "NA"
                    elif key == "Duration":
                        value = durations[cycle_num - 1] if cycle_num <= len(durations) else "NA"
                    elif key == "NDVI":
                        value = str(feature[f"Cycle{cycle_num}_Peak NDVI"]) if f"Cycle{cycle_num}_Peak NDVI" in feature.fields().names() else "NA"
                    elif key == "Date":
                        peak = feature[f"Cycle{cycle_num}_Peak date"]
                        value = peak.toPyDateTime().strftime("%Y-%m-%d") if hasattr(peak, "toPyDateTime") else str(peak)
                except:
                    value = "NA"
            else:
                value = str(feature[attr]) if attr in feature.fields().names() else ""
            self.table.setItem(0, col, QTableWidgetItem(value))

        self.table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.table.resizeColumnsToContents()
        self.table.resizeRowsToContents()
       


        export_table_btn = QPushButton("Export Table")
        export_table_btn.clicked.connect(self.export_table_to_csv)

        sort_layout = QHBoxLayout()
        self.sort_combo = QComboBox()
        fields = [self.table.horizontalHeaderItem(i).text() for i in range(self.table.columnCount())]
        self.sort_combo.addItems(fields)
        self.sort_button = QPushButton("Sort by Attribute")
        self.sort_button.setStyleSheet("""
            QPushButton {
                  
                color: #008CBA;
                border-radius: 5px;
                padding: 8px 15px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #fb8c00;
            }
            QPushButton:pressed {
                background-color: #e65100;
            }
        """)

        
        self.sort_button.clicked.connect(self.sort_table_by_attribute)
        sort_layout.addWidget(self.sort_combo)
        sort_layout.addWidget(self.sort_button)

        
        table_with_export_layout = QVBoxLayout()
        table_with_export_layout.addWidget(self.table)

    
        sort_controls_layout = QHBoxLayout()

        self.sort_button = QPushButton("Sort by Attribute")
        self.sort_button.clicked.connect(self.show_sort_dropdown)

        self.sort_dropdown = QComboBox()
        self.sort_dropdown.setStyleSheet("""
    QComboBox {
        color: #008CBA;
        border: 1px solid #FF9800;
        border-radius: 5px;
        padding: 5px;
        font-size: 13px;
    }
    QComboBox QAbstractItemView {
        ;
        selection-background-color: #FF9800;
        
    }
""")

        self.sort_dropdown.setVisible(False)
        self.sort_dropdown.activated[str].connect(self.sort_table_by_attribute)

        export_table_btn = QPushButton("Export Table")
        export_table_btn.setStyleSheet("""
            QPushButton {
                background-color: #008CBA; color: white; border-radius: 5px; padding: 8px 15px;font-size: 13px; font-weight: bold;}
            QPushButton:hover {
                background-color: #007bb5;
            }
            QPushButton:pressed {
                background-color: #005f7e;
            }
        """)
        export_table_btn.clicked.connect(self.export_table_to_csv)

        sort_controls_layout.addWidget(self.sort_button)
        sort_controls_layout.addWidget(self.sort_dropdown)
        sort_controls_layout.addWidget(export_table_btn)

        # Add to layout
        table_with_export_layout.addLayout(sort_controls_layout)
        main_layout = QVBoxLayout()
        content_layout = QHBoxLayout()
        graph_with_export_layout = QVBoxLayout()
        

        self.canvas_widget = None
        def update_graph(start_dt=None, end_dt=None):
            if self.canvas_widget:
                graph_with_export_layout.removeWidget(self.canvas_widget)
                self.canvas_widget.setParent(None)
                self.canvas_widget = None
            new_canvas = self.plot_ndvi_graph(feature, start_dt, end_dt)
            self.canvas_widget = new_canvas
            if new_canvas:
                graph_with_export_layout.addWidget(new_canvas)

        update_graph()
        

        export_button = QPushButton("Export Graph")
        export_button.setStyleSheet("""
            QPushButton {
                background-color: #008CBA; color: white; border-radius: 5px; padding: 8px 15px;font-size: 13px; font-weight: bold;}
            QPushButton:hover {
                background-color: #007bb5;
            }
            QPushButton:pressed {
                background-color: #005f7e;
            }
        """)
 
        export_button.setMaximumWidth(120)
        export_button.clicked.connect(self.export_graph_dialog)
        graph_with_export_layout.addWidget(export_button, alignment=Qt.AlignLeft)
        

        view_plots_button = QPushButton("View Individual Plot")
        view_plots_button.setStyleSheet("""
            QPushButton {
                background-color: #008CBA; color: white; border-radius: 5px; padding: 8px 15px;font-size: 13px; font-weight: bold;}
            QPushButton:hover {
                background-color: #007bb5;
            }
            QPushButton:pressed {
                background-color: #005f7e;
            }
        """)
        view_plots_button.clicked.connect(self.show_all_individual_plots)
        graph_with_export_layout.addWidget(view_plots_button, alignment=Qt.AlignRight)

        

        def pick_dates():
            dlg = DateRangeDialog(min_qdate, max_qdate)
            if dlg.exec_():
                start_qd, end_qd = dlg.get_dates()
                start_dt = start_qd.toPyDate()
                end_dt = end_qd.toPyDate()
                self.update_graph_all(start_dt, end_dt)
 

        date_range_button = QPushButton("Select Date Range")
        date_range_button.setStyleSheet("""
            QPushButton {
                background-color: #008CBA; color: white; border-radius: 5px; padding: 8px 15px;font-size: 13px; font-weight: bold;}
            QPushButton:hover {
                background-color: #007bb5;
            }
            QPushButton:pressed {
                background-color: #005f7e;
            }
        """)
        date_range_button.clicked.connect(pick_dates)
        reset_date_button = QPushButton("Reset Date Range")
        reset_date_button.setStyleSheet("""
            QPushButton {
                background-color: #008CBA; color: white; border-radius: 5px; padding: 8px 15px;font-size: 13px; font-weight: bold;}
            QPushButton:hover {
                background-color: #007bb5;
            }
            QPushButton:pressed {
                background-color: #005f7e;
            }
        """)
        reset_date_button.clicked.connect(lambda: self.update_graph_all(self.get_startdate(feature), self.get_enddate(feature)))

        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        if button_box: # Check if the button exists
            button_box.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50; /* Green background */
                    color: white; /* White text */
                    border-radius: 5px; /* Rounded corners */
                    padding: 8px 15px; /* Padding inside the button */
                    font-size: 13px; /* Slightly larger font */
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #45a049; /* Darker green on hover */
                }
                QPushButton:pressed {
                    background-color: #367c39; /* Even darker when pressed */
                }
            """)
        compare_button = QPushButton("Compare")
        compare_button.setStyleSheet("""
            QPushButton {
                background-color: #008CBA; color: white; border-radius: 5px; padding: 8px 15px;font-size: 13px; font-weight: bold;}
            QPushButton:hover {
                background-color: #007bb5;
            }
            QPushButton:pressed {
                background-color: #005f7e;
            }
        """)

        button_box.addButton(compare_button, QDialogButtonBox.ActionRole)
        button_box.accepted.connect(table_dialog.accept)
        compare_button.clicked.connect(lambda: self.compare_farm())

        self.checkbox_layout = QHBoxLayout()
        farm_id = str(feature["Farm_ID"])
        if farm_id in self.added_farms:
            return
        self.added_farms.add(farm_id)

        farm_control = self.add_farm_control(farm_id, feature)
        self.checkbox_layout.addWidget(farm_control)

        content_layout.addLayout(table_with_export_layout, stretch=1)
        content_layout.addLayout(graph_with_export_layout, stretch=2)

        controls_layout = QHBoxLayout()
        controls_layout.addWidget(date_range_button)
        controls_layout.addWidget(reset_date_button)  # <-- Add this line
        controls_layout.addWidget(button_box)
        controls_layout.addLayout(self.checkbox_layout)


        main_layout.addLayout(content_layout)
        main_layout.addLayout(controls_layout)

        table_dialog.setLayout(main_layout)
        table_dialog.setAttribute(Qt.WA_DeleteOnClose)
        table_dialog.show()

        self.selected_layer.removeSelection()
        self.selected_layer.select(feature.id())
        self.iface.mapCanvas().zoomToSelected(self.selected_layer)
        self.active_dialog = table_dialog
    
    def update_graph_all(self, start_dt=None, end_dt=None):
        if self.ax is not None and self.canvas is not None:
            if start_dt and end_dt:
                self.ax.set_xlim(start_dt, end_dt)
            else:
                if hasattr(self, "full_start_date") and hasattr(self, "full_end_date"):
                    self.ax.set_xlim(auto=True)  # or set default full range
            self.canvas.draw_idle()



    def export_graph_dialog(self):
        if not self.fig:
            QMessageBox.warning(None, "No Graph", "No graph to export.")
            return

        file_types = "PNG Image (*.png);;JPEG Image (*.jpg);;PDF Document (*.pdf);;SVG Vector (*.svg)"
        filename, filetype = QFileDialog.getSaveFileName(None, "Export Graph", "", file_types)

        if filename:
            try:
                self.fig.savefig(filename)
                QMessageBox.information(None, "Export Successful", f"Graph saved to:\n{filename}")
            except Exception as e:
                QMessageBox.critical(None, "Export Failed", f"Could not save file:\n{e}")


    
    def compare_farm(self):
        if not self.selected_layer:
            QMessageBox.warning(None, "No Layer Selected", "Please select a vector layer first.")
            return

        self.compare_tool = QgsMapToolIdentifyFeature(self.iface.mapCanvas())
        self.compare_tool.setLayer(self.selected_layer)
        self.compare_tool.featureIdentified.connect(self.handle_compare_selection)
        self.iface.mapCanvas().setMapTool(self.compare_tool)
        

    def handle_compare_selection(self, feature):
        self.iface.mapCanvas().setSelectionColor(Qt.yellow)
        self.selected_layer.select(feature.id())
        self.iface.mapCanvas().zoomToSelected(self.selected_layer)

        farm_id = str(feature["Farm_ID"])
        if farm_id in self.added_farms:
            # If the farm is already added, just ensure its checkbox is checked
            # and its line is visible if it was previously hidden.
            farm_checkbox = self.compare_checkboxes.get(farm_id)
            if farm_checkbox and not farm_checkbox.isChecked():
                farm_checkbox.setChecked(True)
            return  # Already added; skip adding duplicate elements

        self.added_farms.add(farm_id)
        self.farm_id_to_feature[farm_id] = feature

        try:
            datetimes = str(feature["Datetime"]).split(',')
            ndvi_values = str(feature["Mean NDVI"]).split(',')
            date_values = [datetime.strptime(dt.strip(), "%Y-%m-%d") for dt in datetimes if dt.strip()]
            ndvi_values = [float(val.strip()) for val in ndvi_values if val.strip()]
            if len(date_values) != len(ndvi_values):
                QMessageBox.warning(None, "Data Error", "Date and NDVI value count mismatch for compared farm.")
                return

            # --- Plot additional NDVI line
            plt.style.use('default')

            line, = self.ax.plot(date_values, ndvi_values, marker='o', linestyle='-',linewidth=0.8, markersize=2, label=f"Farm {farm_id}")
            self.graph_lines[farm_id] = line
            self.farm_plot_color = line.get_color()
            self.farm_id_to_color[farm_id] = self.farm_plot_color
            # --- Setup hover logic for all lines ---
            if not hasattr(self, "_hover_lines"):
                self._hover_lines = []
            self._hover_lines.append(line)

            if not hasattr(self, "_hover_annotation"):
                self._hover_annotation = self.ax.annotate(
                    "", xy=(0,0), xytext=(6,6),fontsize=6, textcoords="offset points",
                    bbox=dict(boxstyle="round", fc="w",lw=0.8),
                    arrowprops=dict(arrowstyle="->")
                )
                self._hover_annotation.set_visible(False)

            def hover(event):
                vis = self._hover_annotation.get_visible()
                found_line = False
                for ln in self._hover_lines:
                    if ln and ln.get_visible() and event.inaxes == self.ax: # Check if ln is not None
                        cont, ind = ln.contains(event)
                        if cont:
                            idx = ind["ind"][0]
                            xdata = ln.get_xdata()
                            ydata = ln.get_ydata()
                            x = xdata[idx]
                            y = ydata[idx]
                            self._hover_annotation.xy = (x, y)
                            xstr = x.strftime('%Y-%m-%d') if hasattr(x, "strftime") else str(x)
                            self._hover_annotation.set_text(f"Date: {xstr}\nNDVI: {y:.3f}\nFarm: {ln.get_label().split()[-1]}")
                            self._hover_annotation.set_visible(True)
                            self.canvas.draw_idle()
                            found_line = True
                            break
                if not found_line and vis:
                    self._hover_annotation.set_visible(False)
                    self.canvas.draw_idle()

            self.fig.canvas.mpl_connect("motion_notify_event", hover)

            # --- Update legend and redraw
            handles, labels = self.ax.get_legend_handles_labels()
            unique = dict(zip(labels, handles))
            self.ax.legend(unique.values(), unique.keys(), loc='center left', bbox_to_anchor=(1, 0.5),fontsize=6)
            plt.subplots_adjust(right=0.75)
            self.canvas.draw_idle()

            # --- Dynamically add table row and controls ---
            # Determine max_cycles for the *new* feature to ensure table headers are sufficient
            current_max_cycles = 0
            for field_name in feature.fields().names():
                if "Cycle" in field_name and "_SOS" in field_name:
                    try:
                        num = int(field_name.split("Cycle")[1].split("_")[0])
                        current_max_cycles = max(current_max_cycles, num)
                    except ValueError: 
                        continue
            
            existing_headers = [self.table.horizontalHeaderItem(i).text() for i in range(self.table.columnCount())]
            all_farm_ids_in_table = [self.table.item(r, 0).text() for r in range(self.table.rowCount()) if self.table.item(r, 0)]
            overall_max_cycles = 0
            for fid in all_farm_ids_in_table:
                overall_max_cycles = max(overall_max_cycles, current_max_cycles) 
            new_attributes_to_show = ["Farm_ID", "crop", "Area", "harvest_date"]
            for i in range(1, overall_max_cycles + 1):
                new_attributes_to_show.extend([
                    f"Cycle {i} SOS", f"Cycle {i} EOS", f"Cycle {i} Duration",
                    f"Cycle {i} Peak NDVI", f"Cycle {i} Peak Date"
                ])
            new_attributes_to_show.extend(["Completed Cycles", "Incomplete Cycles"])
            if new_attributes_to_show != existing_headers:
                self.table.setColumnCount(len(new_attributes_to_show))
                self.table.setHorizontalHeaderLabels(new_attributes_to_show)
            row_position = self.table.rowCount()
            self.table.insertRow(row_position)
            
            completed, incomplete = self.cycles_count(feature)
            sos_dates_list = self.get_sosdates(feature)
            eos_dates_list = self.get_eosdates(feature)
            durations_list = self.get_duration(feature)
            peaks_info_list = self.get_peak_info(feature)


            for col, attr in enumerate(new_attributes_to_show):
                value = ""
                if attr == "Completed Cycles":
                    value = str(len(completed))
                elif attr == "Incomplete Cycles":
                    value = str(len(incomplete))
                elif "Cycle" in attr:
                    parts = attr.split()
                    cycle_num = int(parts[1])
                    key = parts[2]
                    try:
                        if key == "SOS":
                            value = str(sos_dates_list[cycle_num - 1].strftime("%Y-%m-%d")) if cycle_num <= len(sos_dates_list) and isinstance(sos_dates_list[cycle_num - 1], datetime) else "NA"
                        elif key == "EOS":
                            value = str(eos_dates_list[cycle_num - 1].strftime("%Y-%m-%d")) if cycle_num <= len(eos_dates_list) and isinstance(eos_dates_list[cycle_num - 1], datetime) else "NA"
                        elif key == "Duration":
                            value = durations_list[cycle_num - 1] if cycle_num <= len(durations_list) else "NA"
                        elif key == "NDVI":
                            value = str(feature[f"Cycle{cycle_num}_Peak NDVI"]) if f"Cycle{cycle_num}_Peak NDVI" in feature.fields().names() else "NA"
                        elif key == "Date":
                            peak_date_val = None

                            if cycle_num - 1 < len(peaks_info_list) and isinstance(peaks_info_list[cycle_num - 1][0], datetime):
                                peak_date_val = peaks_info_list[cycle_num - 1][0]
                            value = peak_date_val.strftime("%Y-%m-%d") if peak_date_val and hasattr(peak_date_val, "strftime") else "NA"
                    except Exception as e:
                        value = "NA"
                else:
                    value = str(feature[attr]) if attr in feature.fields().names() else ""
                self.table.setItem(row_position, col, QTableWidgetItem(value))

            self.table.resizeColumnsToContents()
            self.table.resizeRowsToContents()
            
            farm_control = self.add_farm_control(farm_id, feature)
            self.checkbox_layout.addWidget(farm_control)

        except Exception as e:
            QMessageBox.critical(None, "Error", f"Failed to plot compared farm: {e}")
            self.added_farms.remove(farm_id) 
    def clear_added_farms(self):
        self.added_farms.clear()

    def add_farm_control(self, farm_id, feature):
        control_widget = QWidget()
        control_layout = QVBoxLayout(control_widget)
        control_layout.setContentsMargins(0, 0, 0, 0)
        control_layout.setSpacing(0)
        farm_checkbox = QCheckBox(f"Show {farm_id}")
        farm_checkbox.setChecked(True)
        self.compare_checkboxes[farm_id] = farm_checkbox
        control_layout.addWidget(farm_checkbox)
        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        info_layout.setContentsMargins(20, 0, 0, 0)
        info_layout.setSpacing(0)

        chk_sos = QCheckBox("SOS")
        chk_eos = QCheckBox("EOS")
        chk_peak = QCheckBox("Peak NDVI")
        chk_duration = QCheckBox("Duration")
        info_cbs = (chk_sos, chk_eos, chk_peak, chk_duration)
        for cb in info_cbs:
            info_layout.addWidget(cb)
        control_layout.addWidget(info_widget)
        info_widget.setVisible(farm_checkbox.isChecked())

        def plot_info():
          
            [a.remove() for a in getattr(self, f'aux_artists_{farm_id}', []) if a in self.ax.lines or a in self.ax.patches]
            aux_artists = []
            if chk_sos.isChecked():
                for date in self.get_sos(feature):
                    vline = self.ax.axvline(date, color="green", linestyle="--",linewidth=0.8, label="SOS")
                    aux_artists.append(vline)
            if chk_eos.isChecked():
                for date in self.get_eos(feature):
                    vline = self.ax.axvline(date, color="red", linestyle="-.",linewidth=0.8, label="EOS")
                    aux_artists.append(vline)
            if chk_peak.isChecked():
                for pd, nv in self.get_peak_info(feature):
                    pd_num = date2num(pd)
                    if self.ax.get_xlim()[0] <= pd_num <= self.ax.get_xlim()[1]:
                        point = self.ax.plot(pd, nv, marker="*", linestyle='None', color="gold", markersize=5, label="Peak NDVI")[0]
                        aux_artists.append(point)

                    aux_artists.append(point)
            if chk_duration.isChecked():
                for sos, eos in self.completed_cycles(feature):
                    line = self.graph_lines.get(farm_id)
                    span_color = line.get_color() if line else "orange"  # fallback if line missing
                    patch = self.ax.axvspan(sos, eos, color=span_color, alpha=0.1)

                    aux_artists.append(patch)
            handles, labels = self.ax.get_legend_handles_labels()
            unique = dict(zip(labels, handles))
            self.ax.legend(unique.values(), unique.keys(), loc='center left', bbox_to_anchor=(1, 0.5),fontsize=6)
            plt.subplots_adjust(right=0.75)  
            self.canvas.draw()

            self.canvas.draw_idle()
            setattr(self, f'aux_artists_{farm_id}', aux_artists)

        for cb in info_cbs:
            cb.stateChanged.connect(plot_info)
        farm_checkbox.stateChanged.connect(plot_info)

        def farm_toggle(state):
            visible = state == Qt.Checked

   
            line = self.graph_lines.get(farm_id)
            if line:
                line.set_visible(visible)

            handles, labels = self.ax.get_legend_handles_labels()
            visible_handles = []
            visible_labels = []
            for handle, label in zip(handles, labels):
                if handle.get_visible():
                    visible_handles.append(handle)
                    visible_labels.append(label)
            self.ax.legend(visible_handles, visible_labels, loc='center left', bbox_to_anchor=(1, 0.5))
            plt.subplots_adjust(right=0.75)  

            self.canvas.draw_idle()

            rows = self.table.rowCount()
            for row in range(rows):
                item = self.table.item(row, 0)
                if item and item.text() == farm_id:
                    self.table.setRowHidden(row, not visible)
      
            info_widget.setVisible(visible)
            if not visible:
  
                for cb in info_cbs:
                    cb.setChecked(False)
                [a.remove() for a in getattr(self, f'aux_artists_{farm_id}', []) if a in self.ax.lines or a in self.ax.patches]
                setattr(self, f'aux_artists_{farm_id}', [])
                self.canvas.draw_idle()


        farm_checkbox.stateChanged.connect(farm_toggle)

        setattr(self, f'aux_artists_{farm_id}', [])  
        return control_widget

    def show_sort_dropdown(self):
        self.sort_dropdown.clear()
        fields = [self.table.horizontalHeaderItem(i).text() for i in range(self.table.columnCount())]
        self.sort_dropdown.addItems(fields)
        self.sort_dropdown.setVisible(True)

    def sort_table_by_attribute(self, column_name):
        column_index = -1
        for i in range(self.table.columnCount()):
            if self.table.horizontalHeaderItem(i).text() == column_name:
                column_index = i
                break

        if column_index == -1:
            return

        rows = []
        for row in range(self.table.rowCount()):
            row_data = []
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                row_data.append(item.text() if item else "")
            rows.append(row_data)

        def try_cast(val):
            try:
                return float(val)
            except:
                return val.lower()

        rows.sort(key=lambda x: try_cast(x[column_index]))

        self.table.setRowCount(0)
        for row_data in rows:
            row_idx = self.table.rowCount()
            self.table.insertRow(row_idx)
            for col_idx, val in enumerate(row_data):
                self.table.setItem(row_idx, col_idx, QTableWidgetItem(str(val)))

      
        self.sort_dropdown.setVisible(False)

    def export_table_to_csv(self):
        if not self.table:
            QMessageBox.warning(None, "No Table", "There is no data table to export.")
            return

        filename, _ = QFileDialog.getSaveFileName(None, "Export Table to CSV", "", "CSV Files (*.csv)")
        if not filename:
            return

        try:
            with open(filename, 'w', encoding='utf-8') as f:
                headers = [self.table.horizontalHeaderItem(i).text() for i in range(self.table.columnCount())]
                f.write(','.join(headers) + '\n')

                for row in range(self.table.rowCount()):
                    if self.table.isRowHidden(row):  
                        continue
                    row_data = []
                    for col in range(self.table.columnCount()):
                        item = self.table.item(row, col)
                        row_data.append(item.text() if item else "")
                    f.write(','.join(row_data) + '\n')

            QMessageBox.information(None, "Export Successful", f"Table exported to:\n{filename}")

        except Exception as e:
            QMessageBox.critical(None, "Export Failed", f"Error exporting table:\n{e}")
    def show_all_individual_plots(self):
        if not hasattr(self, 'farm_id_to_feature') or not self.farm_id_to_feature:
            QMessageBox.warning(None, "No Farms", "No farm plots to display.")
            return

        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QWidget, QScrollArea
        from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
        from matplotlib.figure import Figure
        from datetime import datetime

        dialog = QDialog()
        dialog.setWindowTitle("Individual Farm NDVI Plots")
        dialog_layout = QVBoxLayout(dialog)

        scroll_area = QScrollArea()

        # --- Clear any previous content in scroll_area ---
        old_widget = scroll_area.takeWidget()
        if old_widget is not None:
            old_widget.deleteLater()

        container_widget = QWidget()
        container_layout = QVBoxLayout(container_widget)
        container_layout.setSpacing(15)
        container_layout.setContentsMargins(10, 10, 10, 10)

        for farm_id, feature in self.farm_id_to_feature.items():
            try:
                datetimes_str = str(feature["Datetime"])
                mean_ndvi_str = str(feature["Mean NDVI"])
                date_values = [datetime.strptime(dt.strip(), "%Y-%m-%d") for dt in datetimes_str.split(",") if dt.strip()]
                ndvi_values = [float(val.strip()) for val in mean_ndvi_str.split(",") if val.strip()]
            except Exception:
                continue  

            plot_widget = QWidget()
            plot_layout = QVBoxLayout(plot_widget)
            plot_layout.setContentsMargins(0, 0, 0, 0)
            plot_layout.setSpacing(5)

            fig = Figure(figsize=(6, 4))
            ax = fig.add_subplot(111)
            color = self.farm_id_to_color.get(farm_id, 'dodgerblue')
            ax.plot(date_values, ndvi_values, marker='o', linestyle='-', color=color, label=f"Farm {farm_id}")

            sos_dates = self.get_sos(feature)
            for sos in sos_dates:
                ax.axvline(sos, color='green', linestyle='--', label='SOS')

            eos_dates = self.get_eos(feature)
            for eos in eos_dates:
                ax.axvline(eos, color='red', linestyle='-.', label='EOS')

            completed_cycles = self.completed_cycles(feature)
            for sos, eos in completed_cycles:
                ax.axvspan(sos, eos, color=color, alpha=0.1)

            peaks = self.get_peak_info(feature)
            for pd, ndvi in peaks:
                ax.plot(pd, ndvi, marker='*', color='gold', linestyle='None', markersize=10, label='Peak NDVI')

            ax.set_title(f"NDVI Trend for Farm {farm_id}")
            ax.set_xlabel("Date")
            ax.set_ylabel("Mean NDVI")
            ax.legend()
            fig.autofmt_xdate()

            canvas = FigureCanvas(fig)
            canvas.setMinimumHeight(300)
            plot_layout.addWidget(canvas)

            container_layout.addWidget(plot_widget)

        container_widget.setLayout(container_layout)
        scroll_area.setWidget(container_widget)
        scroll_area.setWidgetResizable(True)
        dialog_layout.addWidget(scroll_area)

        dialog.resize(700, 600)
        dialog.exec_()


        
    def get_peak_info(self, feature):
        peaks = []
        for i in range(1, 4):
            try:
                date_val = feature[f"Cycle{i}_Peak date"]
                ndvi_val = feature[f"Cycle{i}_Peak NDVI"]

                if (date_val and ndvi_val and 
                    str(date_val) not in ["NULL", "NA", "NaT"] and 
                    str(ndvi_val) not in ["NULL", "NA"]):

                    if hasattr(date_val, "toPyDateTime"):
                        peak_date = date_val.toPyDateTime()
                    else:
                        continue  

                    peak_ndvi = float(ndvi_val)
                    peaks.append((peak_date, peak_ndvi))

            except Exception as e:
                print(f"Error parsing Peak NDVI for Cycle {i}: {e}")
        return peaks

    def get_sos(self, feature):
        sos_dates = []
        for i in range(1, 4):
            try:
                sos=feature[f"Cycle{i}_SOS"]
                if isinstance(sos, QDateTime):
                    sos_dates.append(sos.toPyDateTime())
                elif hasattr(sos, "toPyDateTime"):
                    sos_dates.append(sos.toPyDateTime())
            except Exception as e:
                print(f"Error parsing SOS date for Cycle {i}: {e}")
        return sos_dates


    
    def get_eos(self, feature):
        eos_dates = []
        for i in range(1, 4):
            try:
                eos = feature[f"Cycle{i}_EOS"]
                if isinstance(eos, QDateTime):
                    eos_dates.append(eos.toPyDateTime())
                elif hasattr(eos, "toPyDateTime"):
                    eos_dates.append(eos.toPyDateTime())
            except Exception as e:
                print(f"Error parsing EOS date for Cycle {i}: {e}")
        return eos_dates
    
    def get_duration(self, feature):
        duration=[]
        for i in range(1,4):
            duration.append(str(feature[f"Cycle{i}_Duration"]))
        return duration
    def get_sosdates(self, feature):
        sos_dates=[]

        for i in range(1,4):
            sos=feature[f"Cycle{i}_SOS"]
            if sos in ["NA", "NULL", "None"]:
                sos_dates.append(sos)
            elif isinstance(sos, QDateTime):
                sos_dates.append(sos.toPyDateTime())
        return sos_dates
    def get_eosdates(self, feature):
        eos_dates=[]

        for i in range(1,4):
            eos=feature[f"Cycle{i}_EOS"]
            if eos in ["NA", "NULL", "None"]:
                eos_dates.append(eos)
            elif isinstance(eos, QDateTime):
                eos_dates.append(eos.toPyDateTime())
        return eos_dates
    
    def get_startdate(self, feature):
        start_date=feature["start_date"]
        return start_date.toPyDate()
    
    def get_enddate(self, feature):
        end_date=feature["end_date"]
        return end_date.toPyDate()


    def completed_cycles(self, feature):
        ignored_cycles = []
        incomplete_cycles = []
        completed_cycles = []
        for i in range(1, 4):
            duration = feature[f"Cycle{i}_Duration"]
            sos = feature[f"Cycle{i}_SOS"]
            eos = feature[f"Cycle{i}_EOS"]
            values = [duration, sos, eos]           
            if all(val in [None, "NA", "null", "NaT"] for val in values):
                ignored_cycles.append(feature["Farm_ID"])            
            elif any(val in [None, "NA", "null", "NaT"] for val in values):
                incomplete_cycles.append(feature["Farm_ID"])            
            else:
                completed_cycles.append((sos.toPyDateTime(), eos.toPyDateTime()))
        return completed_cycles


    def cycles_count(self, feature):
        ignored_cycles = []
        incomplete_cycles = []
        completed_cycles = []


        for i in range(1, 4):
            duration = feature[f"Cycle{i}_Duration"]
            sos = feature[f"Cycle{i}_SOS"]
            eos = feature[f"Cycle{i}_EOS"]

            values = [duration, sos, eos]

          
            if all(val in [None, "NA", "null", "NaT"] for val in values):
                ignored_cycles.append(feature["Farm_ID"])

            
            elif any(val in [None, "NA", "null", "NaT"] for val in values):
                incomplete_cycles.append(feature["Farm_ID"])

            
            else:
                completed_cycles.append((sos.toPyDateTime(), eos.toPyDateTime()))

        return completed_cycles, incomplete_cycles
   



    def plot_ndvi_graph(self, feature, start_date_filter=None, end_date_filter=None):
        try:
            import matplotlib.pyplot as plt
            import matplotlib.dates as mdates
            import platform
            
            datetimes = str(feature["Datetime"]).split(',')
            mean_ndvi = str(feature["Mean NDVI"]).split(',')

            date_values = [datetime.strptime(dt.strip(), "%Y-%m-%d") for dt in datetimes if dt.strip()]
            ndvi_values = [float(val.strip()) for val in mean_ndvi if val.strip()]
            
            if len(date_values) != len(ndvi_values):
                print("Mismatch in date and NDVI lengths.")
                return None

            self.full_start_date = min(date_values)
            self.full_end_date = max(date_values)

            if start_date_filter and end_date_filter:
                filtered_dates = []
                filtered_ndvi = []
                for dt, val in zip(date_values, ndvi_values):
                    if start_date_filter <= dt <= end_date_filter:
                        filtered_dates.append(dt)
                        filtered_ndvi.append(val)
                date_values, ndvi_values = filtered_dates, filtered_ndvi

            farm_id = str(feature['Farm_ID'])
            fig, ax = plt.subplots()
            for spine in ax.spines.values():
                spine.set_linewidth(0.8)
            plt.style.use('default')
            line, = ax.plot(date_values, ndvi_values, marker='o', linestyle='-', color='dodgerblue',linewidth=0.8, markersize=2, label=f"Farm {farm_id}")
            self.farm_id_to_feature[farm_id]=feature
            self.farm_plot_color = line.get_color()
            self.farm_id_to_color[farm_id] = self.farm_plot_color
            self.graph_lines[farm_id] = line

            annot = ax.annotate(
                "", xy=(0, 0), xytext=(6, 6),fontsize=6, textcoords="offset points",
                bbox=dict(boxstyle="round", fc="w",lw=0.8),
                arrowprops=dict(arrowstyle="->")
            )
            annot.set_visible(False)


            def update_annot(ind):
                idx = ind["ind"][0]
                x, y = date_values[idx], ndvi_values[idx]
                annot.xy = (x, y)
                annot.set_text(f"Date: {x.strftime('%Y-%m-%d')}\nNDVI: {y:.3f}")

            def hover(event):
                try:
                    vis = annot.get_visible()
                    if event.inaxes == ax and line.get_visible():
                        cont, ind = line.contains(event)
                        if cont:
                            update_annot(ind)
                            annot.set_visible(True)
                            fig.canvas.draw_idle()
                        elif vis:
                            annot.set_visible(False)
                            fig.canvas.draw_idle()
                except Exception as e:
                    print("Hover error:", e)

            fig.canvas.mpl_connect("motion_notify_event", hover)

            ax.set_title(f"NDVI Trend ", fontsize=6)
            ax.set_xlabel("Date", fontsize=6)
            ax.set_ylabel("Mean NDVI",fontsize=6)
            ax.tick_params(axis='x', labelrotation=45,labelsize=6)
            ax.tick_params(axis='y',labelsize=6)
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%b-%Y'))
            fig.autofmt_xdate()
            fig.tight_layout(rect=[0, 0, 0.75, 1])  # Leaves space for legend on right

            handles, labels = ax.get_legend_handles_labels()
            unique = dict(zip(labels, handles))
            ax.legend(unique.values(), unique.keys(), loc='center left', bbox_to_anchor=(1, 0.5),fontsize=6)

            import matplotlib.pyplot as plt
            plt.subplots_adjust(right=0.75)

            from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
            canvas = FigureCanvas(fig)
            # canvas = FigureCanvas(fig)
            canvas.setMinimumHeight(450)
            canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            canvas.updateGeometry()

            self.fig = fig
            self.ax = ax
            self.canvas = canvas
            return canvas


  

        except Exception as e:
            print("Error plotting NDVI graph:", e)
            return None

    def on_checkbox_toggled(self, state, farm_id):
        is_checked = state == Qt.Checked

       
        self.active_farm_plots[farm_id] = is_checked

       
        for line in self.ax.get_lines():
            if line.get_label() == farm_id:
                line.set_visible(is_checked)

        self.canvas.draw()
 

    def populate_dynamic_cycles_table(self, properties):
  
    
        fields = ['SOS', 'Peak date', 'Peak NDVI', 'EOS', 'Duration']
        column_labels = ['Cycle'] + fields

        
        self.tableWidget.setRowCount(0)
        self.tableWidget.setColumnCount(len(column_labels))
        self.tableWidget.setHorizontalHeaderLabels(column_labels)

        cycle_index = 1
        while True:
            prefix = f"Cycle{cycle_index}_"
            if any(key.startswith(prefix) for key in properties.keys()):
                row = self.tableWidget.rowCount()
                self.tableWidget.insertRow(row)
                self.tableWidget.setItem(row, 0, QTableWidgetItem(str(cycle_index)))  # Cycle number

                for col, field in enumerate(fields, start=1):
                    value = properties.get(f"{prefix}{field}", "N/A")
                
                    if isinstance(value, str) and value.endswith("T00:00:00"):
                        value = value.split("T")[0]
                    self.tableWidget.setItem(row, col, QTableWidgetItem(str(value)))
                
                cycle_index += 1
            else:
                break
    




class DateRangeDialog(QDialog):
    def __init__(self, min_date, max_date, parent=None):
       
        super().__init__(parent)
        self.setWindowTitle("Select Date Range")
        layout = QVBoxLayout(self)
        
   
        layout.addWidget(QLabel("Start Date:"))
        self.start_date_edit = QDateEdit()
        self.start_date_edit.setCalendarPopup(True)
        self.start_date_edit.setMinimumDate(min_date)
        self.start_date_edit.setMaximumDate(max_date)
        self.start_date_edit.setDate(min_date)
        layout.addWidget(self.start_date_edit)
        
 
        layout.addWidget(QLabel("End Date:"))
        self.end_date_edit = QDateEdit()
        self.end_date_edit.setCalendarPopup(True)
        self.end_date_edit.setMinimumDate(min_date)
        self.end_date_edit.setMaximumDate(max_date)
        self.end_date_edit.setDate(max_date)
        layout.addWidget(self.end_date_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_dates(self):
        return self.start_date_edit.date(), self.end_date_edit.date()
    
    

  
