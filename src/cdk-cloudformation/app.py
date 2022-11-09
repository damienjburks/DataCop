#!/usr/bin/env python3
"""
Module for running the CDK app and deploying all infrastructure.
"""
import aws_cdk as cdk

from templates.core_stack import CoreStack
from templates.integrations.aws_macie_stack import MacieStack
from templates.integrations.file_storage_stack import FileStorageStack

app = cdk.App()

core_stack = CoreStack(app, "DataCopCore")
aws_macie_stack = MacieStack(app, "DataCopMacieStack")
fss_stack = FileStorageStack(app, "DataCopFssStack")

# Dependencies
aws_macie_stack.node.add_dependency(core_stack)
fss_stack.node.add_dependency(core_stack)

app.synth()
