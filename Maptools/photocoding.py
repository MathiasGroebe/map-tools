from re import L
from typing import Any, Optional

from exif import Image
from datetime import datetime
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
    QgsProcessingParameterFile
)
from qgis import processing
import itertools
import math
import os
import shutil
from qgis.core import QgsProcessingParameterNumber

class PhotoCodingAlgorithm(QgsProcessingAlgorithm):
    """
    Kodierung von Photos andhand eines Zeitstempels
    """

    # Constants used to refer to parameters and outputs. 

    POINTS = "POINTS"
    POINTS_TIMESTAMP = "POINTS_TIMESTAMP"
    OFFSET = "OFFSET"
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

        return "Correlation of photos by timestamp."

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
        
       
    def decimal_to_dms(self, value, is_latitude=True):
        degrees = int(abs(value))
        minutes_float = (abs(value) - degrees) * 60
        minutes = int(minutes_float)
        seconds = round((minutes_float - minutes) * 60, 2)
        direction = ''
        if is_latitude:
            direction = 'N' if value >= 0 else 'S'
        else:
            direction = 'E' if value >= 0 else 'W'
        return degrees, minutes, seconds, direction       

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
        folder_in = self.parameterAsString(parameters, self.FOLDER_IN, context)
        folder_out = self.parameterAsString(parameters, self.FOLDER_OUT, context)

        # Apply selection
        points = points.materialize(QgsFeatureRequest(), feedback)

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
                a_image = Image(image.read())
                taken = QDateTime.fromString(a_image.datetime_original, "yyyy:MM:dd HH:mm:ss")

                images_processed += 1

                # Request feature by time
                exp = f"epoch({points_timestamp_field}) = {taken.toSecsSinceEpoch() * 1000} + {offset * 1000}"
                request = QgsFeatureRequest().setFilterExpression(exp)
                for matching_feature in points.getFeatures(request):
                    feedback.pushInfo(f"Match {file} with point {matching_feature.id()} at {taken.toString(Qt.DateFormat.DefaultLocaleLongDate)} ")
                    point = matching_feature.geometry().asPoint()

                    src_path = os.path.join(folder_in, file)
                    dst_path = os.path.join(folder_out, file)
                    shutil.copy2(src_path, dst_path)

                    with open(dst_path, "rb") as out_image_file:
                        out_image = Image(out_image_file.read())

                    # Set GPS EXIF data
                    lat_deg, lat_min, lat_sec, lat_ref = self.decimal_to_dms(point.y(), is_latitude=True)
                    lon_deg, lon_min, lon_sec, lon_ref = self.decimal_to_dms(point.x(), is_latitude=False)

                    out_image.gps_latitude = (lat_deg, lat_min, lat_sec)
                    out_image.gps_latitude_ref = lat_ref
                    out_image.gps_longitude = (lon_deg, lon_min, lon_sec)
                    out_image.gps_longitude_ref = lon_ref

                    # Write updated EXIF back to file
                    with open(dst_path, "wb") as updated_image_file:
                        updated_image_file.write(out_image.get_file())

                    images_referenced += 1


            feedback.setProgress(int(current * total))


        feedback.pushInfo(f"Images processed: {images_processed}")
        feedback.pushInfo(f"Images referenced: {images_referenced}")


        return {self.FOLDER_OUT: folder_out}

    def createInstance(self):
        return self.__class__()