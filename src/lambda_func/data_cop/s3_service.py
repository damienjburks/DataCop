"""
Module for calling S3 APIs.
"""
import json

import botocore.exceptions
from botocore.exceptions import ClientError
from data_cop.logging_config import LoggerConfig

DENY_ALL_POLICY = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "DenyAllPolicy",
            "Effect": "Deny",
            "Principal": "*",
            "Action": ["s3:*"],
            "Resource": ["arn:aws:s3:::bucket_name", "arn:aws:s3:::bucket_name/*"],
            "Condition": {
                "StringNotLike": {
                    "aws:PrincipalARN": [
                        "arn:aws:iam::*:user/DataKnight",
                        "arn:aws:iam::*:role/DataKnight",
                        "arn:aws:iam::*:root",
                    ]
                }
            },
        }
    ],
}


class S3Service:
    """
    This class is responsible for interacting with AWS S3 APIs.
    """

    def __init__(self, boto_session):
        self.s3_client = boto_session.client("s3")
        self.s3_resource = boto_session.resource("s3")
        self.logger = LoggerConfig().configure(type(self).__name__)

    def download_file(self, s3_key, s3_bucket_name, file_name):
        """
        Downloads file from S3
        """
        try:
            self.logger.debug("Downloading S3 key: %s", s3_key)
            self.s3_resource.Bucket(s3_bucket_name).download_file(s3_key, file_name)
            self.logger.debug("Downloaded S3 file, %s, successfully!", file_name)
        except ClientError as c_err:
            if c_err.response["Error"]["Code"] == "404":
                print("This object doesn't exist. Please advise.")
            else:
                raise c_err

        return file_name

    def restrict_access_to_bucket(self, bucket_name):
        """
        Attaches DENY ALL Policy to the S3 bucket
        """
        self.logger.debug("Restricting access to this bucket: %s", bucket_name)

        bucket_policy = json.dumps(DENY_ALL_POLICY).replace("bucket_name", bucket_name)
        try:
            response = self.s3_client.put_bucket_policy(
                Bucket=bucket_name,
                ConfirmRemoveSelfBucketAccess=True,
                Policy=bucket_policy,
            )
            self.logger.debug(
                "Attached the deny all policy to S3 bucket: %s", bucket_name
            )
            self.logger.debug(response)
        except botocore.exceptions.ClientError as err:
            self.logger.warning("Unable to attach deny all bucket policy: %s", str(err))

    def block_public_access(self, bucket_name):
        """
        Blocks all public access to the s3 bucket
        """
        self.logger.debug("Blocking public access to bucket: %s", bucket_name)
        response = self.s3_client.put_public_access_block(
            Bucket=bucket_name,
            PublicAccessBlockConfiguration={
                "BlockPublicAcls": True,
                "IgnorePublicAcls": True,
                "BlockPublicPolicy": True,
                "RestrictPublicBuckets": True,
            },
        )
        self.logger.debug("Blocked public access to bucket: %s", bucket_name)
        self.logger.debug(response)

        return response

    def put_private_acl(self, bucket_name):
        """
        Attaches private ACL to S3 bucket
        """
        self.logger.debug("Attaching private ACL to bucket: %s", bucket_name)
        response = self.s3_client.put_bucket_acl(
            ACL="private",
            Bucket=bucket_name,
        )
        self.logger.debug("Attached private ACL to bucket: %s", bucket_name)
        self.logger.debug(response)

        return response
