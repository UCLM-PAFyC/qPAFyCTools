# -*- coding: utf-8 -*-
"""
/***************************************************************************
Name			 	 : PAFyCTools
Description          : Q QGIS plugin for Precision Agroforestry Tools
Date                 : 04/June/2025
copyright            : (C) David Hernandez Lopez
email                : david.hernandez@uclm.es
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


def classFactory(iface):
    # load GeoCoding class from file GeoCoding
    from .qPAFyCTools import qPAFyCTools
    return qPAFyCTools(iface)
