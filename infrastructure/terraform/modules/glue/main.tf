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

variable "data_bucket" {
  type    = string
  default = ""
}

variable "account_id" {
  type    = string
  default = "YOUR_AWS_ACCOUNT_ID"
}

locals {
  suffix = "${var.env}-${var.account_id}"
  bucket = var.data_bucket != "" ? var.data_bucket : "frameops-data-${local.suffix}"
}

resource "aws_glue_catalog_database" "frameops" {
  name = "frameops_${var.env}"
}

resource "aws_iam_role" "glue" {
  name = "frameops-${var.env}-glue"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Action = "sts:AssumeRole", Effect = "Allow", Principal = { Service = "glue.amazonaws.com" } }]
  })
  tags = { Project = "FrameOps", Env = var.env }
}

resource "aws_iam_role_policy_attachment" "glue" {
  role       = aws_iam_role.glue.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
}

resource "aws_iam_role_policy" "glue_s3" {
  role = aws_iam_role.glue.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      { Effect = "Allow", Action = ["s3:GetObject", "s3:PutObject", "s3:ListBucket"], Resource = ["arn:aws:s3:::${local.bucket}", "arn:aws:s3:::${local.bucket}/*"] },
      { Effect = "Allow", Action = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"], Resource = "*" }
    ]
  })
}

resource "aws_glue_crawler" "asset_metadata" {
  name          = "frameops-${var.env}-asset-metadata"
  database_name = aws_glue_catalog_database.frameops.name
  role          = aws_iam_role.glue.arn
  s3_target { path = "s3://${local.bucket}/asset_metadata/" }
  schedule = "cron(0 1 * * ? *)"
  tags     = { Project = "FrameOps", Env = var.env }
}

resource "aws_glue_crawler" "technical_metadata" {
  name          = "frameops-${var.env}-technical-metadata"
  database_name = aws_glue_catalog_database.frameops.name
  role          = aws_iam_role.glue.arn
  s3_target { path = "s3://${local.bucket}/technical_metadata/" }
  tags = { Project = "FrameOps", Env = var.env }
}

resource "aws_glue_crawler" "processing_jobs" {
  name          = "frameops-${var.env}-processing-jobs"
  database_name = aws_glue_catalog_database.frameops.name
  role          = aws_iam_role.glue.arn
  s3_target { path = "s3://${local.bucket}/processing_jobs/" }
  tags = { Project = "FrameOps", Env = var.env }
}

resource "aws_glue_crawler" "asset_lineage" {
  name          = "frameops-${var.env}-asset-lineage"
  database_name = aws_glue_catalog_database.frameops.name
  role          = aws_iam_role.glue.arn
  s3_target { path = "s3://${local.bucket}/asset_lineage/" }
  tags = { Project = "FrameOps", Env = var.env }
}

output "database_name" { value = aws_glue_catalog_database.frameops.name }
output "crawler_names" {
  value = [
    aws_glue_crawler.asset_metadata.name,
    aws_glue_crawler.technical_metadata.name,
    aws_glue_crawler.processing_jobs.name,
    aws_glue_crawler.asset_lineage.name,
  ]
}
