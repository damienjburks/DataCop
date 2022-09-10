"""
This is a standalone script that will check to see if Macie is configured or not.
This is supposed to be executed prior to deployment.
"""
import sys
import time
import os
import shutil

from lambda_func.data_cop.session_config import BotoConfig
from lambda_func.data_cop.logging_config import LoggerConfig


class MacieSetup:
    """
    Class for configuring Macie and S3 after the CFTs
    has been deployed.
    """

    def __init__(self):
        self.logger = LoggerConfig().configure(__name__)
        self.macie_client = BotoConfig().get_session().client("macie2")
        self.kms_client = BotoConfig().get_session().client("kms")
        self.s3_client = BotoConfig().get_session().client("s3")

    def configure_classification_report(self):
        """
        Configures the classification report S3 bucket for Macie
        :return:
        """
        s3_bucket_name = os.environ["RESULT_S3_BUCKET_NAME"]
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
                    "keyPrefix": "macie-files",
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
            Bucket=os.environ["RESULT_S3_BUCKET_NAME"],
            PublicAccessBlockConfiguration={
                "BlockPublicAcls": True,
                "IgnorePublicAcls": True,
                "BlockPublicPolicy": True,
                "RestrictPublicBuckets": True,
            },
        )
        self.logger.info(
            "Blocked public access to bucket: %s", os.environ["RESULT_S3_BUCKET_NAME"]
        )


def predeploy():
    """
    Function to execute pre-deployment steps
    :return:
    """
    macie = MacieSetup()
    macie.enable_macie()


def postdeploy():
    """
    Function to execute post-deployment steps
    :return:
    """
    macie = MacieSetup()
    macie.configure_s3_bucket()
    macie.configure_classification_report()


def postdestroy():
    """
    Function that disables macie after
    infrastructure has been destroyed.
    :return:
    """
    macie = MacieSetup()
    macie.disable_macie()


if __name__ == "__main__":
    if "true" in sys.argv:
        postdestroy()
    else:
        predeploy()
        postdeploy()
