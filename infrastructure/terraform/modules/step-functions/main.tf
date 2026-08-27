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

variable "sfn_role_arn" {
  type    = string
  default = ""
}

variable "ecs_cluster_arn" {
  type    = string
  default = ""
}

variable "finalizer_arn" {
  type    = string
  default = ""
}

variable "definition_json" {
  type        = string
  description = "Step Functions ASL JSON"
  default     = ""
}

resource "aws_iam_role" "sfn" {
  count = var.sfn_role_arn == "" ? 1 : 0
  name  = "frameops-${var.env}-sfn"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Action = "sts:AssumeRole", Effect = "Allow", Principal = { Service = "states.amazonaws.com" } }]
  })
  tags = { Project = "FrameOps", Env = var.env }
}

resource "aws_iam_role_policy" "sfn" {
  count = var.sfn_role_arn == "" ? 1 : 0
  role  = aws_iam_role.sfn[0].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      { Effect = "Allow", Action = ["ecs:RunTask", "ecs:StopTask", "ecs:DescribeTasks", "iam:PassRole"], Resource = "*" },
      { Effect = "Allow", Action = ["lambda:InvokeFunction"], Resource = var.finalizer_arn != "" ? var.finalizer_arn : "*" },
      { Effect = "Allow", Action = ["logs:CreateLogDelivery", "logs:CreateLogStream", "logs:PutLogEvents", "logs:DescribeLogGroups"], Resource = "*" },
      { Effect = "Allow", Action = ["events:PutTargets", "events:PutRule", "events:DescribeRule"], Resource = "*" }
    ]
  })
}

resource "aws_cloudwatch_log_group" "sfn" {
  name              = "/aws/states/frameops-${var.env}"
  retention_in_days = 30
  tags              = { Project = "FrameOps", Env = var.env }
}

resource "aws_sfn_state_machine" "processing" {
  name       = "frameops-${var.env}-processing"
  role_arn   = var.sfn_role_arn != "" ? var.sfn_role_arn : aws_iam_role.sfn[0].arn
  definition = var.definition_json
  # logging_configuration disabled for initial apply — SFN log delivery requires
  # additional CW resource policy (AccessDeniedException fix). Re-enable after
  # adding aws_cloudwatch_log_resource_policy for states.amazonaws.com
  # logging_configuration {
  #   level                  = "ALL"
  #   include_execution_data = true
  #   log_destination        = "${aws_cloudwatch_log_group.sfn.arn}:*"
  # }
  # tracing_configuration { enabled = true }
  tags       = { Project = "FrameOps", Env = var.env }
  depends_on = [aws_cloudwatch_log_group.sfn, aws_iam_role_policy.sfn]
}

output "state_machine_arn" { value = aws_sfn_state_machine.processing.arn }
output "state_machine_name" { value = aws_sfn_state_machine.processing.name }
