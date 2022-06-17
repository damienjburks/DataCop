import gzip
import json

from logging_config import LoggerConfig


class FileParser:

    def __init__(self):
        self.logger = LoggerConfig().configure_logger(type(self).__name__)

    def decompress(self, file_path):
        json_data = None
        self.logger.debug("Decompressing file and getting JSON file: %s", file_path)
        with gzip.open(file_path, 'rb') as json_file:
            json_data = json_file.read().decode()
        self.logger.debug("Printing JSON data from file: %s", json_data)
        return json_data


class StringParser:

    def __init__(self):
        self.logger = LoggerConfig().configure_logger(type(self).__name__)

    def transform_json(self, json_str):
        transformed_json = json.loads(json_str)
        return transformed_json

    def parse_findings(self, findings_dict):
        # Take the dictionary and grab the criticality
        self.logger.debug("Grabbing necessary information and parsing JSON: %s", findings_dict)
        s3_bucket_arn = findings_dict["resourcesAffected"]["s3Bucket"]["arn"]
        s3_object_path = findings_dict["resourcesAffected"]["s3Object"]["path"]
        severity = findings_dict["severity"]["description"]

        return {
            "bucket_arn": s3_bucket_arn,
            "object_path": s3_object_path,
            "severity": severity
        }
