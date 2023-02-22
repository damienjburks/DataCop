#!/usr/bin/env python3
"""
Module for running the CDK app and deploying all infrastructure.
"""
from os import environ
import aws_cdk as cdk

from templates.core_stack import CoreStack
from templates.integrations.aws_rekognition_image_stack import RekognitionImageStack
from templates.integrations.aws_macie_stack import MacieStack
from templates.integrations.tm_file_storage_stack import FileStorageStack

app = cdk.App()

core_stack = CoreStack(app, "DataCopCore")

rekognition_image_stack = RekognitionImageStack(app, "DCRekognitionImageStack")
rekognition_image_stack.node.add_dependency(core_stack)

aws_macie_stack = MacieStack(app, "DCMacieStack")
aws_macie_stack.node.add_dependency(core_stack)

if environ.get("FSS_SNS_TOPIC_ARN") is not None:
    fss_stack = FileStorageStack(app, "DataCopFssStack")
    fss_stack.node.add_dependency(core_stack)

app.synth()
