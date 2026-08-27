"""Alarm definitions — Spec bullet list."""

ALARMS = [
    {
        "name": "FrameOps-SQS-Backlog",
        "metric": "SQSQueueDepth",
        "threshold": 1000,
        "evaluation_periods": 2,
        "comparison": "GreaterThanThreshold",
        "description": "Sustained queue backlog",
    },
    {
        "name": "FrameOps-DLQ-Growth",
        "metric": "DLQDepth",
        "threshold": 1,
        "evaluation_periods": 1,
        "comparison": "GreaterThanThreshold",
        "description": "Unexpected DLQ growth",
    },
    {
        "name": "FrameOps-SFN-FailureSpike",
        "metric": "StepFunctionsFailed",
        "threshold": 5,
        "evaluation_periods": 1,
        "comparison": "GreaterThanThreshold",
        "description": "Step Functions failure spike",
    },
    {
        "name": "FrameOps-ECS-Failures",
        "metric": "ECSTaskFailed",
        "threshold": 5,
        "evaluation_periods": 1,
        "comparison": "GreaterThanThreshold",
        "description": "ECS task failures",
    },
    {
        "name": "FrameOps-Lambda-Errors",
        "metric": "LambdaErrors",
        "threshold": 10,
        "evaluation_periods": 1,
        "comparison": "GreaterThanThreshold",
        "description": "Lambda error/throttle spike",
    },
    {
        "name": "FrameOps-DQ-Failures",
        "metric": "DataQualityFailures",
        "threshold": 5,
        "evaluation_periods": 1,
        "comparison": "GreaterThanThreshold",
        "description": "Data-quality failure spike",
    },
]
