"""
Module that is responsible for sending an email
with information about the S3 bucket that is contained.
"""

from data_cop.logging_config import LoggerConfig


class EmailService:
    # pylint: disable=line-too-long
    """
    Class that contains logic for sending emails using
    SES.
    """

    def __init__(self, boto_session):
        self.logger = LoggerConfig().configure(type(self).__name__)
        self.ses_client = boto_session.client("ses")

    def send_email(self, to_email_address, s3_buckets):
        """
        Sends an email to the supplied email address
        that solidifies how many s3 buckets have been blocked.
        """
        self.logger.info("Sending email to end-user")
        response = self.ses_client.send_email(
            Destination={
                "ToAddresses": [
                    to_email_address,
                ],
            },
            Message={
                "Body": {
                    "Html": {
                        "Charset": "UTF-8",
                        "Data": f"The following S3 buckets has been blocked: {s3_buckets}. Please log into the "
                        f"console and inspect the logs for more information.",
                    },
                },
                "Subject": {
                    "Charset": "UTF-8",
                    "Data": f"AWS DataCop Report: {len(s3_buckets)} buckets blocked",
                },
            },
            Source="dburksgtr@gmail.com",
        )
        self.logger.info("Sent the message successfully: %s", response["MessageId"])
