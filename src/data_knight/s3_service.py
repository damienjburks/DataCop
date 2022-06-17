"""
Module for calling S3 APIs.
"""
from botocore.exceptions import ClientError
from logging_config import LoggerConfig


class S3Service:

    def __init__(self, boto_session):
        self.boto_session = boto_session
        self.logger = LoggerConfig().configure_logger(type(self).__name__)

    def attach_deny_all_acl(self):
        pass

    def download_file(self, s3_key, s3_bucket_name, file_name):
        s3_resource = self.boto_session.resource('s3')
        try:
            self.logger.debug("Downloading S3 key: %s", s3_key)
            s3_resource.Bucket(s3_bucket_name).download_file(s3_key, file_name)
            self.logger.debug("Downloaded S3 file, %s, successfully!", file_name)

            return file_name
        except ClientError as c_err:
            if c_err.response['Error']['Code'] == '404':
                print("This object doesn't exist. Please advise.")
            else:
                raise