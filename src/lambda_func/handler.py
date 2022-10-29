"""
Module for defining Lambda handler.
"""
import json

from data_cop.session_config import BotoConfig
from data_cop.ssm_service import SSMService
from data_cop.s3_service import S3Service
from data_cop.sns_service import SnsService
from data_cop.sfn_service import SfnService
from data_cop.parser_ import FileParser, MacieLogParser, EventParser
from data_cop.enums_ import DataCopEnum


def lambda_handler(event, _context):
    """
    Handler that contains core logic for blocking S3 buckets
    and parsing Macie results
    :param event:
    :param context:
    :return:
    """

    boto_session = BotoConfig().get_session()
    state_response = None

    if "state_name" not in event:  # It's coming from SNS
        _enum = EventParser(event).determine_type()

        # DataCop FSS Step Function States
        if _enum == DataCopEnum.FSS:
            # Execute the step function
            sfn_payload = EventParser(event).create_sfn_payload(_enum)
            sfn_obj = SfnService(boto_session)
            sfn_obj.execute_sfn(sfn_payload, _enum)

    if event["state_name"] == "check_bucket_status":
        state_response = state_check_bucket_status(event, boto_session)
    if event["state_name"] == "block_s3_bucket":
        state_response = state_block_s3_bucket(event, boto_session)
    if event["state_name"] == "copy_object_to_quarantine_bucket":
        state_response = state_copy_object_to_quarantine_bucket(event, boto_session)
    if event["state_name"] == "remove_object_from_parent_bucket":
        state_response = state_remove_object_from_parent_bucket(event, boto_session)
    if event["state_name"] == "send_report":
        state_response = state_send_report(event, boto_session)
    if event["state_name"] == "send_error_report":
        state_response = state_send_error_report(event, boto_session)
    if event["state_name"] == "determine_severity":
        state_response = state_determine_severity(event, boto_session)

    return state_response


def state_copy_object_to_quarantine_bucket(event, boto_session):
    """
    Contains logic for copy_object_to_quarantine_bucket
    in the step function
    """
    s3_svc = S3Service(boto_session)
    ssm_service = SSMService(boto_session)

    # Parse the event and pull out the bucket name
    # and get the target bucket name
    original_bucket_name = event["report"]["bucket_name"]
    original_object_key_path = event["report"]["object_path"]
    target_object_key_path = f"{original_bucket_name}/{event['report']['object_key']}"
    target_bucket_name = ssm_service.get_quarantine_bucket_name()

    # Copy object from original bucket to quarantine
    s3_svc.copy_object_to_bucket(
        original_object_key_path,
        target_object_key_path,
        original_bucket_name,
        target_bucket_name,
    )

    return {
        "original_bucket_name": original_bucket_name,
        "target_bucket_name": target_bucket_name,
        "target_bucket_path": target_object_key_path,
    }


def state_remove_object_from_parent_bucket(event, boto_session):
    """
    Contains logic for remove_object_from_parent_bucket
    in the step function
    """
    s3_svc = S3Service(boto_session)

    original_bucket_name = event["report"]["bucket_name"]
    original_object_key_path = event["report"]["object_path"]

    s3_svc.delete_object_from_bucket(original_object_key_path, original_bucket_name)

    return {
        "original_bucket_name": original_bucket_name,
        "deleted_object_key": original_object_key_path,
    }


def state_determine_severity(event, boto_session):
    """
    Contains logic for the determine_severity state in the
    step function
    """
    ssm_svc = SSMService(boto_session)
    severity = ssm_svc.get_severity()
    s3_obj_key = event["Payload"]["detail"]["requestParameters"]["key"]
    s3_bucket_name = event["Payload"]["detail"]["requestParameters"]["bucketName"]
    vetted_findings = None

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


def state_check_bucket_status(event, boto_session):
    """
    Checks the status of the S3 bucket. If it has been blocked,
    it will return true, otherwise, false.
    """
    s3_service = S3Service(boto_session)
    bucket_name = event["report"]["bucket_name"]
    is_denied = s3_service.compare_bucket_policy(bucket_name)
    is_not_public = s3_service.is_public_access_blocked(bucket_name)

    is_blocked = is_denied and is_not_public
    return {"is_blocked": str(is_blocked), "bucket_name": bucket_name}


def state_block_s3_bucket(event, boto_session):
    """
    Blocks the S3 bucket by restricting all access
    to the bucket
    """
    # Start the block public access to the bucket
    s3_service = S3Service(boto_session)
    bucket_name = event["report"]["bucket_name"]
    s3_service.block_public_access(bucket_name)
    s3_service.restrict_access_to_bucket(bucket_name)

    return {"bucket_name": bucket_name, "is_blocked": True}


def state_send_report(event, boto_session):
    """
    Publishes a report to the SNS topic
    """
    sns_service = SnsService(boto_session)
    bucket_name = event["report"]["bucket_name"]
    execution_id = event["execution_id"].split(":")[-1]
    subject = "SUCCESS: DataCop S3 Blocking"
    message = (
        f"The following bucket(s) have been blocked: \n{bucket_name}!\n"
        f"Please revert to the step function logs associated with this execution id: {execution_id}"
    )
    message_id = sns_service.send_email(subject, message)
    return message_id


def state_send_error_report(event, boto_session):
    """
    Publishes the error report to the SNS topic
    """
    sns_service = SnsService(boto_session)
    cause = event["report"]["Cause"]
    error_message = json.loads(cause)["errorMessage"]
    execution_id = event["execution_id"].split(":")[-1]
    subject = "FAILURE: DataCop S3 Blocking"
    message = (
        f"We've experienced an error. Please revert to the step function "
        f"logs associated with this execution id: {execution_id}"
        f" \nThe exception output is highlighted below: \n{error_message} "
    )
    message_id = sns_service.send_email(subject, message)
    return message_id
