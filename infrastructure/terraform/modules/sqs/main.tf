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

resource "aws_sqs_queue" "dlq" {
  name                       = "frameops-${var.env}-dlq"
  message_retention_seconds  = 1209600 # 14 days
  visibility_timeout_seconds = 300
  tags = {
    Project = "FrameOps"
    Env     = var.env
  }
}

resource "aws_sqs_queue" "main" {
  name                       = "frameops-${var.env}-queue"
  visibility_timeout_seconds = 300 # Spec §4, prevents blocking
  message_retention_seconds  = 1209600
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn
    maxReceiveCount     = 5 # Spec §23 delivery/control
  })
  tags = {
    Project = "FrameOps"
    Env     = var.env
  }
}

resource "aws_sqs_queue_policy" "main" {
  queue_url = aws_sqs_queue.main.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Principal = { Service = "events.amazonaws.com" }
        Action    = "sqs:SendMessage"
        Resource  = aws_sqs_queue.main.arn
        Condition = { ArnEquals = { "aws:SourceArn" = "arn:aws:events:${var.region}:*:rule/frameops-${var.env}-*" } }
      }
    ]
  })
}

output "queue_url" { value = aws_sqs_queue.main.url }
output "queue_arn" { value = aws_sqs_queue.main.arn }
output "queue_name" { value = aws_sqs_queue.main.name }
output "dlq_url" { value = aws_sqs_queue.dlq.url }
output "dlq_arn" { value = aws_sqs_queue.dlq.arn }
output "dlq_name" { value = aws_sqs_queue.dlq.name }
