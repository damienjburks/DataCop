from .constructs.lambda_packager import LambdaPackager

from aws_cdk import aws_events as events
from aws_cdk import aws_events_targets as targets
from aws_cdk import (
    Stack,
    App,
    Duration,
    aws_lambda as _lambda,
    aws_sqs as sqs,
    aws_logs as logs,
)

DETAIL_JSON = {
    "eventSource": ["macie2.amazonaws.com"],
    "eventName": ["CreateClassificationJob"],
}

class EventBridgeStack(Stack):
    def __init__(self, scope: App, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Creating Lambda Function and packaging it up
        lambda_package_dir = LambdaPackager("../lambda").package()
        fn = _lambda.Function(
            self,
            "DataKnightLambda",
            function_name="DataKnightLambda",
            runtime=_lambda.Runtime.PYTHON_3_9,
            timeout=Duration.minutes(10),
            handler="handler.lambda_handler",
            log_retention=logs.RetentionDays.INFINITE,
            code=_lambda.Code.from_asset(path=lambda_package_dir),
        )

        rule = events.Rule(
            self,
            "DataKnightRule",
            event_pattern=events.EventPattern(
                source=["aws.macie2"],
                detail_type=["AWS API Call via CloudTrail"],
                detail=DETAIL_JSON,
            ),
            rule_name="DataKnightRule",
        )

        queue = sqs.Queue(self, "DataKnightQueue")

        rule.add_target(
            targets.LambdaFunction(
                fn,
                dead_letter_queue=queue,
                max_event_age=Duration.hours(2),
                retry_attempts=2,
            )
        )