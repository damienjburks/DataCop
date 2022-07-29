"""
Module for defining Lambda handler.
"""
from data_cop.session_config import BotoConfig
from data_cop.ssm_service import SSMService
from data_cop.s3_service import S3Service
from data_cop.parser_ import FileParser, MacieLogParser


def lambda_handler(event, _context):
    """
    Handler that contains core logic for blocking S3 buckets
    and parsing Macie results
    :param event:
    :param _context:
    :return:
    """

    boto_session = BotoConfig().get_session()

    if event["state_name"] == "determine_severity":
        state_response = state_determine_severity(event, boto_session)
    if event["state_name"] == "block_s3_bucket":
        state_response = state_block_s3_bucket(event, boto_session)

    return state_response


def state_determine_severity(event, boto_session):
    """
    Contains logic for the determine_severity state in the
    step function
    """
    ssm_svc = SSMService(boto_session)
    severity = ssm_svc.get_severity()
    s3_obj_key = event["Payload"]["detail"]["requestParameters"]["key"]
    s3_bucket_name = event["Payload"]["detail"]["requestParameters"]["bucketName"]

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
            if vetted_findings["severity"].lower() == severity:
                break

    return vetted_findings


def state_block_s3_bucket(event, boto_session):
    """
    Contains logic for the block_s3_bucket state in the
    step function
    """
    # Start the block public access to the bucket
    s3_service = S3Service(boto_session)
    bucket_name = event["report"]["bucket_name"]
    s3_service.block_public_access(bucket_name)
    s3_service.restrict_access_to_bucket(bucket_name)

    return {"bucket_name": bucket_name, "is_blocked": True}
