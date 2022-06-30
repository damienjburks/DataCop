'''
This is a standalone script that will check to see if Macie is configured or not.
This is supposed to be executed prior to deployment.
'''
import time
import os

from data_cop.session_config import BotoConfig
from data_cop.logging_config import LoggerConfig


class MacieSetup:
    """
    Class for configuring Macie
    """

    def __init__(self):
        self.logger = LoggerConfig().configure(__name__)
        self.macie_client = BotoConfig().get_session().client("macie2")

    def configure_classification_report(self):
        s3_bucket_name = os.environ['S3_BUCKET_NAME']
        self.logger.info("Configuring classification report: %s", s3_bucket_name)
        response = self.macie_client.put_classification_export_configuration(
            configuration={
                's3Destination': {
                    'bucketName': s3_bucket_name,
                    'keyPrefix': '/',
                    'kmsKeyArn': 'arn:aws:kms:us-east-1:976556613810:key/08a9a7dc-d0f8-495b-b5df-19de3591292b', # TODO: Change this to an actual KMS key
                }
            }
        )
        self.logger.info("Configured classification report.")
        self.logger.debug(response)

    def enable_macie(self):
        enabled = self.check_macie_status()
        if not enabled:
            self.logger.info("Macie is not enabled. Enabling now...")
            self.macie_client.enable_macie(
                status='ENABLED'
            )
            time.sleep(10)  # Wait 10 seconds

            # Checking to see if it's enabled
            enabled = self.check_macie_status()
            if not enabled:
                raise Exception("Macie is not enabled. Please enable it manually before continuing with deployment.")
        else:
            self.logger.info("Macie is already enabled!")

    def check_macie_status(self):
        is_enabled = True

        try:
            self.macie_client.get_macie_session()
        except self.macie_client.exceptions.AccessDeniedException:
            is_enabled = False

        return is_enabled

    def disable_macie(self):
        self.macie_client.disable_macie()
        self.logger.info("Macie has been disabled for this account.")

def predeploy():
    macie = MacieSetup()
    macie.enable_macie()

def postdeploy():
    macie = MacieSetup()
    macie.configure_classification_report()

if __name__ == '__main__':
    predeploy()
    postdeploy()
