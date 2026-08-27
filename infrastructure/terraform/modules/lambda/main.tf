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
  default = "YOUR_AWS_REGION"
}

variable "sqs_arn" {
  type    = string
  default = ""
}

variable "sqs_queue_name" {
  type    = string
  default = ""
}

variable "assets_bucket" {
  type    = string
  default = ""
}

variable "table_name" {
  type    = string
  default = ""
}

variable "state_machine_arn" {
  type    = string
  default = ""
}

variable "lambda_role_arn" {
  type    = string
  default = ""
}

# Real validator zip — packages services/validator + data/schemas + fallback logic (Spec )
# Build dir is at ../../../../build/lambda_validator (created via build/lambda_validator)
data "archive_file" "validator_placeholder" {
  type        = "zip"
  output_path = "${path.module}/validator_placeholder.zip"
  source_dir  = "${path.module}/../../../../build/lambda_validator"
  excludes    = ["__pycache__"]
}

resource "aws_cloudwatch_log_group" "validator" {
  name              = "/aws/lambda/frameops-${var.env}-validator"
  retention_in_days = 30
  tags = {
    Project = "FrameOps"
    Env     = var.env
  }
}

resource "aws_lambda_function" "validator" {
  function_name    = "frameops-${var.env}-validator"
  handler          = "handler.lambda_handler"
  runtime          = "python3.11"
  filename         = data.archive_file.validator_placeholder.output_path
  source_code_hash = data.archive_file.validator_placeholder.output_base64sha256
  role             = var.lambda_role_arn != "" ? var.lambda_role_arn : "arn:aws:iam::YOUR_AWS_ACCOUNT_ID:role/frameops-${var.env}-lambda-validator"
  timeout          = 30
  memory_size      = 256
  environment {
    variables = {
      ENV               = var.env
      TABLE_NAME        = var.table_name
      STATE_MACHINE_ARN = var.state_machine_arn
      ASSETS_BUCKET     = var.assets_bucket
    }
  }
  tags = {
    Project = "FrameOps"
    Env     = var.env
  }
  depends_on = [aws_cloudwatch_log_group.validator]
}

resource "aws_lambda_event_source_mapping" "sqs" {
  event_source_arn                   = var.sqs_arn
  function_name                      = aws_lambda_function.validator.arn
  batch_size                         = 10
  maximum_batching_window_in_seconds = 5
  function_response_types            = ["ReportBatchItemFailures"]
}

# Finalizer Lambda — real handler with audit (uses same build as validator)
data "archive_file" "finalizer_placeholder" {
  type        = "zip"
  output_path = "${path.module}/finalizer_placeholder.zip"
  source_dir  = "${path.module}/../../../../build/lambda_validator"
  excludes    = ["__pycache__"]
}

resource "aws_cloudwatch_log_group" "finalizer" {
  name              = "/aws/lambda/frameops-${var.env}-finalizer"
  retention_in_days = 30
  tags = {
    Project = "FrameOps"
    Env     = var.env
  }
}

resource "aws_lambda_function" "finalizer" {
  function_name    = "frameops-${var.env}-finalizer"
  handler          = "services.finalizer.handler.lambda_handler"
  runtime          = "python3.11"
  filename         = data.archive_file.finalizer_placeholder.output_path
  source_code_hash = data.archive_file.finalizer_placeholder.output_base64sha256
  role             = var.lambda_role_arn != "" ? var.lambda_role_arn : "arn:aws:iam::YOUR_AWS_ACCOUNT_ID:role/frameops-${var.env}-lambda-validator"
  timeout          = 30
  memory_size      = 256
  environment {
    variables = {
      ENV          = var.env
      DATA_BUCKET  = var.assets_bucket != "" ? replace(var.assets_bucket, "assets", "data") : ""
      AUDIT_BUCKET = var.assets_bucket != "" ? replace(var.assets_bucket, "assets", "data") : ""
    }
  }
  tags = {
    Project = "FrameOps"
    Env     = var.env
  }
  depends_on = [aws_cloudwatch_log_group.finalizer]
}

output "validator_arn" { value = aws_lambda_function.validator.arn }
output "validator_name" { value = aws_lambda_function.validator.function_name }
output "finalizer_arn" { value = aws_lambda_function.finalizer.arn }
output "finalizer_name" { value = aws_lambda_function.finalizer.function_name }
