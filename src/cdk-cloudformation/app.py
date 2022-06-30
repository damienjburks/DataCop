#!/usr/bin/env python3
"""
Module for running the CDK app and deploying all infrastructure.
"""
import aws_cdk as cdk
import os

from templates.core_stack import DataCopCoreStack

app = cdk.App()
DataCopCoreStack(app, "DataCopCore")
app.synth()
