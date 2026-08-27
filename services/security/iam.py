"""IAM least-privilege helpers — Spec Table 9."""

ROLE_SCOPES = {
    "lambda_validator": {
        "actions": [
            "s3:GetObject",
            "sqs:ReceiveMessage",
            "sqs:DeleteMessage",
            "dynamodb:PutItem",
            "states:StartExecution",
            "logs:CreateLogStream",
            "logs:PutLogEvents",
        ],
        "resources": [
            "arn:aws:s3:::frameops-assets-dev/raw/*",
            "arn:aws:sqs:ap-south-1:*:frameops-*",
            "arn:aws:dynamodb:ap-south-1:*:table/frameops-*",
        ],
    },
    "step_functions": {
        "actions": [
            "ecs:RunTask",
            "ecs:DescribeTasks",
            "lambda:InvokeFunction",
            "logs:CreateLogStream",
        ],
        "resources": ["*"],
    },
    "ecs_worker": {
        "actions": ["s3:GetObject", "s3:PutObject", "dynamodb:UpdateItem", "logs:PutLogEvents"],
        "resources": [
            "arn:aws:s3:::frameops-assets-dev/*",
            "arn:aws:dynamodb:ap-south-1:*:table/frameops-*",
        ],
    },
    "glue": {
        "actions": ["s3:GetObject", "s3:ListBucket", "glue:*"],
        "resources": ["arn:aws:s3:::frameops-data-dev/*"],
    },
}


def validate_no_admin(role: str) -> bool:
    """Ensure no AdministratorAccess."""
    scope = ROLE_SCOPES.get(role, {})
    actions = scope.get("actions", [])
    return "iam:*" not in actions and "*:*" not in actions and "AdministratorAccess" not in actions


def least_privilege_check(role: str) -> list[str]:
    """Return violations if any over-broad permissions."""
    violations = []
    scope = ROLE_SCOPES.get(role, {})
    for a in scope.get("actions", []):
        if a == "*:*" or a == "s3:*":
            violations.append(f"overbroad {a} in {role}")
    return violations
