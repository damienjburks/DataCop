"""
Module for defining Lambda handler.
"""

import os
import json


def lambda_handler(event, context):
    json_region = os.environ["AWS_REGION"]
    json_body = {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"Region ": json_region}),
    }
    print(json_body)

    return json_body
