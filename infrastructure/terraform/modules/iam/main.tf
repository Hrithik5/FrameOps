terraform {
  required_version = ">= 1.5"
  required_providers { aws = { source = "hashicorp/aws", version = ">= 5.0" } }
}

variable "env" {
  type    = string
  default = "dev"
}
variable "region" {
  type    = string
  default = "YOUR_AWS_REGION"
}

resource "aws_iam_role" "lambda_validator" {
  name = "frameops-${var.env}-lambda-validator"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17",
    Statement = [{ Action = "sts:AssumeRole", Effect = "Allow", Principal = { Service = "lambda.amazonaws.com" } }]
  })
}

resource "aws_iam_role_policy" "lambda_validator" {
  role = aws_iam_role.lambda_validator.id
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      { Effect = "Allow", Action = ["s3:GetObject"], Resource = "arn:aws:s3:::frameops-assets-${var.env}/raw/*" },
      { Effect = "Allow", Action = ["sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:GetQueueAttributes"], Resource = "arn:aws:sqs:${var.region}:*:frameops-${var.env}-*" },
      { Effect = "Allow", Action = ["dynamodb:PutItem", "dynamodb:GetItem"], Resource = "arn:aws:dynamodb:${var.region}:*:table/frameops-${var.env}-*" },
      { Effect = "Allow", Action = ["states:StartExecution"], Resource = "arn:aws:states:${var.region}:*:stateMachine:frameops-${var.env}-*" },
      { Effect = "Allow", Action = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"], Resource = "arn:aws:logs:${var.region}:*:log-group:/frameops/${var.env}:*" }
    ]
  })
}

resource "aws_iam_role" "ecs_worker" {
  name = "frameops-${var.env}-ecs-worker"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17",
    Statement = [{ Action = "sts:AssumeRole", Effect = "Allow", Principal = { Service = "ecs-tasks.amazonaws.com" } }]
  })
}

resource "aws_iam_role_policy" "ecs_worker" {
  role = aws_iam_role.ecs_worker.id
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      { Effect = "Allow", Action = ["s3:GetObject"], Resource = "arn:aws:s3:::frameops-assets-${var.env}/raw/*" },
      { Effect = "Allow", Action = ["s3:PutObject"], Resource = "arn:aws:s3:::frameops-assets-${var.env}/processed/*" },
      { Effect = "Allow", Action = ["dynamodb:UpdateItem"], Resource = "arn:aws:dynamodb:${var.region}:*:table/frameops-${var.env}-*" },
      { Effect = "Allow", Action = ["logs:PutLogEvents", "logs:CreateLogStream"], Resource = "*" }
    ]
  })
}

output "lambda_role" { value = aws_iam_role.lambda_validator.arn }
output "ecs_role" { value = aws_iam_role.ecs_worker.arn }
