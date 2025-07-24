# authors:
# David Hernandez Lopez, david.hernandez@uclm.es
import os
import sys

current_path = os.path.dirname(__file__)
sys.path.append(os.path.join(current_path, '..'))
# sys.path.insert(0, '..')

IMAGES_PATH = "images"
PAFYCTOOLS_ICON_FILE = "pafyc.ico"
QDATE_TO_STRING_FORMAT = "yyyy:MM:dd"
DATE_TIME_STRING_FORMAT = "%Y%m%d %H:%M:%S"
QDATETIME_TO_STRING_FORMAT_FOR_FILE_NAME = "yyyyMMdd_hhmmss"
TEMPLATES_PATH = "templates"
SETTINGS_FILE = "settings.ini"
NO_COMBO_SELECT = " ... "
EPSG_STRING_PREFIX = "EPSG:"



