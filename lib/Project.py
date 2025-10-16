# authors:
# David Hernandez Lopez, david.hernandez@uclm.es

from PyQt5.QtWidgets import QApplication, QMessageBox, QDialog, QFileDialog, QPushButton, QComboBox
from PyQt5.QtCore import QDir, QFileInfo, QFile, QDate, QDateTime

import os
import sys
import math
import random
import re
import json

from osgeo import gdal, osr, ogr
gdal.UseExceptions()

current_path = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(current_path, '..'))
sys.path.append(os.path.join(current_path, '../..'))
# sys.path.insert(0, '..')
# sys.path.insert(0, '../..')

from PAFyCTools.defs import defs_paths, defs_project, defs_main
from PAFyCTools.gui.ProjectDefinitionDialog import ProjectDefinitionDialog

common_libs_absolute_path = os.path.join(current_path, defs_paths.COMMON_LIBS_RELATIVE_PATH)
sys.path.append(common_libs_absolute_path)

from pyLibCRSs import CRSsDefines as defs_crs
from pyLibCRSs.CRSsTools import CRSsTools
from pyLibQtTools import Tools
from pyLibGDAL import defs_gdal
from pyLibGDAL.GDALTools import GDALTools

class Project:
    def __init__(self,
                 qgis_iface,
                 settings):
        self.qgis_iface = qgis_iface
        self.settings = settings
        self.file_path = None
        self.project_definition = {}
        self.project_definition[defs_project.PROJECT_DEFINITIONS_TAG_NAME] = None
        self.project_definition[defs_project.PROJECT_DEFINITIONS_TAG_TAG] = None
        self.project_definition[defs_project.PROJECT_DEFINITIONS_TAG_AUTHOR] = None
        # self.project_definition[defs_project.PROJECT_DEFINITIONS_TAG_GEO3D_CRS] = None
        # self.project_definition[defs_project.PROJECT_DEFINITIONS_TAG_GEO2D_CRS] = None
        # self.project_definition[defs_project.PROJECT_DEFINITIONS_TAG_ECEF_CRS] = None
        self.project_definition[defs_project.PROJECT_DEFINITIONS_TAG_PROJECTED_CRS] = defs_project.CRS_PROJECTED_DEFAULT
        self.project_definition[defs_project.PROJECT_DEFINITIONS_TAG_VERTICAL_CRS] = defs_project.CRS_VERTICAL_DEFAULT
        self.project_definition[defs_project.PROJECT_DEFINITIONS_TAG_OUTPUT_PATH] = None
        self.project_definition[defs_project.PROJECT_DEFINITIONS_TAG_DESCRIPTION] = None
        self.project_definition[defs_project.PROJECT_DEFINITIONS_TAG_START_DATE] = None
        self.project_definition[defs_project.PROJECT_DEFINITIONS_TAG_FINISH_DATE] = None
        self.crs_tools = None
        # self.gpkg_tools = None
        self.map_views = {}
        self.process_by_label = {}
        self.initialize()

    def add_map_view(self,
                      map_view_id,
                      map_view_wkb_geometry):
        str_error = ''
        if map_view_id in self.map_views:
            str_error = ('Exists a previous location with name: {}'.format(map_view_id))
            return str_error
        update = False
        return self.save_map_view(map_view_id,
                                  map_view_wkb_geometry,
                                  update)

    def create(self,
               file_name):
        str_error = ''
        layers_definition = {}
        layers_definition[defs_project.MANAGEMENT_LAYER_NAME] = {}
        layers_definition[defs_project.MANAGEMENT_LAYER_NAME] \
            = defs_project.fields_by_layer[defs_project.MANAGEMENT_LAYER_NAME]
        layers_crs_id = {}
        layers_crs_id[defs_project.MANAGEMENT_LAYER_NAME] = None
        ignore_existing_layers = False # create new gpkg
        create_options = defs_project.create_options
        str_error = GDALTools.create_vector(file_name,
                                            layers_definition,
                                            layers_crs_id,
                                            ignore_existing_layers,
                                            create_options)
        if not str_error:
            self.file_path = file_name
        return str_error

    def create_locations_layer(self):
        str_error = ''
        layers_definition = {}
        layers_definition[defs_project.LOCATIONS_LAYER_NAME] = {}
        layers_definition[defs_project.LOCATIONS_LAYER_NAME] \
            = defs_project.fields_by_layer[defs_project.LOCATIONS_LAYER_NAME]
        layers_crs_id = {}
        layers_crs_id[defs_project.LOCATIONS_LAYER_NAME] \
            = self.project_definition[defs_project.PROJECT_DEFINITIONS_TAG_PROJECTED_CRS]
        ignore_existing_layers = True # no create new gpkg
        str_error = GDALTools.create_vector(self.file_path,
                                            layers_definition,
                                            layers_crs_id,
                                            ignore_existing_layers)
        return str_error

    def create_processes_layer(self):
        str_error = ''
        str_error, exists_layer = GDALTools.exists_layer(self.file_path, defs_project.PROCESESS_LAYER_NAME)
        if str_error:
            return str_error
        if exists_layer:
            return str_error
        layers_definition = {}
        layers_definition[defs_project.PROCESESS_LAYER_NAME] = {}
        layers_definition[defs_project.PROCESESS_LAYER_NAME] \
            = defs_project.fields_by_layer[defs_project.PROCESESS_LAYER_NAME]
        layers_crs_id = {}
        layers_crs_id[defs_project.PROCESESS_LAYER_NAME] = None
        ignore_existing_layers = True # create new gpkg
        str_error = GDALTools.create_vector(self.file_path,
                                            layers_definition,
                                            layers_crs_id,
                                            ignore_existing_layers)
        return str_error

    def get_map_views(self):
        return self.map_views.keys()

    def get_map_view_wkb_geometry(self,
                                  map_view_id):
        str_error = ''
        wkb_geometry = None
        if not map_view_id in self.map_views:
            str_error = ('Not exists location: {}'.format(map_view_id))
            return str_error
        wkb_geometry = self.map_views[map_view_id]
        return str_error, wkb_geometry

    def initialize(self):
        self.crs_tools = CRSsTools()
        # self.gpkg_tools = GpkgTools(self.crs_tools)
        if self.qgis_iface:
            self.qgis_iface.set_project(self)
        return

    def load_management(self, file_name):
        str_error = ''
        # str_error, layer_names = self.gpkg_tools.get_layers_names(file_name)
        str_error, layer_names = GDALTools.get_layers_names(file_name)
        if str_error:
            str_error = ('Loading gpgk:\n{}\nError:\n{}'.
                         format(file_name, str_error))
            return str_error
        if not defs_project.MANAGEMENT_LAYER_NAME in layer_names:
            str_error = ('Loading gpgk:\n{}\nError: not exists layer:\n{}'.
                         format(file_name, defs_project.MANAGEMENT_LAYER_NAME))
            return str_error
        layer_name = defs_project.MANAGEMENT_LAYER_NAME
        fields = defs_project.fields_by_layer[defs_project.MANAGEMENT_LAYER_NAME]
        fields = {}
        field_name = defs_project.MANAGEMENT_FIELD_CONTENT
        fields[field_name] = defs_project.fields_by_layer[layer_name][field_name]
        filter_fields = {}
        filter_field_name = defs_project.MANAGEMENT_FIELD_NAME
        filter_field_value = defs_project.PROJECT_DEFINITIONS_MANAGEMENT_FIELD_NAME
        filter_fields[filter_field_name] = filter_field_value
        str_error, features = GDALTools.get_features(file_name,
                                                     layer_name,
                                                     fields,
                                                     filter_fields)
        # str_error, features = self.gpkg_tools.get_features(file_name,
        #                                                    layer_name,
        #                                                    fields,
        #                                                    filter_fields)
        if str_error:
            str_error = ('Getting management from gpgk:\n{}\nError:\n{}'.
                         format(file_name, str_error))
            return str_error
        if len(features) != 1:
            str_error = ('Loading gpgk:\n{}\nError: not one value for field: {} in layer: {}'.
                         format(file_name, defs_project.MANAGEMENT_FIELD_CONTENT, defs_project.MANAGEMENT_LAYER_NAME))
            return str_error
        value = features[0][field_name]
        json_acceptable_string = value.replace("'", "\"")
        management_json_content = json.loads(json_acceptable_string)
        str_error = self.set_definition_from_json(management_json_content)
        if str_error:
            str_error = ('\nSetting from json project file:\n{}\nerror:\n{}'.format(file_name, str_error))
            return str_error
        self.file_path = file_name
        return str_error

    def load_map_views(self):
        str_error = ''
        file_name = self.file_path
        # str_error, layer_names = self.gpkg_tools.get_layers_names(file_name)
        str_error, layer_names = GDALTools.get_layers_names(file_name)
        if str_error:
            str_error = ('Loading gpgk:\n{}\nError:\n{}'.
                         format(file_name, str_error))
            return str_error
        if not defs_project.LOCATIONS_LAYER_NAME in layer_names:
            str_error = ('Loading gpgk:\n{}\nError: not exists layer:\n{}'.
                         format(file_name, defs_project.LOCATIONS_LAYER_NAME))
            return str_error
        layer_name = defs_project.LOCATIONS_LAYER_NAME
        fields = defs_project.fields_by_layer[defs_project.LOCATIONS_LAYER_NAME]
        fields = {}
        field_name = defs_project.LOCATIONS_FIELD_NAME
        fields[field_name] = defs_project.fields_by_layer[layer_name][field_name]
        field_geometry = defs_project.LOCATIONS_FIELD_GEOMETRY
        fields[field_geometry] = defs_project.fields_by_layer[layer_name][field_geometry]
        filter_fields = None
        # str_error, features = self.gpkg_tools.get_features(file_name,
        #                                                    layer_name,
        #                                                    fields,
        #                                                    filter_fields)
        str_error, features = GDALTools.get_features(file_name,
                                                     layer_name,
                                                     fields,
                                                     filter_fields)
        if str_error:
            str_error = ('Getting locations from gpgk:\n{}\nError:\n{}'.
                         format(file_name, str_error))
            return str_error
        self.map_views.clear()
        for i in range(len(features)):
            name = features[i][defs_project.LOCATIONS_FIELD_NAME]
            wkb_geometry = features[i][defs_project.LOCATIONS_FIELD_GEOMETRY]
            self.map_views[name] = wkb_geometry
        return str_error

    def load_processes(self):
        str_error = ''
        str_error, layer_names = GDALTools.get_layers_names(self.file_path)
        if str_error:
            str_error = ('Loading gpgk:\n{}\nError:\n{}'.
                         format(self.file_path, str_error))
            return str_error
        if not defs_project.PROCESESS_LAYER_NAME in layer_names:
            str_error = ('Loading gpgk:\n{}\nError: not exists layer:\n{}'.
                         format(self.file_path, defs_project.MANAGEMENT_LAYER_NAME))
            return str_error
        layer_name = defs_project.PROCESESS_LAYER_NAME
        fields = defs_project.fields_by_layer[defs_project.PROCESESS_LAYER_NAME]
        str_error, features = GDALTools.get_features(self.file_path,
                                                     layer_name,
                                                     fields)
        if str_error:
            str_error = ('Getting processes from gpgk:\n{}\nError:\n{}'.
                         format(self.file_path, str_error))
            return str_error
        for feature in features:
            process_label = feature[defs_project.PROCESESS_FIELD_LABEL]
            process_dict = {}
            for field_name in defs_project.fields_by_layer[defs_project.PROCESESS_LAYER_NAME]:
                if field_name == defs_project.PROCESESS_FIELD_GEOMETRY:
                    continue
                field_value = ''
                if field_name in feature:
                    field_value = feature[field_name]
                process_dict[field_name] = field_value
            if process_label in self.process_by_label:
                self.process_by_label.pop(process_label)
            self.process_by_label[process_label] = process_dict
        return str_error

    def project_definition_gui(self):
        str_error = ""
        title = defs_project.PROJECT_DEFINITION_DIALOG_TITLE
        dialog = ProjectDefinitionDialog(self, title)
        dialog_result = dialog.exec()
        if dialog_result != QDialog.Accepted:
            return str_error
        return str_error

    def remove_map_view(self,
                        map_view_id):
        str_error = ''
        if not map_view_id in self.map_views:
            str_error = ('Not exists location with name: {}'.format(map_view_id))
            return str_error
        features_filters = []
        feature_filters = []
        filter = {}
        filter[defs_gdal.FIELD_NAME_TAG] = defs_project.LOCATIONS_FIELD_NAME
        filter[defs_gdal.FIELD_TYPE_TAG] \
            = defs_project.fields_by_layer[defs_project.LOCATIONS_LAYER_NAME][defs_project.LOCATIONS_FIELD_NAME]
        filter[defs_gdal.FIELD_VALUE_TAG] = map_view_id
        feature_filters.append(filter)
        features_filters.append(feature_filters)
        features_filters_by_layer = {}
        features_filters_by_layer[defs_project.LOCATIONS_LAYER_NAME] = features_filters
        return GDALTools.remove_features(self.file_path, features_filters_by_layer)

    def remove_process(self,
                       process_label):
        str_error = ''
        features_filters = []
        feature_filters = []
        filter = {}
        filter[defs_gdal.FIELD_NAME_TAG] = defs_project.PROCESESS_FIELD_LABEL
        filter[defs_gdal.FIELD_TYPE_TAG] \
            = defs_project.fields_by_layer[defs_project.PROCESESS_LAYER_NAME][defs_project.PROCESESS_FIELD_LABEL]
        filter[defs_gdal.FIELD_VALUE_TAG] = process_label
        feature_filters.append(filter)
        features_filters.append(feature_filters)
        features_filters_by_layer = {}
        features_filters_by_layer[defs_project.PROCESESS_LAYER_NAME] = features_filters
        str_error = GDALTools.remove_features(self.file_path, features_filters_by_layer)
        if not str_error:
            self.process_by_label.pop(process_label)
        return str_error

    def save_map_view(self,
                      map_view_id,
                      map_view_wkb_geometry,
                      update = False):
        str_error = ""
        features = []
        feature = []
        field = {}
        field[defs_gdal.FIELD_NAME_TAG] = defs_project.LOCATIONS_FIELD_NAME
        field[defs_gdal.FIELD_TYPE_TAG] \
            = defs_project.fields_by_layer[defs_project.LOCATIONS_LAYER_NAME][defs_project.LOCATIONS_FIELD_NAME]
        field[defs_gdal.FIELD_VALUE_TAG] = map_view_id
        feature.append(field)
        # field = {}
        # field[defs_gdal.FIELD_NAME_TAG] = defs_project.MANAGEMENT_FIELD_CONTENT
        # field[defs_gdal.FIELD_TYPE_TAG] \
        #     = defs_project.fields_by_layer[defs_project.LOCATIONS_LAYER_NAME][defs_project.MANAGEMENT_FIELD_CONTENT]
        # field[defs_gdal.FIELD_VALUE_TAG] = value_as_string
        # feature.append(field)
        field = {}
        field[defs_gdal.FIELD_NAME_TAG] = defs_project.LOCATIONS_FIELD_GEOMETRY
        field[defs_gdal.FIELD_TYPE_TAG] \
            = defs_project.fields_by_layer[defs_project.LOCATIONS_LAYER_NAME][defs_project.LOCATIONS_FIELD_GEOMETRY]
        field[defs_gdal.FIELD_VALUE_TAG] = map_view_wkb_geometry
        feature.append(field)
        features.append(feature)
        features_by_layer = {}
        features_by_layer[defs_project.LOCATIONS_LAYER_NAME] = features
        if not update:
            str_error = GDALTools.write_features(self.file_path, features_by_layer)
            # str_error = self.gpkg_tools.write(self.file_name,
            #                                   features_by_layer)
        else:
            features_filters = []
            feature_filters= []
            filter = {}
            filter[defs_gdal.FIELD_NAME_TAG] = defs_project.LOCATIONS_FIELD_NAME
            filter[defs_gdal.FIELD_TYPE_TAG] \
                = defs_project.fields_by_layer[defs_project.LOCATIONS_LAYER_NAME][defs_project.LOCATIONS_FIELD_NAME]
            filter[defs_gdal.FIELD_VALUE_TAG] = map_view_id
            feature_filters.append(filter)
            features_filters.append(feature_filters)
            features_filters_by_layer = {}
            features_filters_by_layer[defs_project.LOCATIONS_LAYER_NAME] = features_filters
            str_error = GDALTools.update_features(self.file_path, features_by_layer, features_filters_by_layer)
            # str_error = self.gpkg_tools.update(self.file_name,
            #                                    features_by_layer,
            #                                    features_filters_by_layer)
        return str_error

    def save_management(self,
                        update = False):
        str_error = ""
        value_as_string = str(self.project_definition)
        features = []
        feature = []
        field = {}
        field[defs_gdal.FIELD_NAME_TAG] = defs_project.MANAGEMENT_FIELD_NAME
        field[defs_gdal.FIELD_TYPE_TAG] \
            = defs_project.fields_by_layer[defs_project.MANAGEMENT_LAYER_NAME][defs_project.MANAGEMENT_FIELD_NAME]
        field[defs_gdal.FIELD_VALUE_TAG] = defs_project.PROJECT_DEFINITIONS_MANAGEMENT_FIELD_NAME
        feature.append(field)
        field = {}
        field[defs_gdal.FIELD_NAME_TAG] = defs_project.MANAGEMENT_FIELD_CONTENT
        field[defs_gdal.FIELD_TYPE_TAG] \
            = defs_project.fields_by_layer[defs_project.MANAGEMENT_LAYER_NAME][defs_project.MANAGEMENT_FIELD_CONTENT]
        field[defs_gdal.FIELD_VALUE_TAG] = value_as_string
        feature.append(field)
        geometry_value = None
        field = {}
        field[defs_gdal.FIELD_NAME_TAG] = defs_project.MANAGEMENT_FIELD_GEOMETRY
        field[defs_gdal.FIELD_TYPE_TAG] \
            = defs_project.fields_by_layer[defs_project.MANAGEMENT_LAYER_NAME][defs_project.MANAGEMENT_FIELD_GEOMETRY]
        field[defs_gdal.FIELD_VALUE_TAG] = defs_project.fields_by_layer[
            defs_project.MANAGEMENT_LAYER_NAME][defs_project.MANAGEMENT_FIELD_GEOMETRY]
        feature.append(field)
        features.append(feature)
        features_by_layer = {}
        features_by_layer[defs_project.MANAGEMENT_LAYER_NAME] = features
        if not update:
            str_error = GDALTools.write_features(self.file_path, features_by_layer)
            # str_error = self.gpkg_tools.write(self.file_name,
            #                                   features_by_layer)
        else:
            features_filters = []
            feature_filters= []
            filter = {}
            filter[defs_gdal.FIELD_NAME_TAG] = defs_project.MANAGEMENT_FIELD_NAME
            filter[defs_gdal.FIELD_TYPE_TAG] \
                = defs_project.fields_by_layer[defs_project.MANAGEMENT_LAYER_NAME][defs_project.MANAGEMENT_FIELD_NAME]
            filter[defs_gdal.FIELD_VALUE_TAG] = defs_project.PROJECT_DEFINITIONS_MANAGEMENT_FIELD_NAME
            feature_filters.append(filter)
            features_filters.append(feature_filters)
            features_filters_by_layer = {}
            features_filters_by_layer[defs_project.MANAGEMENT_LAYER_NAME] = features_filters
            str_error = GDALTools.update_features(self.file_path, features_by_layer, features_filters_by_layer)
            # str_error = self.gpkg_tools.update(self.file_name,
            #                                    features_by_layer,
            #                                    features_filters_by_layer)
        return str_error

    def save_process(self,
                     process_content,
                     process_author,
                     process_label,
                     process_description,
                     process_log,
                     process_date_time_as_string,
                     process_output_uclm,
                     process_output_uco,
                     process_content_uclm,
                     process_content_uco):
        str_error = ''
        # if map_view_id in self.map_views:
        #     str_error = ('Exists a previous location with name: {}'.format(map_view_id))
        #     return str_error
        features = []
        feature = []
        field = {}
        field[defs_gdal.FIELD_NAME_TAG] = defs_project.PROCESESS_FIELD_LABEL
        field[defs_gdal.FIELD_TYPE_TAG] \
            = defs_project.fields_by_layer[defs_project.PROCESESS_LAYER_NAME][defs_project.PROCESESS_FIELD_LABEL]
        field[defs_gdal.FIELD_VALUE_TAG] = process_label
        feature.append(field)
        field = {}
        field[defs_gdal.FIELD_NAME_TAG] = defs_project.PROCESESS_FIELD_AUTHOR
        field[defs_gdal.FIELD_TYPE_TAG] \
            = defs_project.fields_by_layer[defs_project.PROCESESS_LAYER_NAME][defs_project.PROCESESS_FIELD_AUTHOR]
        field[defs_gdal.FIELD_VALUE_TAG] = process_author
        feature.append(field)
        field = {}
        field[defs_gdal.FIELD_NAME_TAG] = defs_project.PROCESESS_FIELD_DESCRIPTION
        field[defs_gdal.FIELD_TYPE_TAG] \
            = defs_project.fields_by_layer[defs_project.PROCESESS_LAYER_NAME][defs_project.PROCESESS_FIELD_DESCRIPTION]
        field[defs_gdal.FIELD_VALUE_TAG] = process_description
        feature.append(field)
        field = {}
        field[defs_gdal.FIELD_NAME_TAG] = defs_project.PROCESESS_FIELD_DATE_TIME
        field[defs_gdal.FIELD_TYPE_TAG] \
            = defs_project.fields_by_layer[defs_project.PROCESESS_LAYER_NAME][defs_project.PROCESESS_FIELD_DATE_TIME]
        field[defs_gdal.FIELD_VALUE_TAG] = process_date_time_as_string
        feature.append(field)
        field = {}
        field[defs_gdal.FIELD_NAME_TAG] = defs_project.PROCESESS_FIELD_PROCESS_CONTENT
        field[defs_gdal.FIELD_TYPE_TAG] \
            = defs_project.fields_by_layer[defs_project.PROCESESS_LAYER_NAME][defs_project.PROCESESS_FIELD_PROCESS_CONTENT]
        field[defs_gdal.FIELD_VALUE_TAG] = process_content
        feature.append(field)
        field = {}
        field[defs_gdal.FIELD_NAME_TAG] = defs_project.PROCESESS_FIELD_LOG
        field[defs_gdal.FIELD_TYPE_TAG] \
            = defs_project.fields_by_layer[defs_project.PROCESESS_LAYER_NAME][defs_project.PROCESESS_FIELD_LOG]
        field[defs_gdal.FIELD_VALUE_TAG] = process_log
        feature.append(field)
        field = {}
        field[defs_gdal.FIELD_NAME_TAG] = defs_project.PROCESESS_FIELD_OUTPUT_UCLM
        field[defs_gdal.FIELD_TYPE_TAG] \
            = defs_project.fields_by_layer[defs_project.PROCESESS_LAYER_NAME][defs_project.PROCESESS_FIELD_OUTPUT_UCLM]
        field[defs_gdal.FIELD_VALUE_TAG] = process_output_uclm
        feature.append(field)
        field = {}
        field[defs_gdal.FIELD_NAME_TAG] = defs_project.PROCESESS_FIELD_OUTPUT_UCO
        field[defs_gdal.FIELD_TYPE_TAG] \
            = defs_project.fields_by_layer[defs_project.PROCESESS_LAYER_NAME][defs_project.PROCESESS_FIELD_OUTPUT_UCO]
        field[defs_gdal.FIELD_VALUE_TAG] = process_output_uco
        feature.append(field)
        field = {}
        field[defs_gdal.FIELD_NAME_TAG] = defs_project.PROCESESS_FIELD_CONTENT_UCLM
        field[defs_gdal.FIELD_TYPE_TAG] \
            = defs_project.fields_by_layer[defs_project.PROCESESS_LAYER_NAME][defs_project.PROCESESS_FIELD_CONTENT_UCLM]
        field[defs_gdal.FIELD_VALUE_TAG] = process_content_uclm
        feature.append(field)
        field = {}
        field[defs_gdal.FIELD_NAME_TAG] = defs_project.PROCESESS_FIELD_CONTENT_UCO
        field[defs_gdal.FIELD_TYPE_TAG] \
            = defs_project.fields_by_layer[defs_project.PROCESESS_LAYER_NAME][defs_project.PROCESESS_FIELD_CONTENT_UCO]
        field[defs_gdal.FIELD_VALUE_TAG] = process_content_uco
        feature.append(field)
        field = {}
        field[defs_gdal.FIELD_NAME_TAG] = defs_project.PROCESESS_FIELD_GEOMETRY
        field[defs_gdal.FIELD_TYPE_TAG] \
            = defs_project.fields_by_layer[defs_project.PROCESESS_LAYER_NAME][defs_project.PROCESESS_FIELD_GEOMETRY]
        field[defs_gdal.FIELD_VALUE_TAG] = defs_project.fields_by_layer[
            defs_project.PROCESESS_LAYER_NAME][defs_project.PROCESESS_FIELD_GEOMETRY]
        feature.append(field)
        features.append(feature)
        features_by_layer = {}
        features_by_layer[defs_project.PROCESESS_LAYER_NAME] = features
        if not process_label in self.process_by_label:
            str_error = GDALTools.write_features(self.file_path, features_by_layer)
            # str_error = self.gpkg_tools.write(self.file_name,
            #                                   features_by_layer)
            if not str_error:
                self.process_by_label[process_label] = {}
        else:
            features_filters = []
            feature_filters= []
            filter = {}
            filter[defs_gdal.FIELD_NAME_TAG] = defs_project.PROCESESS_FIELD_LABEL
            filter[defs_gdal.FIELD_TYPE_TAG] \
                = defs_project.fields_by_layer[defs_project.PROCESESS_LAYER_NAME][defs_project.PROCESESS_FIELD_LABEL]
            filter[defs_gdal.FIELD_VALUE_TAG] = process_label
            feature_filters.append(filter)
            features_filters.append(feature_filters)
            features_filters_by_layer = {}
            features_filters_by_layer[defs_project.PROCESESS_LAYER_NAME] = features_filters
            str_error = GDALTools.update_features(self.file_path, features_by_layer, features_filters_by_layer)
        if not str_error:
            self.process_by_label[process_label][defs_project.PROCESESS_FIELD_LABEL] = process_label
            self.process_by_label[process_label][defs_project.PROCESESS_FIELD_AUTHOR] = process_author
            self.process_by_label[process_label][defs_project.PROCESESS_FIELD_DESCRIPTION] = process_description
            self.process_by_label[process_label][defs_project.PROCESESS_FIELD_DATE_TIME] = process_date_time_as_string
            self.process_by_label[process_label][defs_project.PROCESESS_FIELD_PROCESS_CONTENT] = process_content
            self.process_by_label[process_label][defs_project.PROCESESS_FIELD_LOG] = process_log
            self.process_by_label[process_label][defs_project.PROCESESS_FIELD_OUTPUT_UCLM] = process_output_uclm
            self.process_by_label[process_label][defs_project.PROCESESS_FIELD_OUTPUT_UCO] = process_output_uco
            self.process_by_label[process_label][defs_project.PROCESESS_FIELD_CONTENT_UCLM] = process_content_uclm
            self.process_by_label[process_label][defs_project.PROCESESS_FIELD_CONTENT_UCO] = process_content_uco
        return str_error

    def set_definition_from_json(self, json_content):
        str_error = ''
        if not defs_project.PROJECT_DEFINITIONS_TAG_NAME in json_content:
            str_error = ("No {} in json content {}".format(defs_project.PROJECT_DEFINITIONS_TAG_NAME,
                                                           defs_project.PROJECT_DEFINITIONS_TAG))
            return str_error
        if not defs_project.PROJECT_DEFINITIONS_TAG_TAG in json_content:
            str_error = ("No {} in json content {}".format(defs_project.PROJECT_DEFINITIONS_TAG_TAG,
                                                           defs_project.PROJECT_DEFINITIONS_TAG))
            return str_error
        if not defs_project.PROJECT_DEFINITIONS_TAG_AUTHOR in json_content:
            str_error = ("No {} in json content {}".format(defs_project.PROJECT_DEFINITIONS_TAG_AUTHOR,
                                                           defs_project.PROJECT_DEFINITIONS_TAG))
            return str_error
        if not defs_project.PROJECT_DEFINITIONS_TAG_PROJECTED_CRS in json_content:
            str_error = ("No {} in json content {}".format(defs_project.PROJECT_DEFINITIONS_TAG_PROJECTED_CRS,
                                                           defs_project.PROJECT_DEFINITIONS_TAG))
            return str_error
        if not defs_project.PROJECT_DEFINITIONS_TAG_VERTICAL_CRS in json_content:
            str_error = ("No {} in json content {}".format(defs_project.PROJECT_DEFINITIONS_TAG_VERTICAL_CRS,
                                                           defs_project.PROJECT_DEFINITIONS_TAG))
            return str_error
        if not defs_project.PROJECT_DEFINITIONS_TAG_OUTPUT_PATH in json_content:
            str_error = ("No {} in json content {}".format(defs_project.PROJECT_DEFINITIONS_TAG_OUTPUT_PATH,
                                                           defs_project.PROJECT_DEFINITIONS_TAG))
            return str_error
        if not defs_project.PROJECT_DEFINITIONS_TAG_START_DATE in json_content:
            str_error = ("No {} in json content {}".format(defs_project.PROJECT_DEFINITIONS_TAG_START_DATE,
                                                           defs_project.PROJECT_DEFINITIONS_TAG))
            return str_error
        if not defs_project.PROJECT_DEFINITIONS_TAG_FINISH_DATE in json_content:
            str_error = ("No {} in json content {}".format(defs_project.PROJECT_DEFINITIONS_TAG_FINISH_DATE,
                                                           defs_project.PROJECT_DEFINITIONS_TAG))
            return str_error
        name = json_content[defs_project.PROJECT_DEFINITIONS_TAG_NAME]
        tag = json_content[defs_project.PROJECT_DEFINITIONS_TAG_TAG]
        author = json_content[defs_project.PROJECT_DEFINITIONS_TAG_AUTHOR]
        crs_projected_id = json_content[defs_project.PROJECT_DEFINITIONS_TAG_PROJECTED_CRS]
        crs_vertical_id = json_content[defs_project.PROJECT_DEFINITIONS_TAG_VERTICAL_CRS]
        output_path = json_content[defs_project.PROJECT_DEFINITIONS_TAG_OUTPUT_PATH]
        description = json_content[defs_project.PROJECT_DEFINITIONS_TAG_DESCRIPTION]
        start_date = json_content[defs_project.PROJECT_DEFINITIONS_TAG_START_DATE]
        if start_date:
            date_start_date = QDate.fromString(start_date, defs_main.QDATE_TO_STRING_FORMAT)
            if not date_start_date.isValid():
                str_error = ("Invalid date: {} for format: {}".format(start_date, defs_main.QDATE_TO_STRING_FORMAT))
                return str_error
        finish_date = json_content[defs_project.PROJECT_DEFINITIONS_TAG_FINISH_DATE]
        if finish_date:
            date_finish_date = QDate.fromString(finish_date, defs_main.QDATE_TO_STRING_FORMAT)
            if not date_finish_date.isValid():
                str_error = ("Invalid date: {} for format: {}".format(finish_date, defs_main.QDATE_TO_STRING_FORMAT))
                return str_error
        self.project_definition[defs_project.PROJECT_DEFINITIONS_TAG_NAME] = name
        self.project_definition[defs_project.PROJECT_DEFINITIONS_TAG_TAG] = tag
        self.project_definition[defs_project.PROJECT_DEFINITIONS_TAG_AUTHOR] = author
        self.project_definition[defs_project.PROJECT_DEFINITIONS_TAG_PROJECTED_CRS] = crs_projected_id
        self.project_definition[defs_project.PROJECT_DEFINITIONS_TAG_VERTICAL_CRS] = crs_vertical_id
        self.project_definition[defs_project.PROJECT_DEFINITIONS_TAG_OUTPUT_PATH] = output_path
        self.project_definition[defs_project.PROJECT_DEFINITIONS_TAG_DESCRIPTION] = description
        self.project_definition[defs_project.PROJECT_DEFINITIONS_TAG_START_DATE] = start_date
        self.project_definition[defs_project.PROJECT_DEFINITIONS_TAG_FINISH_DATE] = finish_date

    def update_map_view(self,
                        map_view_id,
                        map_view_wkb_geometry):
        str_error = ''
        if not map_view_id in self.map_views:
            str_error = ('Not exists location with name: {}'.format(map_view_id))
            return str_error
        update = True
        return self.save_map_view(map_view_id,
                                  map_view_wkb_geometry,
                                  update)

    def update_process(self,
                       original_process_label,
                       process_label): # is modified in self.processes
        str_error = ''
        if not process_label in self.process_by_label:
            str_error = ('Not exists process: {}'.format(process_label))
            return str_error
        features = []
        feature = []
        field = {}
        field[defs_gdal.FIELD_NAME_TAG] = defs_project.PROCESESS_FIELD_LABEL
        field[defs_gdal.FIELD_TYPE_TAG] \
            = defs_project.fields_by_layer[defs_project.PROCESESS_LAYER_NAME][defs_project.PROCESESS_FIELD_LABEL]
        field[defs_gdal.FIELD_VALUE_TAG] = process_label
        feature.append(field)
        field = {}
        field[defs_gdal.FIELD_NAME_TAG] = defs_project.PROCESESS_FIELD_AUTHOR
        field[defs_gdal.FIELD_TYPE_TAG] \
            = defs_project.fields_by_layer[defs_project.PROCESESS_LAYER_NAME][defs_project.PROCESESS_FIELD_AUTHOR]
        field[defs_gdal.FIELD_VALUE_TAG] = self.process_by_label[process_label][defs_project.PROCESESS_FIELD_AUTHOR]
        feature.append(field)
        field = {}
        field[defs_gdal.FIELD_NAME_TAG] = defs_project.PROCESESS_FIELD_DESCRIPTION
        field[defs_gdal.FIELD_TYPE_TAG] \
            = defs_project.fields_by_layer[defs_project.PROCESESS_LAYER_NAME][defs_project.PROCESESS_FIELD_DESCRIPTION]
        field[defs_gdal.FIELD_VALUE_TAG] = self.process_by_label[process_label][defs_project.PROCESESS_FIELD_DESCRIPTION]
        feature.append(field)
        field = {}
        field[defs_gdal.FIELD_NAME_TAG] = defs_project.PROCESESS_FIELD_DATE_TIME
        field[defs_gdal.FIELD_TYPE_TAG] \
            = defs_project.fields_by_layer[defs_project.PROCESESS_LAYER_NAME][defs_project.PROCESESS_FIELD_DATE_TIME]
        field[defs_gdal.FIELD_VALUE_TAG] = self.process_by_label[process_label][defs_project.PROCESESS_FIELD_DATE_TIME]
        feature.append(field)
        field = {}
        field[defs_gdal.FIELD_NAME_TAG] = defs_project.PROCESESS_FIELD_PROCESS_CONTENT
        field[defs_gdal.FIELD_TYPE_TAG] \
            = defs_project.fields_by_layer[defs_project.PROCESESS_LAYER_NAME][defs_project.PROCESESS_FIELD_PROCESS_CONTENT]
        field[defs_gdal.FIELD_VALUE_TAG] = self.process_by_label[process_label][defs_project.PROCESESS_FIELD_PROCESS_CONTENT]
        feature.append(field)
        field = {}
        field[defs_gdal.FIELD_NAME_TAG] = defs_project.PROCESESS_FIELD_LOG
        field[defs_gdal.FIELD_TYPE_TAG] \
            = defs_project.fields_by_layer[defs_project.PROCESESS_LAYER_NAME][defs_project.PROCESESS_FIELD_LOG]
        field[defs_gdal.FIELD_VALUE_TAG] = self.process_by_label[process_label][defs_project.PROCESESS_FIELD_LOG]
        feature.append(field)
        field = {}
        field[defs_gdal.FIELD_NAME_TAG] = defs_project.PROCESESS_FIELD_CONTENT_UCLM
        field[defs_gdal.FIELD_TYPE_TAG] \
            = defs_project.fields_by_layer[defs_project.PROCESESS_LAYER_NAME][defs_project.PROCESESS_FIELD_CONTENT_UCLM]
        field[defs_gdal.FIELD_VALUE_TAG] = self.process_by_label[process_label][defs_project.PROCESESS_FIELD_CONTENT_UCLM]
        feature.append(field)
        field = {}
        field[defs_gdal.FIELD_NAME_TAG] = defs_project.PROCESESS_FIELD_CONTENT_UCO
        field[defs_gdal.FIELD_TYPE_TAG] \
            = defs_project.fields_by_layer[defs_project.PROCESESS_LAYER_NAME][defs_project.PROCESESS_FIELD_CONTENT_UCO]
        field[defs_gdal.FIELD_VALUE_TAG] = self.process_by_label[process_label][defs_project.PROCESESS_FIELD_CONTENT_UCO]
        feature.append(field)
        field = {}
        field[defs_gdal.FIELD_NAME_TAG] = defs_project.PROCESESS_FIELD_GEOMETRY
        field[defs_gdal.FIELD_TYPE_TAG] \
            = defs_project.fields_by_layer[defs_project.PROCESESS_LAYER_NAME][defs_project.PROCESESS_FIELD_GEOMETRY]
        field[defs_gdal.FIELD_VALUE_TAG] = defs_project.fields_by_layer[
            defs_project.PROCESESS_LAYER_NAME][defs_project.PROCESESS_FIELD_GEOMETRY]
        feature.append(field)
        features.append(feature)
        features_by_layer = {}
        features_by_layer[defs_project.PROCESESS_LAYER_NAME] = features
        features_filters = []
        feature_filters = []
        filter = {}
        filter[defs_gdal.FIELD_NAME_TAG] = defs_project.PROCESESS_FIELD_LABEL
        filter[defs_gdal.FIELD_TYPE_TAG] \
            = defs_project.fields_by_layer[defs_project.PROCESESS_LAYER_NAME][defs_project.PROCESESS_FIELD_LABEL]
        filter[defs_gdal.FIELD_VALUE_TAG] = original_process_label
        feature_filters.append(filter)
        features_filters.append(feature_filters)
        features_filters_by_layer = {}
        features_filters_by_layer[defs_project.PROCESESS_LAYER_NAME] = features_filters
        str_error = GDALTools.update_features(self.file_path, features_by_layer, features_filters_by_layer)
        return str_error
