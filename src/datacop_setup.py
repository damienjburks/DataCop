"""
This is a standalone script that will check to see if Macie is configured or not.
This is supposed to be executed prior to deployment.
"""
import json
import sys
import time
import os
import shutil

from botocore.exceptions import ClientError
from lambda_func.data_cop.session_config import BotoConfig
from lambda_func.data_cop.logging_config import LoggerConfig


class DatacopSetup:
    """
    Class for configuring Macie and S3 after the CFTs
    has been deployed.
    """

    def __init__(self):
        self.logger = LoggerConfig().configure(__name__)
        self.macie_client = BotoConfig().get_session().client("macie2")
        self.kms_client = BotoConfig().get_session().client("kms")
        self.s3_client = BotoConfig().get_session().client("s3")
        self.ses_client = BotoConfig().get_session().client("ses")
        self.account_id = (
            BotoConfig()
            .get_session()
            .client("sts")
            .get_caller_identity()
            .get("Account")
        )

    def create_and_verify_email(self):
        """
        This function create and verify the main distro
        for sending emails to DataCop.
        :return:
        """
        try:
            ses_email_name = os.environ["SES_EMAIL"]
            ses_policy_name = f"DataCopSesPolicy{self.account_id}"
            ses_identity = (
                f"arn:aws:ses:us-east-1:{self.account_id}:identity/{ses_email_name}"
            )

            ses_policy = {
                "Version": "2008-10-17",
                "Statement": [
                    {
                        "Sid": "DataCopSesPolicy",
                        "Effect": "Allow",
                        "Principal": {"AWS": f"arn:aws:iam::{self.account_id}:root"},
                        "Action": ["ses:SendEmail", "ses:SendRawEmail"],
                        "Resource": ses_identity,
                    }
                ],
            }
            self.ses_client.put_identity_policy(
                Identity=ses_email_name,
                Policy=json.dumps(ses_policy),
                PolicyName="DataCopSesPolicy",
            )
            self.ses_client.verify_email_identity(EmailAddress=ses_email_name)

            return ses_policy_name, ses_identity

        except ClientError as err:
            self.logger.error("Cannot configure SES. Disabling moving forward.")
            self.logger.error("Printing exception now: %s", str(err))

        return None

    def configure_classification_report(self):
        """
        Configures the classification report S3 bucket for Macie
        :return:
        """
        s3_bucket_name = os.environ["S3_BUCKET_NAME"]
        kms_key_alias = os.environ["KMS_KEY_ALIAS"]
        self.logger.info("Configuring classification report: %s", s3_bucket_name)

        # Deriving KMS key
        kms_key_aliases = self.kms_client.list_aliases()["Aliases"]
        for alias in kms_key_aliases:
            if alias["AliasName"] == kms_key_alias:
                key_id = alias["TargetKeyId"]

        key_arn = self.kms_client.describe_key(KeyId=key_id)["KeyMetadata"]["Arn"]

        self.macie_client.put_classification_export_configuration(
            configuration={
                "s3Destination": {
                    "bucketName": s3_bucket_name,
                    "keyPrefix": "/",
                    "kmsKeyArn": key_arn,
                }
            }
        )
        self.logger.info("Configured classification report successfully!")

    def enable_macie(self):
        """
        Function that enables macie for an account
        :return:
        """
        enabled = self.check_macie_status()
        if not enabled:
            self.logger.info("Macie is not enabled. Enabling now...")
            self.macie_client.enable_macie(status="ENABLED")
            time.sleep(10)  # Wait 10 seconds

            # Checking to see if it's enabled
            enabled = self.check_macie_status()
            if not enabled:
                raise Exception(
                    """Macie is not enabled. Please enable it manually
                    before continuing with deployment."""
                )
        else:
            self.logger.info("Macie is already enabled!")

    def check_macie_status(self):
        """
        Checks the status of Macie. Whether it is enabled/disabled.
        :return:
        """
        is_enabled = True

        try:
            self.macie_client.get_macie_session()
        except self.macie_client.exceptions.AccessDeniedException:
            is_enabled = False

        return is_enabled

    def disable_macie(self):
        """
        Disables macie for an AWS account.
        :return:
        """
        self.macie_client.disable_macie()
        self.logger.info("Macie has been disabled for this account.")

    def create_config_json(self):
        """
        Creates the config json for the lambda
        """
        original_config_file = "config.json"
        dest_config_file = "./src/lambda_func/.config.json"
        shutil.copyfile(original_config_file, dest_config_file)
        self.logger.info("Copied config.json into lambda function folder")

    def configure_s3_bucket(self):
        """
        Configures the S3 bucket by blocking public access.
        :return:
        """
        self.s3_client.put_public_access_block(
            Bucket=os.environ["S3_BUCKET_NAME"],
            PublicAccessBlockConfiguration={
                "BlockPublicAcls": True,
                "IgnorePublicAcls": True,
                "BlockPublicPolicy": True,
                "RestrictPublicBuckets": True,
            },
        )
        self.logger.info(
            "Blocked public access to bucket: %s", os.environ["S3_BUCKET_NAME"]
        )


def predeploy():
    """
    Function to execute pre-deployment steps
    :return:
    """
    macie = DatacopSetup()
    macie.enable_macie()
    macie.create_config_json()
    macie.create_and_verify_email()


def postdeploy():
    """
    Function to execute post-deployment steps
    :return:
    """
    setup = DatacopSetup()
    setup.configure_s3_bucket()
    setup.configure_classification_report()


def postdestroy():
    """
    Function that disables macie after
    infrastructure has been destroyed.
    :return:
    """
    setup = DatacopSetup()
    setup.disable_macie()


if __name__ == "__main__":
    if "true" in sys.argv:
        postdestroy()
    else:
        predeploy()
        postdeploy()
