terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = { source = "hashicorp/aws", version = ">= 5.0" }
  }
}

variable "env" {
  type    = string
  default = "dev"
}

variable "region" {
  type    = string
  default = "ap-south-1"
}

variable "sqs_arn" {
  type        = string
  description = "SQS queue ARN to route S3 ObjectCreated events"
  default     = ""
}

variable "assets_bucket_arn" {
  type    = string
  default = ""
}

resource "aws_cloudwatch_event_rule" "s3_object_created" {
  name        = "frameops-${var.env}-s3-object-created"
  description = "Route S3 ObjectCreated to SQS (Spec §8 EventBridge)"
  event_pattern = jsonencode({
    source        = ["aws.s3"]
    "detail-type" = ["Object Created"]
    detail = {
      bucket = { name = [{ prefix = "frameops-assets-" }] }
    }
  })
  tags = {
    Project = "FrameOps"
    Env     = var.env
  }
}

resource "aws_cloudwatch_event_target" "to_sqs" {
  count     = var.sqs_arn != "" ? 1 : 0
  rule      = aws_cloudwatch_event_rule.s3_object_created.name
  target_id = "SendToSQS"
  arn       = var.sqs_arn
}

# Event bus policy is not needed for default bus; SQS policy is in sqs module
output "rule_arn" { value = aws_cloudwatch_event_rule.s3_object_created.arn }
output "rule_name" { value = aws_cloudwatch_event_rule.s3_object_created.name }
