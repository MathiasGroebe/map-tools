# -*- coding: utf-8 -*-
# ***************************************************************************
# __init__.py  -  Map tools plugin for QGIS
# ---------------------
#     begin                : 2024-02-23
#     copyright            : (C) 2024 by Mathias Gröbe
#     email                : mathias dot groebe at gmail dot com
# ***************************************************************************
# *                                                                         *
# *   This program is free software; you can redistribute it and/or modify  *
# *   it under the terms of the GNU General Public License as published by  *
# *   the Free Software Foundation; either version 2 of the License, or     *
# *   (at your option) any later version.                                   *
# *                                                                         *
# ***************************************************************************

def classFactory(iface):  # pylint: disable=invalid-name
    """Load class from file map-tools

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .maptools import MapToolsPlugin

    return MapToolsPlugin(iface)