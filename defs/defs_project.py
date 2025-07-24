# authors:
# David Hernandez Lopez, david.hernandez@uclm.es
import os
import sys

current_path = os.path.dirname(__file__)
sys.path.append(os.path.join(current_path, '..'))

from defs import defs_paths
common_libs_absolute_path = os.path.join(current_path, defs_paths.COMMON_LIBS_RELATIVE_PATH)
sys.path.append(common_libs_absolute_path)
from pyLibCRSs import CRSsDefines as defs_crs
from pyLibGDAL import defs_gdal

CRS_PROJECTED_DEFAULT = "EPSG:25830"
CRS_VERTICAL_DEFAULT = "EPSG:5782"

TEMPLATE_PROJECT_FILE = "template.gpkg"
create_options = ['CRS_WKT_EXTENSION=YES',
                  'METADATA_TABLES=YES']

PROJECT_FILE_SUFFIX = '.gpkg'

MANAGEMENT_LAYER_NAME = 'management'
MANAGEMENT_FIELD_NAME = 'name'
MANAGEMENT_FIELD_CONTENT = 'content'
MANAGEMENT_FIELD_CONTENT_UCLM = 'content_uclm'
MANAGEMENT_FIELD_CONTENT_UCO = 'content_uco'
MANAGEMENT_FIELD_GEOMETRY = defs_gdal.LAYERS_GEOMETRY_TAG
fields_by_layer = {}
fields_by_layer[MANAGEMENT_LAYER_NAME] = {}
fields_by_layer[MANAGEMENT_LAYER_NAME][MANAGEMENT_FIELD_NAME] = defs_gdal.type_by_name['string']
fields_by_layer[MANAGEMENT_LAYER_NAME][MANAGEMENT_FIELD_CONTENT] = defs_gdal.type_by_name['string']
fields_by_layer[MANAGEMENT_LAYER_NAME][MANAGEMENT_FIELD_CONTENT_UCLM] = defs_gdal.type_by_name['string']
fields_by_layer[MANAGEMENT_LAYER_NAME][MANAGEMENT_FIELD_CONTENT_UCO] = defs_gdal.type_by_name['string']
fields_by_layer[MANAGEMENT_LAYER_NAME][MANAGEMENT_FIELD_GEOMETRY] = defs_gdal.geometry_type_by_name['none']

LOCATIONS_LAYER_NAME = 'locations'
LOCATIONS_FIELD_NAME = 'name'
LOCATIONS_FIELD_CONTENT = 'content'
LOCATIONS_FIELD_CONTENT_UCLM = 'content_uclm'
LOCATIONS_FIELD_CONTENT_UCO = 'content_uco'
LOCATIONS_FIELD_GEOMETRY = defs_gdal.LAYERS_GEOMETRY_TAG
fields_by_layer[LOCATIONS_LAYER_NAME] = {}
fields_by_layer[LOCATIONS_LAYER_NAME][LOCATIONS_FIELD_NAME] = defs_gdal.type_by_name['string']
fields_by_layer[LOCATIONS_LAYER_NAME][LOCATIONS_FIELD_CONTENT] = defs_gdal.type_by_name['string']
fields_by_layer[LOCATIONS_LAYER_NAME][LOCATIONS_FIELD_CONTENT_UCLM] = defs_gdal.type_by_name['string']
fields_by_layer[LOCATIONS_LAYER_NAME][LOCATIONS_FIELD_CONTENT_UCO] = defs_gdal.type_by_name['string']
fields_by_layer[LOCATIONS_LAYER_NAME][LOCATIONS_FIELD_GEOMETRY] = defs_gdal.geometry_type_by_name['polygon']

