# -*- coding: utf-8 -*-
# ***************************************************************************
# __init__.py  -  Map-tools plugin for QGIS
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

import os.path
from PyQt5.QtWidgets import QApplication
from qgis.core import Qgis, QgsMapLayer, QgsRasterLayer, QgsProject, QgsCoordinateReferenceSystem, QgsApplication
from qgis.gui import QgsMessageBar, QgsExtentWidget, QgsProjectionSelectionWidget
from qgis.utils import iface
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QToolButton, QLabel, QFileDialog
from qgis.PyQt.QtCore import QStandardPaths

from .maptools_provider import MaptoolsAlgorithms


class MapToolsPlugin:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):

        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        self.plugin_name = 'Maptools'

    def initProcessing(self):
        """Init Processing provider for QGIS >= 3.8."""
        
        self.provider = MaptoolsAlgorithms()
        QgsApplication.processingRegistry().addProvider(self.provider)        


    def initGui(self):

        self.toolbar = self.iface.addToolBar("map-tools")
        self.toolbar.setObjectName("map-tools")
        self.toolbar.setVisible(True)
        
        self.toolbarName = QLabel(self.plugin_name + ":")
        self.toolbar.addWidget(self.toolbarName)
    
        self.reloadButton = QToolButton()
        self.reloadButton.setText("Reload data")
        self.reloadButton.setToolTip("Reload data of the layer and repaint map for selected layers")
        self.reloadButton.clicked.connect(self.reload)
        self.toolbar.addWidget(self.reloadButton)

        self.reopenButton = QToolButton()
        self.reopenButton.setText("Reload layer")
        self.reopenButton.setToolTip("Reload layer settings (CRS, fields, extents) and repaint map for selected layers")
        self.reopenButton.clicked.connect(self.reopen)
        self.toolbar.addWidget(self.reopenButton)

        self.toolbar.addSeparator()
        
        self.wktButton = QToolButton()
        self.wktButton.setText("Feature WKT")
        self.wktButton.setToolTip("Copy WKT of the selected features of the activ layer")
        self.wktButton.clicked.connect(self.getWkt)
        self.toolbar.addWidget(self.wktButton)
        
        self.toolbar.addSeparator()
        
        self.osmButton = QToolButton()
        self.osmButton.setText("OSM Basemap")
        self.osmButton.setToolTip("Add OSM Carto base map")
        self.osmButton.clicked.connect(self.addOSM)
        self.toolbar.addWidget(self.osmButton)
        
        self.toolbar.addSeparator()
        
        self.loadQmlButton = QToolButton()
        self.loadQmlButton.setText("Load QML-Style")
        self.loadQmlButton.setToolTip("Load QML style from file and apply it to the active layer")
        self.loadQmlButton.clicked.connect(self.loadQML)
        self.toolbar.addWidget(self.loadQmlButton)   
        
        self.saveQmlButton = QToolButton()
        self.saveQmlButton.setText("Save QML-Style")
        self.saveQmlButton.setToolTip("Save layer style of the active layer to QML file")
        self.saveQmlButton.clicked.connect(self.saveQML)
        self.toolbar.addWidget(self.saveQmlButton)  
        
        self.toolbar.addSeparator()
        
        self.extentName = QLabel("Extent: ")
        self.toolbar.addWidget(self.extentName)
        
        self.extentWidget = QgsExtentWidget()
        self.extentWidget.setMapCanvas(self.iface.mapCanvas())
        self.extentWidget.setOriginalExtent(self.iface.mapCanvas().extent(), QgsProject.instance().crs())
        self.extentWidget.setCurrentExtent(self.iface.mapCanvas().extent(), QgsProject.instance().crs())
        self.outputCrs = QgsCoordinateReferenceSystem.fromOgcWmsCrs("EPSG:4326")
        self.extentWidget.setOutputCrs(self.outputCrs)
        self.toolbar.addWidget(self.extentWidget)
        self.iface.mapCanvas().extentsChanged.connect(self.updateExtentWidget)

        self.copyButton = QToolButton()
        self.copyButton.setText("Copy extent")
        self.copyButton.setToolTip("Copy extent xmin, ymin, xmax, ymax")
        self.copyButton.clicked.connect(self.copyExtent)
        self.toolbar.addWidget(self.copyButton)

        self.initProcessing()

    def updateExtentWidget(self):
        """Update QgsExtentWidget when map extent changes."""
        self.extentWidget.setCurrentExtent(self.iface.mapCanvas().extent(), QgsProject.instance().crs())
        self.extentWidget.update()
        # self.iface.messageBar().pushMessage(self.plugin_name, "Extent widget updated", level=Qgis.Info, duration=3)
        
        
    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""

        self.iface.mapCanvas().extentsChanged.disconnect(self.updateExtentWidget)
        self.reloadButton.clicked.disconnect(self.reload)
        self.reopenButton.clicked.disconnect(self.reopen)
        self.wktButton.clicked.disconnect(self.getWkt)
        self.osmButton.clicked.disconnect(self.addOSM)
        self.loadQmlButton.clicked.disconnect(self.loadQML)
        self.saveQmlButton.clicked.disconnect(self.saveQML)
        self.copyButton.clicked.disconnect(self.copyExtent)

        self.iface.mainWindow().removeToolBar(self.toolbar)

        QgsApplication.processingRegistry().removeProvider(self.provider)

    def reload(self):
        """Reload selected layer(s)."""
        layers = self.iface.layerTreeView().selectedLayers()

        if len(layers) == 0:
            self.iface.messageBar().pushMessage(self.plugin_name, "No selected layer(s).", level=Qgis.Warning, duration=6 )
        else:
            for layer in layers:
                layer.reload()
                layer.triggerRepaint()
                self.iface.messageBar().pushMessage(self.plugin_name, f"Reload Layer {layer.name()}", level=Qgis.Success, duration=3)

    def reopen(self):
        """Reopen selected layer(s), which also updates the extent and crs in contrast to `reload`."""
        layers = self.iface.layerTreeView().selectedLayers()

        if len(layers) == 0:
            self.iface.messageBar().pushMessage(self.plugin_name, "No selected layer(s).", level=Qgis.Warning, duration=6 )
        else:
            for layer in layers:
                
                if layer.type() == QgsMapLayer.VectorLayer:
                
                    layer.setDataSource(layer.source(), layer.name(), layer.providerType())
                    layer.setCrs(layer.dataProvider().sourceCrs())
                    layer.setExtent(layer.dataProvider().sourceExtent())
                    layer.triggerRepaint()

                    self.iface.messageBar().pushMessage(self.plugin_name, f"Reopen Layer {layer.name()}", level=Qgis.Success, duration=3)
                
                else:
                    self.iface.messageBar().pushMessage(self.plugin_name, "Only implmented for vector layers", level=Qgis.Warning, duration=6 )
                    
                
    def getWkt(self):
        """Get WKT of selected features in the active layer
        """
        
        layer = self.iface.activeLayer()
        
        if layer.type() == QgsMapLayer.VectorLayer:
            
            output = ""
            for feature in layer.selectedFeatures():
                output = output + " " + feature.geometry().asWkt()
                
            clipboard = QApplication.clipboard()
            clipboard.setText(output)
                
            self.iface.messageBar().pushMessage(self.plugin_name, "Copied feature WKT to clipboard", level=Qgis.Success, duration=3)
                
        else:
            self.iface.messageBar().pushMessage(self.plugin_name, "Works only for vector layers", level=Qgis.Warning, duration=6 )

    def addOSM(self):
        layer_url = 'type=xyz&url=https://tile.openstreetmap.org/%7Bz%7D/%7Bx%7D/%7By%7D.png&zmax=19&zmin=0&crs=EPSG3857'
        layer = QgsRasterLayer(layer_url, 'OpenStreetMap', 'wms')  

        if layer.isValid():
            QgsProject.instance().addMapLayer(layer)
        else:
            self.iface.messageBar().pushMessage(self.plugin_name, "Error adding OSM layer", level=Qgis.Warning, duration=6 )
            
        # TODO: Add layer under all other layers and set resampling
        # https://qgis.org/pyqgis/master/gui/QgsLayerTreeViewDefaultActions.html#qgis.gui.QgsLayerTreeViewDefaultActions.actionMoveToBottom
        
    def loadQML(self):
        """Load QML layer style from file
        """
        
        layer = self.iface.activeLayer()
        dialog = QFileDialog()
        home_dir = str(QStandardPaths.writableLocation(QStandardPaths.HomeLocation))
        filepath, extension = (dialog.getOpenFileName(None, "Load QGIS-Style from QML", home_dir, "*.qml")) 
        
        if filepath.endswith(".qml"):
            layer.loadNamedStyle(filepath)
            layer.triggerRepaint()
            
            self.iface.messageBar().pushMessage(self.plugin_name, f"Loaded style for layer '{layer.name()}'", level=Qgis.Success, duration=3)
        
        else:
            self.iface.messageBar().pushMessage(self.plugin_name, "No QML style selected!", level=Qgis.Warning, duration=6 )
            
    def saveQML(self):
        """ Save layer style to QML-file"""
        
        layer = self.iface.activeLayer()
        dialog = QFileDialog()
        dialog.setDefaultSuffix("qml")  
        home_dir = str(QStandardPaths.writableLocation(QStandardPaths.HomeLocation))
        filepath, extension = (dialog.getSaveFileName(None, "Save QGIS-Style as QML", home_dir, "*.qml"))
        if filepath:
            layer.saveNamedStyle(filepath + ".qml")
            self.iface.messageBar().pushMessage(self.plugin_name, f"Saved style for layer '{layer.name()}'", level=Qgis.Success, duration=3)
        
    def copyExtent(self):
        """Copy extent from extent widget to clipboard
        """
        
        ouputBbox = ""
        
        # WKT
        # print(self.extentWidget.outputExtent().asWktCoordinates())
        # TODO: Select Bbox typ
        
        # minx, miny, maxx, maxy
        ouputBbox = str(round(self.extentWidget.outputExtent().xMinimum(), 4)) + ", " + \
            str(round(self.extentWidget.outputExtent().yMinimum(), 4)) + ", " + \
            str(round(self.extentWidget.outputExtent().xMaximum(), 4)) + ", " + \
            str(round(self.extentWidget.outputExtent().yMaximum(), 4))   
        
        clipboard = QApplication.clipboard()
        clipboard.setText(ouputBbox)   
        
        self.iface.messageBar().pushMessage(self.plugin_name, "Copied extent to clipboard", level=Qgis.Success, duration=3)    
        