"""
Module with parsing classes (File/String/Macie)
"""

import gzip
import json
import re
import ast

from urllib.parse import urlparse
from data_cop.logging_config import LoggerConfig
from data_cop.enums_ import DataCopEnum


class EventParser:
    """
    This class is responsible for parsing the event and
    figuring out what state machine it should be sent to, if applicable.
    """

    def __init__(self, event):
        self.logger = LoggerConfig().configure(type(self).__name__)
        self.event = event

    def transform_event(self):
        """Transforms the event into a dictionary"""
        return ast.literal_eval(str(self.event))

    def determine_type(self):
        """Function that determines the type of event"""
        event_records = self.transform_event()

        try:
            for record in event_records["Records"]:  # Should only be one :)
                topic_arn = record["Sns"]["TopicArn"]
                if "FileStorageSecurity" in topic_arn:
                    return DataCopEnum.FSS
        except KeyError:
            self.logger.info("Ignoring key error - most likely not an SNS event.")

        return DataCopEnum.MACIE

    def create_sfn_payload(self, message_type):
        """
        Function that determines the message type,
        parses message accordingly, and creates sfn payload.
        """
        event_records = self.transform_event()

        if message_type == DataCopEnum.FSS:
            message = event_records["Records"][0]["Sns"]["Message"]
            message_json = json.loads(message)

            url_segments = urlparse(message_json["file_url"])

            bucket_url_regex = "(.*).s3.amazonaws.com"
            pattern = re.compile(bucket_url_regex)
            matches = re.match(pattern, url_segments.netloc)
            bucket_name = matches.groups()[0]

            object_name = url_segments.path.split("/")[-1]

            return {
                "bucket_name": bucket_name,
                "object_key": object_name,
                "object_path": url_segments.path,
            }


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
        json_file_contents = []
        with gzip.open(file_path, "rb") as json_file:
            data = json_file.readline().decode()
            json_file_contents.append(data)
        self.logger.debug("Printing JSON data list: %s", json_file_contents)
        return json_file_contents


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


class FileStorageParser:
    """
    This class is responsible for parsing the results from the Trend Micro's
    File Storage Parser.
    """

    def __init__(self, event):
        self.logger = LoggerConfig().configure(type(self).__name__)
        self.event = event

    def parse_results(self):
        """
        Parsing the results that is sent from the SNS topic
        that contains the report from File Storage.
        """
        pass
