"""
Module for deploying core CDK resources with Trend Micro's Cloud One
File Storage.
"""
from aws_cdk import RemovalPolicy, CfnParameter
from aws_cdk import Stack, App, aws_events as events
from aws_cdk.aws_iam import Effect
from aws_cdk.aws_logs import RetentionDays
from aws_cdk.aws_sns_subscriptions import EmailSubscription

from ..constructs.lambda_packager import LambdaPackager


class FileStorageStack(Stack):
    # pylint: disable=too-many-locals

    def __init__(self, scope: App, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)
