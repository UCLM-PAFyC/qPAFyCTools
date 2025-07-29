
# authors:
# David Hernandez Lopez, david.hernandez@uclm.es

import os, sys
import shutil
import pathlib
import json

from PyQt5.uic import loadUi
from PyQt5.QtWidgets import (QApplication, QMessageBox, QDialog, QFileDialog, QPushButton, QComboBox,
                             QInputDialog, QLineEdit)
from PyQt5.QtCore import QDir, QFileInfo, QFile

current_path = os.path.dirname(__file__)
sys.path.append(os.path.join(current_path, '..'))
sys.path.append(os.path.join(current_path, '../..'))
# sys.path.insert(0, '..')
# sys.path.insert(0, '../..')

from PAFyCTools.defs import defs_paths, defs_main, defs_project, defs_processes
from PAFyCTools.lib.Project import Project
from PAFyCTools.lib.ProcessesManager import ProcessesManager
from PAFyCTools.gui.ProcessesManagerDialog import ProcessesManagerDialog
from PAFyCTools.gui.ProjectProcessesDialog import ProjectProcessesDialog

common_libs_absolute_path = os.path.join(current_path, defs_paths.COMMON_LIBS_RELATIVE_PATH)
sys.path.append(common_libs_absolute_path)

from pyLibQtTools import Tools
from pyLibQtTools.Tools import SimpleTextEditDialog
from pyLibParameters import defs_pars
from pyLibParameters.ParametersManager import ParametersManager
from pyLibParameters.ui_qt.ParametersManagerDialog import ParametersManagerDialog
from pyLibQtTools.QProcessDialog import QProcessDialog
from pyLibQtTools import defs_qprocess


