"""
Module with parsing classes (File/String/Macie)
"""

import gzip
import json

from src.lambda_func.data_cop.logging_config import LoggerConfig


class FileParser:
    """
    This class is responsible for all IO operations with files.
    """

    def __init__(self):
        self.logger = LoggerConfig().configure(type(self).__name__)

    def decompress(self, file_path):
        """
        Functions that unzips the file from macie and reads
        the data.
        """
        self.logger.debug("Decompressing file and getting JSON file: %s", file_path)
        with gzip.open(file_path, "rb") as json_file:
            json_data = json_file.read().decode()
        self.logger.debug("Printing JSON data from file: %s", json_data)
        return json_data


class MacieLogParser:
    """
    This class is responsible for all string operations with Macie logs.
    """

    def __init__(self):
        self.logger = LoggerConfig().configure(type(self).__name__)

    def transform_json(self, json_str):
        """
        This function transforms the JSON string
        """
        transformed_json = json.loads(json_str)
        return transformed_json

    def parse_findings(self, findings_dict):
        """
        This function parses the findings and returns
        the json object of the buckets that are flagged.
        """
        # Take the dictionary and grab the criticality
        self.logger.debug(
            "Grabbing necessary information and parsing JSON: %s", findings_dict
        )
        s3_bucket_name = findings_dict["resourcesAffected"]["s3Bucket"]["name"]
        s3_bucket_arn = findings_dict["resourcesAffected"]["s3Bucket"]["arn"]
        s3_object_path = findings_dict["resourcesAffected"]["s3Object"]["path"]
        severity = findings_dict["severity"]["description"]

        return {
            "bucket_name": s3_bucket_name,
            "bucket_arn": s3_bucket_arn,
            "object_path": s3_object_path,
            "severity": severity,
        }
