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
                        "arn:aws:iam::*:user/DataCop",
                        "arn:aws:iam::*:role/DataCop*",
                        "arn:aws:iam::*:root",
                    ]
                }
            },
        }
    ],
}

S3_OBJECTS = []
DENY_OBJECTS_POLICY = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "DenyAllObjectsPolicy",
            "Effect": "Deny",
            "Principal": "*",
            "Action": ["s3:*"],
            "Resource": S3_OBJECTS,
            "Condition": {
                "StringNotLike": {
                    "aws:PrincipalARN": [
                        "arn:aws:iam::*:user/DataCop",
                        "arn:aws:iam::*:role/DataCop*",
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

    def compare_bucket_policy(self, s3_bucket_name):
        """
        This function compares the existing bucket policy against the
        default DENYALL policy
        """
        try:
            bucket_policy = self.s3_client.get_bucket_policy(Bucket=s3_bucket_name)[
                "Policy"
            ]
            deny_all_policy_json = json.dumps(DENY_ALL_POLICY).replace(
                "bucket_name", s3_bucket_name
            )
            return bool(bucket_policy == deny_all_policy_json)
        except ClientError as err:
            if "NoSuchBucketPolicy" in str(err):
                return False
            return True

    def is_public_access_blocked(self, s3_bucket_name):
        """
        Checks to see if public access has been blocked
        for an S3 bucket.
        """
        pub_access_block = self.s3_client.get_public_access_block(
            Bucket=s3_bucket_name,
        )["PublicAccessBlockConfiguration"]

        if "false" in str(pub_access_block).lower():
            return False
        return True

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

    def copy_object_to_bucket(
        self,
        original_object_key,
        target_object_key,
        original_bucket_name,
        target_bucket_name,
    ):
        """
        Copies an S3 bucket from one bucket to the target bucket.
        """
        copy_source = {"Bucket": original_bucket_name, "Key": original_object_key}
        target_bucket_res = self.s3_resource.Bucket(target_bucket_name)
        target_obj = target_bucket_res.Object(target_object_key)
        target_obj.copy(copy_source)
        self.logger.info("Object has been copied successfully!")

        return {"targetBucketName": target_bucket_name, "fileName": target_object_key}

    def delete_object_from_bucket(self, object_key, bucket_name):
        """
        Deletes the object from the s3 bucket
        """
        delete_response = self.s3_client.delete_object(
            Bucket=bucket_name,
            Key=object_key,
        )

        self.logger.info(
            "Deleted the following object from the %s S3 bucket: %s",
            object_key,
            bucket_name,
        )
        return delete_response
