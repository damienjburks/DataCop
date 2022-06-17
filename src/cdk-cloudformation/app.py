#!/usr/bin/env python3
import os

import aws_cdk as cdk

from templates.core_stack import DataKnightCoreStack


app = cdk.App()
DataKnightCoreStack(app, "DataKnightCore")
app.synth()
