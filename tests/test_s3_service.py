"""
Module for testing S3 service
"""
import boto3
from moto import mock_s3
from src.lambda_func.data_cop.s3_service import S3Service


@mock_s3
def test_restrict_access_to_bucket(aws_credentials):
    mock_session = create_mock_session(aws_credentials)
    mock_s3_class = S3Service(mock_session)
    bucket_name = "test_bucket"
    bucket_response = create_bucket(bucket_name)
    assert bucket_response is not None

    mock_s3_class.restrict_access_to_bucket(bucket_name)


@mock_s3
def test_block_public_access(aws_credentials):
    mock_session = create_mock_session(aws_credentials)
    mock_s3_class = S3Service(mock_session)
    bucket_name = "test_bucket"
    bucket_response = create_bucket(bucket_name)
    assert bucket_response is not None

    response = mock_s3_class.block_public_access(bucket_name)
    assert response is not None


@mock_s3
def test_put_private_acl(aws_credentials):
    mock_session = create_mock_session(aws_credentials)
    mock_s3_class = S3Service(mock_session)
    bucket_name = "test_bucket"
    bucket_response = create_bucket(bucket_name)
    assert bucket_response is not None

    response = mock_s3_class.put_private_acl(bucket_name)
    assert response is not None


@mock_s3
def test_download_file(aws_credentials):
    mock_session = create_mock_session(aws_credentials)
    mock_s3_class = S3Service(mock_session)
    mock_bucket_name = "test_bucket_1011"
    mock_file_name = "test.pdf"

    upload_file_response = upload_file(mock_bucket_name, mock_file_name)
    assert upload_file_response is not None

    mock_file_name = mock_s3_class.download_file(
        mock_file_name, mock_bucket_name, mock_file_name
    )
    assert mock_file_name == mock_file_name


def create_bucket(bucket_name):
    s3_client = boto3.client("s3")
    response = s3_client.create_bucket(Bucket=bucket_name)
    return response


def upload_file(bucket_name, file_name):
    s3_client = boto3.client("s3")
    s3_client.create_bucket(Bucket=bucket_name)
    response = s3_client.put_object(Bucket=bucket_name, Key=file_name)
    return response


def create_mock_session(aws_credentials):
    return boto3.Session()