class PAFyCToolsDialog(QDialog):
    """Employee dialog."""

    def __init__(self,
                 settings,
                 main_path,
                 parent=None):
        super().__init__(parent)
        loadUi(os.path.join(os.path.dirname(__file__), 'PAFyCToolsDialog.ui'), self)
        self.settings = settings
        self.main_path = main_path
        self.project = None
        self.widget_project_definitions = None
        self.import_csv_json_file_formats = None
        self.qgis_iface = None
        self.processes_manager = None
        self.process_author_value = ''
        self.process_label_value = ''
        self.process_description_value = ''
        self.initialize()

    def create_project(self, file_name):
        str_error = ''
        if os.path.exists(file_name):
            os.remove(file_name)
            if os.path.exists(file_name):
                str_error = ('Error removing existing project file:\n{}'.format(file_name))
                return str_error
        self.project = Project(self.qgis_iface,
                               self.settings)
        str_error = self.project.create(file_name)
        if str_error:
            str_error = ('Creating project file:\n{}\nError:\n{}'.format(file_name, str_error))
            self.project = None
            return str_error
        str_error = self.project.save_management(False)
        if str_error:
            str_error = ('Error updating project definition:\n{}'.
                         format(str_error))
            Tools.error_msg(str_error)
            self.project = None
            if os.path.exists(file_name):
                os.remove(file_name)
            return
        self.project_definition()
        str_error = self.project.create_locations_layer()
        return str_error

    def initialize(self):
        processes_path = (self.main_path + '/' + defs_processes.PROCESSES_PATH)
        processes_manager = ProcessesManager()
        str_error = processes_manager.initialize(processes_path)
        if str_error:
            Tools.error_msg(str_error)
            return
        self.processes_manager = processes_manager
        self.processesManagerPushButton.clicked.connect(self.select_processes_manager_gui)

        self.projectFilePushButton.clicked.connect(self.select_project_file)
        self.projectDefinitionPushButton.clicked.connect(self.project_definition)

        self.tabWidget.setEnabled(False)
        # map views
        self.mapViewsComboBox.addItem(defs_main.NO_COMBO_SELECT)
        self.mapViewsComboBox.currentIndexChanged.connect(self.location_changed)
        self.setMapViewPushButton.clicked.connect(self.location_set_map_view)
        self.removeMapViewPushButton.clicked.connect(self.location_remove)
        self.updateFromMapViewPushButton.clicked.connect(self.location_update_from_map_view)
        self.newFromMapViewPushButton.clicked.connect(self.location_new_from_map_view)

        # processes
        self.processComboBox.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.processComboBox.addItem(defs_main.NO_COMBO_SELECT)
        self.processComboBox.currentIndexChanged.connect(self.process_changed)
        self.processesDbPushButton.clicked.connect(self.processes_db)
        self.processParametersPushButton.clicked.connect(self.process_parameters)
        self.processLabelPushButton.clicked.connect(self.process_label)
        self.processAuthorPushButton.clicked.connect(self.process_author)
        self.processDescriptionPushButton.clicked.connect(self.process_description)
        self.processRunPushButton.clicked.connect(self.process_run)
        self.processesDbPushButton.setEnabled(False)
        self.processParametersPushButton.setEnabled(False)
        self.processLabelPushButton.setEnabled(False)
        self.processAuthorPushButton.setEnabled(False)
        self.processDescriptionPushButton.setEnabled(False)
        self.processRunPushButton.setEnabled(False)

        self.saveProjectPushButton.setEnabled(False)
        return

    def location_changed(self):
        map_view = self.mapViewsComboBox.currentText()
        if map_view == defs_main.NO_COMBO_SELECT:
            self.updateFromMapViewPushButton.setEnabled(False)
            self.removeMapViewPushButton.setEnabled(False)
            self.newFromMapViewPushButton.setEnabled(True)
            self.setMapViewPushButton.setEnabled(False)
        else:
            self.updateFromMapViewPushButton.setEnabled(True)
            self.removeMapViewPushButton.setEnabled(True)
            self.newFromMapViewPushButton.setEnabled(True)
            self.setMapViewPushButton.setEnabled(True)
        return

    def location_new_from_map_view(self):
        if not self.qgis_iface:
            return
        str_error, wkb_geometry = self.qgis_iface.get_map_canvas_wkb_geometry_in_project_crs()
        if str_error:
            str_error = ('Getting map canvas WKB geometry, error:\n{}'.format(str_error))
            Tools.error_msg(str_error)
            return
        text, okPressed = QInputDialog.getText(self, "Location name", "Enter name:",
                                               QLineEdit.Normal)
        if okPressed and text != '':
            if text in self.project.get_map_views():
                str_error = ('Exists a previous location with name: {}'.format(text))
                Tools.error_msg(str_error)
                return
            str_error = self.project.add_map_view(text, wkb_geometry)
            if str_error:
                Tools.error_msg(str_error)
                return
            self.update_locations(text)
        else:
            str_error = ('You must enter a valid location name')
            Tools.error_msg(str_error)
            return
        return

    def open_project(self, file_name):
        str_error = ''
        self.project = Project(self.qgis_iface,
                               self.settings)
        str_error = self.project.load_management(file_name)
        if str_error:
            str_error = ('Opening project, error:\n{}'.format(str_error))
        str_error = self.project.create_processes_layer() #if not exists
        if str_error:
            Tools.error_msg(str_error)
            return
        str_error = self.project.load_processes()
        if str_error:
            Tools.error_msg(str_error)
            return
        self.processComboBox.adjustSize()
        return str_error

    def process_author(self):
        current_text = self.process_author_value
        title = "Enter process author"
        text, ok = QInputDialog().getText(self, title,
                                          "Process author:", QLineEdit.Normal,
                                          current_text)
        if ok and text:
            self.process_author_value = text
        return

    def process_changed(self):
        self.processParametersPushButton.setEnabled(False)
        self.processLabelPushButton.setEnabled(False)
        self.processAuthorPushButton.setEnabled(False)
        self.processDescriptionPushButton.setEnabled(False)
        self.processRunPushButton.setEnabled(False)
        process = self.processComboBox.currentText()
        if process != defs_main.NO_COMBO_SELECT:
            self.processParametersPushButton.setEnabled(True)
            self.processLabelPushButton.setEnabled(True)
            self.processAuthorPushButton.setEnabled(True)
            self.processDescriptionPushButton.setEnabled(True)
            self.processRunPushButton.setEnabled(True)

    def processes_db(self):
        title = defs_project.PROJECT_PROCESSES_DIALOG_TITLE
        dialog = ProjectProcessesDialog(self.project, title, self.settings, self)
        dialog_result = dialog.exec()
        # if dialog_result != QDialog.Accepted:
        #     return str_error
        # Tools.error_msg(str_error)
        return

    def process_description(self):
        current_text = self.process_description_value
        title = "Enter process description"
        dialog = SimpleTextEditDialog(title, current_text, False)
        ret = dialog.exec()
        # if ret == QDialog.Accepted:
        #     text = dialog.get_text()
        #     self.descriptionLineEdit.setText(text)
        text = dialog.get_text()
        if text != current_text:
            self.process_description_value = text
        return

    def process_label(self):
        current_text = self.process_label_value
        title = "Enter process label"
        text, ok = QInputDialog().getText(self, title,
                                          "Process label (unique value):", QLineEdit.Normal,
                                          current_text)
        if ok and text:
            self.process_label_value = text
        return

    def process_parameters(self):
        process_name = self.processComboBox.currentText()
        if process_name == defs_main.NO_COMBO_SELECT:
            return
        process = None
        for process_provider in self.processes_manager.processes_by_provider:
            if process_name in self.processes_manager.processes_by_provider[process_provider]:
                process = self.processes_manager.processes_by_provider[process_provider][process_name]
                break
        if not process:
            return
        parametes_manager = process[defs_processes.PROCESS_FIELD_PARAMETERS]
        process_file_path = process[defs_processes.PROCESS_FILE]
        title = defs_pars.PARAMETERS_MANAGER_DIALOG_TITLE
        dialog = ParametersManagerDialog(parametes_manager, title, self.qgis_iface, self.settings, self)
        dialog_result = dialog.exec()
        return

    def process_run(self):
        if not self.process_author_value:
            msg = ("Input process author")
            Tools.info_msg(msg)
            return
        if not self.process_description_value:
            msg = ("Input process description")
            Tools.info_msg(msg)
            return
        if not self.process_label_value:
            msg = ("Input process label")
            Tools.info_msg(msg)
            return
        if self.process_label_value in self.project.process_by_label:
            msg = ("Exists another process with label: {}".format(self.process_label_value))
            msg += ("\nChange the label for new process,")
            msg += ("\nchange the label in the existing process ")
            msg += ("\nor remove the existing process")
            Tools.info_msg(msg)
            return
        process_name = self.processComboBox.currentText()
        if process_name == defs_main.NO_COMBO_SELECT:
            return
        process = None
        process_provider = None
        for process_provider in self.processes_manager.processes_by_provider:
            if process_name in self.processes_manager.processes_by_provider[process_provider]:
                process = self.processes_manager.processes_by_provider[process_provider][process_name]
                break
        if not process:
            return
        str_error, arguments = self.processes_manager.get_process_arguments(process_provider, process_name)
        if str_error:
            Tools.error_msg(str_error)
            return
        arguments.append('--' + defs_qprocess.ARGPARSER_TAG_STRING_TO_PUBLISH_THE_NUMBER_OF_STEPS)
        arguments.append('\"' + defs_qprocess.STRING_TO_PUBLISH_THE_NUMBER_OF_STEPS_DEFAULT + '\"')
        arguments.append('--' + defs_qprocess.ARGPARSER_TAG_STRING_TO_PUBLISH_COMPLETED_STEPS_PERCENTAGE)
        arguments.append('\"' + defs_qprocess.STRING_TO_PUBLISH_COMPLETED_STEPS_PERCENTAGE_DEFAULT + '\"')
        str_arguments = ""
        for i in range(len(arguments)):
            if i > 0:
                str_arguments += ' '
            if isinstance(arguments[i], str):
                str_arguments += arguments[i]
            else:
                str_arguments += str(arguments[i])
        program = defs_processes.PROCESS_PYTHON_PROGRAM
        title = ("Program: {}".format(program, arguments))
        dialog = QProcessDialog(title, self)
        dialog.start_process(program, arguments,
                             defs_qprocess.STRING_TO_PUBLISH_THE_NUMBER_OF_STEPS_DEFAULT,
                             defs_qprocess.STRING_TO_PUBLISH_COMPLETED_STEPS_PERCENTAGE_DEFAULT)
        dialog_result = dialog.exec()
        process_date_time_as_string = dialog.get_end_date_time_as_string(defs_main.DATE_TIME_STRING_FORMAT)
        process_log = dialog.get_log()
        process_contentas_dict = {}
        process_contentas_dict[defs_processes.PROCESS_FIELD_NAME] = process[defs_processes.PROCESS_FIELD_NAME]
        process_contentas_dict[defs_processes.PROCESS_FIELD_CONTRIBUTIONS] = process[defs_processes.PROCESS_FIELD_CONTRIBUTIONS]
        process_contentas_dict[defs_processes.PROCESS_FIELD_SRC] = process[defs_processes.PROCESS_FIELD_SRC]
        process_contentas_dict[defs_processes.PROCESS_FIELD_DESCRIPTION] = process[defs_processes.PROCESS_FIELD_DESCRIPTION]
        process_contentas_dict[defs_processes.PROCESS_FIELD_DOC] = process[defs_processes.PROCESS_DOC]
        process_contentas_dict[defs_processes.PROCESS_FIELD_PARAMETERS] \
            = process[defs_processes.PROCESS_FIELD_PARAMETERS].parameters_as_list_of_dict
        process_contentas_json = json.dumps(process_contentas_dict, indent=4, ensure_ascii=False)
        process_content = process_contentas_json
        process_content_uclm = ''
        process_content_uco = ''
        str_error = self.project.save_process(process_content,
                                              self.process_author_value,
                                              self.process_label_value,
                                              self.process_description_value,
                                              process_log,
                                              process_date_time_as_string,
                                              process_content_uclm,
                                              process_content_uco)
        if str_error:
            Tools.error_msg(str_error)
            return
        if self.qgis_iface:
            str_error = self.qgis_iface.reload_all_layers()
            if str_error:
                Tools.error_msg(str_error)
                return
        return

    def project_definition(self):
        if not self.project:
            str_error = ('Not exists project')
            Tools.error_msg(str_error)
            return
        str_error = self.project.project_definition_gui()
        if str_error:
            str_error = ('Project definition, error:\n{}'.format(str_error))
            Tools.error_msg(str_error)
            return
        return

    def location_remove(self):
        if not self.qgis_iface:
            return
        map_view_id = self.mapViewsComboBox.currentText()
        if map_view_id == defs_main.NO_COMBO_SELECT:
            return
        str_error = self.project.remove_map_view(map_view_id)
        if str_error:
            Tools.error_msg(str_error)
        self.update_locations()
        return

    def select_processes_manager_gui(self):
        str_error = ""
        title = defs_processes.PROCESSES_MANAGER_DIALOG_TITLE
        dialog = ProcessesManagerDialog(self.processes_manager, title, self.qgis_iface, self.settings, self)
        dialog_result = dialog.exec()
        # if dialog_result != QDialog.Accepted:
        #     return str_error
        # Tools.error_msg(str_error)
        return str_error

    def select_project_file(self):
        self.mapViewsComboBox.clear()
        self.mapViewsComboBox.addItem(defs_main.NO_COMBO_SELECT)
        self.locationsGroupBox.setEnabled(False)
        self.processesDbPushButton.setEnabled(False)
        title = "Select Project File"
        previous_file = self.projectLineEdit.text()
        last_path = self.settings.value("last_path")
        if not last_path:
            last_path = QDir.currentPath()
            self.settings.setValue("last_path", last_path)
            self.settings.sync()
        dlg = QFileDialog()
        dlg.setDirectory(last_path)
        dlg.setFileMode(QFileDialog.AnyFile)
        dlg.setNameFilter("Project File (*.gpkg)")
        if dlg.exec_():
            file_names = dlg.selectedFiles()
            file_name = file_names[0]
        else:
            return
        if file_name:
            if pathlib.Path(file_name).suffix != defs_project.PROJECT_FILE_SUFFIX:
                file_name = file_name + defs_project.PROJECT_FILE_SUFFIX
            self.projectLineEdit.setText(file_name)
            last_path = QFileInfo(file_name).absolutePath()
            self.settings.setValue("last_path", last_path)
            self.settings.sync()
            self.tabWidget.setEnabled(False)
            self.saveProjectPushButton.setEnabled(False)
            if os.path.exists(file_name):
                str_error = self.open_project(file_name)
                if str_error:
                    Tools.error_msg(str_error)
                    return
            else:
                str_error = self.create_project(file_name)
                if str_error:
                    Tools.error_msg(str_error)
                    return
            if not self.project:
                return
            self.tabWidget.setEnabled(True)
            self.saveProjectPushButton.setEnabled(True)
            if self.qgis_iface:
                self.qgis_iface.open_project(self.project)
                self.update_locations()
                self.locationsGroupBox.setEnabled(True)
            self.processesDbPushButton.setEnabled(True)
            self.update_processes()
        return

    def location_update_from_map_view(self):
        if not self.qgis_iface:
            return
        map_view_id = self.mapViewsComboBox.currentText()
        if map_view_id == defs_main.NO_COMBO_SELECT:
            return
        str_error, wkb_geometry = self.qgis_iface.get_map_canvas_wkb_geometry_in_project_crs()
        if str_error:
            Tools.error_msg(str_error)
            self.update_locations()
            return
        str_error = self.project.update_map_view(map_view_id, wkb_geometry)
        if str_error:
            Tools.error_msg(str_error)
            self.update_locations()
            return
        self.update_locations(map_view_id)
        return

    def location_set_map_view(self):
        if not self.qgis_iface:
            return
        map_view_id = self.mapViewsComboBox.currentText()
        if map_view_id == defs_main.NO_COMBO_SELECT:
            return
        str_error, wkb_geometry = self.project.get_map_view_wkb_geometry(map_view_id)
        if str_error:
            Tools.error_msg(str_error)
            self.update_locations()
            return
        if not wkb_geometry:
            str_error = ('Null geometry for location: {}'.format(map_view_id))
            Tools.error_msg(str_error)
            self.update_locations()
            return
        str_error = self.qgis_iface.set_map_canvas_from_wkb_geometry_in_project_crs(wkb_geometry)
        if str_error:
            Tools.error_msg(str_error)
            self.update_locations()
            return
        return

    def set_qgis_iface(self, qgis_iface):
        self.qgis_iface = qgis_iface

    def update_locations(self,
                         location_id = None):
        self.project.load_map_views()
        self.mapViewsComboBox.currentIndexChanged.disconnect(self.location_changed)
        self.mapViewsComboBox.clear()
        self.mapViewsComboBox.addItem(defs_main.NO_COMBO_SELECT)
        map_views = self.project.get_map_views()
        for map_view in map_views:
            self.mapViewsComboBox.addItem(map_view)
        self.mapViewsComboBox.currentIndexChanged.connect(self.location_changed)
        pos = 0
        if location_id:
            pos = self.mapViewsComboBox.findText(location_id)
            if pos == -1:
                pos = 0
        self.mapViewsComboBox.setCurrentIndex(pos)
        self.location_changed()

    def update_processes(self):
        if not self.processes_manager:
            return
        self.processComboBox.currentIndexChanged.disconnect(self.process_changed)
        self.processComboBox.clear()
        self.processComboBox.addItem(defs_main.NO_COMBO_SELECT)
        for process_provider in self.processes_manager.processes_by_provider:
            for process_name in self.processes_manager.processes_by_provider[process_provider]:
                process = self.processes_manager.processes_by_provider[process_provider][process_name]
                self.processComboBox.addItem(process_name)
        self.processComboBox.currentIndexChanged.connect(self.process_changed)
        return