PROJECT_PROCESSES_DIALOG_TITLE = 'Project processes'
PROCESESS_LAYER_NAME = 'processes'
PROCESESS_FIELD_LABEL = 'label'
PROCESESS_FIELD_AUTHOR = 'author'
PROCESESS_FIELD_DESCRIPTION = 'description'
PROCESESS_FIELD_DATE_TIME = 'date_time'
PROCESESS_FIELD_PROCESS_CONTENT = 'process_content'
PROCESESS_FIELD_LOG = 'log'
PROCESESS_FIELD_CONTENT_UCLM = 'content_uclm'
PROCESESS_FIELD_CONTENT_UCO = 'content_uco'
PROCESESS_FIELD_GEOMETRY = defs_gdal.LAYERS_GEOMETRY_TAG
fields_by_layer[PROCESESS_LAYER_NAME] = {}
fields_by_layer[PROCESESS_LAYER_NAME][PROCESESS_FIELD_LABEL] = defs_gdal.type_by_name['string']
fields_by_layer[PROCESESS_LAYER_NAME][PROCESESS_FIELD_AUTHOR] = defs_gdal.type_by_name['string']
fields_by_layer[PROCESESS_LAYER_NAME][PROCESESS_FIELD_DESCRIPTION] = defs_gdal.type_by_name['string']
fields_by_layer[PROCESESS_LAYER_NAME][PROCESESS_FIELD_DATE_TIME] = defs_gdal.type_by_name['string']
fields_by_layer[PROCESESS_LAYER_NAME][PROCESESS_FIELD_PROCESS_CONTENT] = defs_gdal.type_by_name['string']
fields_by_layer[PROCESESS_LAYER_NAME][PROCESESS_FIELD_LOG] = defs_gdal.type_by_name['string']
fields_by_layer[PROCESESS_LAYER_NAME][PROCESESS_FIELD_CONTENT_UCLM] = defs_gdal.type_by_name['string']
fields_by_layer[PROCESESS_LAYER_NAME][PROCESESS_FIELD_CONTENT_UCO] = defs_gdal.type_by_name['string']
fields_by_layer[PROCESESS_LAYER_NAME][PROCESESS_FIELD_GEOMETRY] = defs_gdal.geometry_type_by_name['none']
PROCESESS_FIELD_LABEL_TAG = 'Label'
PROCESESS_FIELD_AUTHOR_TAG = 'Author'
PROCESESS_FIELD_DESCRIPTION_TAG = 'Description'
PROCESESS_FIELD_DATE_TIME_TAG = 'Date and time'
PROCESESS_FIELD_PROCESS_CONTENT_TAG = 'Process content'
PROCESESS_FIELD_LOG_TAG = 'Log'
PROCESESS_FIELD_CONTENT_UCLM_TAG = 'Content UCLM'
PROCESESS_FIELD_CONTENT_UCO_TAG = 'Content UCO'
PROCESESS_FIELD_LABEL_TOOLTIP = 'Label'
PROCESESS_FIELD_AUTHOR_TOOLTIP = 'Author'
PROCESESS_FIELD_DESCRIPTION_TOOLTIP = 'Description'
PROCESESS_FIELD_DATE_TIME_TOOLTIP = 'Date and time'
PROCESESS_FIELD_PROCESS_CONTENT_TOOLTIP = 'Process content'
PROCESESS_FIELD_LOG_TOOLTIP = 'Log'
PROCESESS_FIELD_CONTENT_UCLM_TOOLTIP = 'Content UCLM'
PROCESESS_FIELD_CONTENT_UCO_TOOLTIP = 'Content UCO'
project_processes_dialog_header=[PROCESESS_FIELD_LABEL_TAG,
                                 PROCESESS_FIELD_AUTHOR_TAG,
                                 PROCESESS_FIELD_DESCRIPTION_TAG,
                                 PROCESESS_FIELD_DATE_TIME_TAG,
                                 PROCESESS_FIELD_PROCESS_CONTENT_TAG,
                                 PROCESESS_FIELD_LOG_TAG,
                                 PROCESESS_FIELD_CONTENT_UCLM_TAG,
                                 PROCESESS_FIELD_CONTENT_UCO_TAG]
