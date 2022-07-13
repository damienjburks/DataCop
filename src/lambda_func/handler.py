"""
Module for defining Lambda handler.
"""
import json

from data_cop.s3_service import S3Service
from data_cop.session_config import BotoConfig
from data_cop.parser_ import FileParser, MacieLogParser

CONFIG_FILE_PATH = "./.config.json"


def lambda_handler(event, _context):
    """
    Handler that contains core logic for blocking S3 buckets
    and parsing Macie results
    :param event:
    :param _context:
    :return:
    """
    boto_session = BotoConfig().get_session()
    config = load_config_file()

    if event["Records"][0]["eventName"] == "ObjectCreated:Put":
        s3_obj_key = event["Records"][0]["s3"]["object"]["key"]
        s3_bucket_name = event["Records"][0]["s3"]["bucket"]["name"]
        if "jsonl.gz" in s3_obj_key:
            file_name = s3_obj_key.split("/")[-1]

            # Downloading file
            lambda_file_path = "/tmp/" + file_name
            s3_service = S3Service(boto_session)
            s3_service.download_file(s3_obj_key, s3_bucket_name, lambda_file_path)

            # Grabbing the json content
            file_util_obj = FileParser()
            data_list = file_util_obj.decompress(lambda_file_path)

            # Parsing JSON
            string_parser = MacieLogParser()
            for data in data_list:
                findings_dict = string_parser.transform_json(data)
                vetted_findings = string_parser.parse_findings(findings_dict)

                # Start denying services
                if vetted_findings["severity"].lower() == config["severity"]:
                    # Start the block public access to the bucket
                    bucket_name = vetted_findings["bucket_name"]
                    s3_service.block_public_access(bucket_name)
                    s3_service.restrict_access_to_bucket(bucket_name)
                    break

    return event


def load_config_file():
    """Loads the config file"""
    with open(CONFIG_FILE_PATH, "rb") as f:
        config_file = f.read().decode()
        conf_json = json.load(config_file)

    return conf_json
