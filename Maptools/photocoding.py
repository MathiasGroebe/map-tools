# -*- coding: utf-8 -*-

from typing import Any, Optional
import os
import shutil
from PyQt5.QtCore import QDateTime, Qt
from qgis.core import (

    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingContext,
    QgsProcessingFeedback,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterField,
    QgsFeatureRequest,
    QgsProcessingParameterFolderDestination,
    QgsProcessingParameterFile,
    QgsCoordinateTransform,
    QgsCoordinateReferenceSystem,
    QgsExifTools,
    QgsProcessingParameterNumber
)

class PhotoCodingAlgorithm(QgsProcessingAlgorithm):
    """
    Correlation of photos by timestamp.
    """

    # Constants used to refer to parameters and outputs. 

    POINTS = "POINTS"
    POINTS_TIMESTAMP = "POINTS_TIMESTAMP"
    OFFSET = "OFFSET"
    ELEVATION_OFFSET = "ELEVATION_OFFSET"
    FOLDER_IN = "FOLDER_IN"
    FOLDER_OUT = "FOLDER_OUT"

    def name(self) -> str:
        """
        Returns the algorithm name, used for identifying the algorithm. 
        """
        return "photocoding"

    def displayName(self) -> str:
        """
        Returns the translated algorithm name, which should be used for any
        user-visible display of the algorithm name.
        """
        return "Correlation of photos"

    def group(self) -> str:
        """
        Returns the name of the group this algorithm belongs to. This string
        should be localised.
        """
        return "Geocoding"

    def groupId(self) -> str:
        """
        Returns the unique ID of the group this algorithm belongs to. 
        """
        return "geocoding"

    def shortHelpString(self):

        file = os.path.join(os.path.dirname(__file__), "help_files", "photocoding.html")
        print(file)
        if not os.path.exists(file):
            return "Correlation of photos by timestamp."
        with open(file) as helpfile:
            help = helpfile.read()
        return help  


    def initAlgorithm(self, config: Optional[dict[str, Any]] = None):
        """
        Here we define the inputs and output of the algorithm, along
        with some other properties.
        """

        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.POINTS,
                "Points with timestamp",
                [QgsProcessing.TypeVectorPoint],
            )
        )
        
        self.addParameter(
            QgsProcessingParameterField(
            self.POINTS_TIMESTAMP,
            "Timestamp field",
            parentLayerParameterName=self.POINTS,
            type=QgsProcessingParameterField.DateTime
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                "OFFSET",
                "Offset in seconds",
                type=QgsProcessingParameterNumber.Integer,
                defaultValue=0
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                "ELEVATION_OFFSET",
                "Elevation offset in meters",
                type=QgsProcessingParameterNumber.Double,
                defaultValue=0
            )
        )

        self.addParameter(
            QgsProcessingParameterFile(
                self.FOLDER_IN,
                "Input folder with photos",
                behavior=QgsProcessingParameterFile.Folder
            )
        )

        self.addParameter(
            QgsProcessingParameterFolderDestination(
                self.FOLDER_OUT,
                "Output folder for photos"
            )
        )    

    def processAlgorithm(
        self,
        parameters: dict[str, Any],
        context: QgsProcessingContext,
        feedback: QgsProcessingFeedback,
    ) -> dict[str, Any]:
        """
        Here is where the processing itself takes place.
        """

        # Retrieve the feature source and sink.

        points = self.parameterAsSource(parameters, self.POINTS, context)
        points_timestamp_field = self.parameterAsString(parameters, self.POINTS_TIMESTAMP, context)
        offset = self.parameterAsInt(parameters, self.OFFSET, context)
        elevation_offset = self.parameterAsDouble(parameters, self.ELEVATION_OFFSET, context)
        folder_in = self.parameterAsString(parameters, self.FOLDER_IN, context)
        folder_out = self.parameterAsString(parameters, self.FOLDER_OUT, context)

        # Apply selection
        points = points.materialize(QgsFeatureRequest(), feedback)

        # Get the CRS of the points layer
        points_crs = points.sourceCrs()

        images_processed = 0
        images_referenced = 0

        # If the folder does not exist, create it
        if not os.path.exists(folder_out):
            os.makedirs(folder_out)

        files = os.listdir(folder_in)
        file_count = len(files)


        # Compute the number of steps to display within the progress bar and
        
        total = 100.0 / file_count if file_count else 0


        for current, file in enumerate(files):
            
            if not os.path.isfile(os.path.join(folder_in, file)):
                continue
            if not file.lower().endswith((".jpg", ".jpeg")):
                continue

            with open(os.path.join(folder_in, file) , "rb") as image:

                taken = QgsExifTools().readTag(os.path.join(folder_in, file), "Exif.Image.DateTime")

                images_processed += 1

                # Request feature by time
                exp = f"epoch({points_timestamp_field}) = {taken.toSecsSinceEpoch() * 1000} + {offset * 1000}"
                request = QgsFeatureRequest().setFilterExpression(exp)
                for matching_feature in points.getFeatures(request):
                    feedback.pushInfo(f"Match {file} with point {matching_feature.id()} at {taken.toString(Qt.DateFormat.DefaultLocaleLongDate)} ")
                    
                    # Check if the point is in WGS84
                    if points_crs == QgsCoordinateReferenceSystem("EPSG:4326"):
                        point = matching_feature.geometry().asPoint()
                        
                    else:
                        dest_crs = QgsCoordinateReferenceSystem("EPSG:4326")
                        transform = QgsCoordinateTransform(points_crs, dest_crs, context.transformContext())
                        geom = matching_feature.geometry()
                        geom.transform(transform)
                        point = geom.asPoint()

                    src_path = os.path.join(folder_in, file)
                    dst_path = os.path.join(folder_out, file)
                    shutil.copy2(src_path, dst_path)

                    # Write coordinates to the image
                    QgsExifTools().geoTagImage(os.path.join(folder_out, file), point)

                    # If Z coordinate is available, set altitude
                    if matching_feature.geometry().constGet().is3D():
                        altitude = matching_feature.geometry().constGet().z() + elevation_offset
                        QgsExifTools().tagImage(os.path.join(folder_out, file), "Exif.GPSInfo.GPSAltitude", altitude)

                    images_referenced += 1


            feedback.setProgress(int(current * total))


        feedback.pushInfo(f"Images processed: {images_processed}")
        feedback.pushInfo(f"Images referenced: {images_referenced}")


        return {self.FOLDER_OUT: folder_out}

    def createInstance(self):
        return self.__class__()