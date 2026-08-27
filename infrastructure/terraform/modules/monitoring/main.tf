terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

variable "env" {
  type    = string
  default = "dev"
}

variable "region" {
  type    = string
  default = "YOUR_AWS_REGION"
}

resource "aws_cloudwatch_log_group" "frameops" {
  name              = "/frameops/${var.env}"
  retention_in_days = 30
  tags              = { Project = "FrameOps", Env = var.env }
}

resource "aws_cloudwatch_dashboard" "frameops" {
  dashboard_name = "FrameOps-${var.env}"
  dashboard_body = file("${path.module}/dashboard.json")
}

# Alarms per Spec 
resource "aws_cloudwatch_metric_alarm" "sqs_backlog" {
  alarm_name          = "FrameOps-${var.env}-SQS-Backlog"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = 300
  statistic           = "Maximum"
  threshold           = 1000
  alarm_description   = "Sustained queue backlog — Spec "
}

resource "aws_cloudwatch_metric_alarm" "dlq_growth" {
  alarm_name          = "FrameOps-${var.env}-DLQ-Growth"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = 300
  statistic           = "Maximum"
  threshold           = 0
  alarm_description   = "Unexpected DLQ growth — Spec "
}

resource "aws_cloudwatch_metric_alarm" "sfn_failures" {
  alarm_name          = "FrameOps-${var.env}-SFN-FailureSpike"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ExecutionsFailed"
  namespace           = "AWS/States"
  period              = 300
  statistic           = "Sum"
  threshold           = 5
  alarm_description   = "Step Functions failure spike"
}

output "log_group" { value = aws_cloudwatch_log_group.frameops.name }
output "dashboard" { value = aws_cloudwatch_dashboard.frameops.dashboard_name }