project_processes_dialog_field_by_header_tag = {}
project_processes_dialog_field_by_header_tag[PROCESESS_FIELD_LABEL_TAG] = PROCESESS_FIELD_LABEL
project_processes_dialog_field_by_header_tag[PROCESESS_FIELD_AUTHOR_TAG] = PROCESESS_FIELD_AUTHOR
project_processes_dialog_field_by_header_tag[PROCESESS_FIELD_DESCRIPTION_TAG] = PROCESESS_FIELD_DESCRIPTION
project_processes_dialog_field_by_header_tag[PROCESESS_FIELD_DATE_TIME_TAG] = PROCESESS_FIELD_DATE_TIME
project_processes_dialog_field_by_header_tag[PROCESESS_FIELD_PROCESS_CONTENT_TAG] = PROCESESS_FIELD_PROCESS_CONTENT
project_processes_dialog_field_by_header_tag[PROCESESS_FIELD_LOG_TAG] = PROCESESS_FIELD_LOG
project_processes_dialog_field_by_header_tag[PROCESESS_FIELD_CONTENT_UCLM_TAG] = PROCESESS_FIELD_CONTENT_UCLM
project_processes_dialog_field_by_header_tag[PROCESESS_FIELD_CONTENT_UCO_TAG] = PROCESESS_FIELD_CONTENT_UCO
project_processes_dialog_tooltip_by_header_tag = {}
project_processes_dialog_tooltip_by_header_tag[PROCESESS_FIELD_LABEL_TAG] = PROCESESS_FIELD_LABEL_TOOLTIP
project_processes_dialog_tooltip_by_header_tag[PROCESESS_FIELD_AUTHOR_TAG] = PROCESESS_FIELD_AUTHOR_TOOLTIP
project_processes_dialog_tooltip_by_header_tag[PROCESESS_FIELD_DESCRIPTION_TAG] = PROCESESS_FIELD_DESCRIPTION_TOOLTIP
project_processes_dialog_tooltip_by_header_tag[PROCESESS_FIELD_DATE_TIME_TAG] = PROCESESS_FIELD_DATE_TIME_TOOLTIP
project_processes_dialog_tooltip_by_header_tag[PROCESESS_FIELD_PROCESS_CONTENT_TAG] = PROCESESS_FIELD_PROCESS_CONTENT_TOOLTIP
project_processes_dialog_tooltip_by_header_tag[PROCESESS_FIELD_LOG_TAG] = PROCESESS_FIELD_LOG_TOOLTIP
project_processes_dialog_tooltip_by_header_tag[PROCESESS_FIELD_CONTENT_UCLM_TAG] = PROCESESS_FIELD_CONTENT_UCLM_TOOLTIP
project_processes_dialog_tooltip_by_header_tag[PROCESESS_FIELD_CONTENT_UCO_TAG] = PROCESESS_FIELD_CONTENT_UCO_TOOLTIP


PROJECT_DEFINITION_DIALOG_TITLE = "Project Definition"
PROJECT_DEFINITIONS_MANAGEMENT_FIELD_NAME = "Project Definition"
PROJECT_DEFINITIONS_TAG = "ProjectDefinition"
PROJECT_DEFINITIONS_TAG_NAME = "Name"
PROJECT_DEFINITIONS_TAG_TAG = "Tag"
PROJECT_DEFINITIONS_TAG_AUTHOR = "Author"
# PROJECT_DEFINITIONS_TAG_GEO3D_CRS = defs_crs.CRS_GEODETIC_3D_LABEL
# PROJECT_DEFINITIONS_TAG_GEO2D_CRS = defs_crs.CRS_GEODETIC_2D_LABEL
# PROJECT_DEFINITIONS_TAG_ECEF_CRS = defs_crs.CRS_ECEF_LABEL
PROJECT_DEFINITIONS_TAG_PROJECTED_CRS = defs_crs.CRS_PROJECTED_LABEL
PROJECT_DEFINITIONS_TAG_VERTICAL_CRS = defs_crs.CRS_VERTICAL_LABEL
PROJECT_DEFINITIONS_TAG_OUTPUT_PATH = "OutputPath"
PROJECT_DEFINITIONS_TAG_DESCRIPTION = "Description"
PROJECT_DEFINITIONS_TAG_START_DATE = "StartDate"
PROJECT_DEFINITIONS_TAG_FINISH_DATE = "FinishDate"
