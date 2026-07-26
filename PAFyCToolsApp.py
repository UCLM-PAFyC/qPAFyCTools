# authors:
# David Hernandez Lopez, david.hernandez@uclm.es

import sys, os
from qgis.PyQt.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QApplication

current_path = os.path.dirname(os.path.realpath(__file__))

from pafyc_gui.PAFyCToolsDialog import PAFyCToolsDialog
from pafyc_defs import defs_main

def main():
    app = QApplication(sys.argv)
    current_path = os.path.dirname(os.path.realpath(__file__))
    path_file_qsettings = current_path + "/" + defs_main.SETTINGS_FILE
    settings = QSettings(path_file_qsettings, QSettings.IniFormat)
    dialog = PAFyCToolsDialog(settings, current_path)
    icon_path = current_path + "/" + defs_main.IMAGES_PATH + "/" + defs_main.PAFYCTOOLS_ICON_FILE
    dialog.setWindowIcon(QIcon(icon_path))
    dialog.show()
    app.exec()

if __name__ == '__main__':
    main()
