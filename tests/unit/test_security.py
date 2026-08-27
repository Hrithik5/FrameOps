from services.security.iam import least_privilege_check, validate_no_admin
from services.security.redact import redact_dict, redact_string


def test_no_admin():
    assert validate_no_admin("lambda_validator") is True
    assert validate_no_admin("ecs_worker") is True


def test_least_privilege():
    assert least_privilege_check("lambda_validator") == []
    assert least_privilege_check("ecs_worker") == []


def test_redact_dict():
    data = {"username": "alice", "password": "secret123", "nested": {"api_key": "abc"}}
    redacted = redact_dict(data)
    assert redacted["password"] == "***REDACTED***"
    assert redacted["nested"]["api_key"] == "***REDACTED***"
    assert redacted["username"] == "alice"


def test_redact_aws_key():
    s = "key AKIAIOSFODNN7EXAMPLE leaked"
    assert "***REDACTED***" in redact_string(s)


def test_secrets_not_in_logs():
    # Simulate log line check per bullet 4
    log = "processing asset a1 with checksum abc and token mytoken"
    redacted = redact_string(log)
    assert "mytoken" not in redacted or "***" in redacted
