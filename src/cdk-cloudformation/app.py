#!/usr/bin/env python3
import os

import aws_cdk as cdk

from templates.event_bridge_stack import EventBridgeStack


app = cdk.App()
EventBridgeStack(app, "DataKnightEventBridgeStack")
app.synth()
