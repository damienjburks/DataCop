"""
Module for defining Lambda handler.
"""
from s3_service import S3Service
from session_config import BotoConfig
from parser_ import FileParser, MacieLogParser


def lambda_handler(event, _context):
    """
    Handler that contains core logic for blocking S3 buckets
    and parsing Macie results
    :param event:
    :param _context:
    :return:
    """
    boto_session = BotoConfig().get_session()
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
            json_contents = file_util_obj.decompress(lambda_file_path)

            # Parsing JSON
            string_parser = MacieLogParser()
            findings_dict = string_parser.transform_json(json_contents)
            vetted_findings = string_parser.parse_findings(findings_dict)

            # Start denying services for everything
            if vetted_findings["severity"].lower() == "high":
                # Start the block public access to the bucket
                bucket_name = vetted_findings["bucket_name"]
                s3_service.block_public_access(bucket_name)
                s3_service.restrict_access_to_bucket(bucket_name)

    return event
