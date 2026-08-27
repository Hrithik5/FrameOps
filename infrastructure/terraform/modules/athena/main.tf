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

variable "data_bucket" {
  type    = string
  default = ""
}

variable "account_id" {
  type    = string
  default = "559050238050"
}

locals {
  suffix = "${var.env}-${var.account_id}"
  bucket = var.data_bucket != "" ? var.data_bucket : "frameops-data-${local.suffix}"
}

resource "aws_athena_workgroup" "frameops" {
  name = "frameops-${var.env}"
  configuration {
    result_configuration {
      output_location = "s3://${local.bucket}/athena-results/"
      encryption_configuration { encryption_option = "SSE_S3" }
    }
    engine_version { selected_engine_version = "Athena engine version 3" }
    enforce_workgroup_configuration    = true
    publish_cloudwatch_metrics_enabled = true
  }
  tags = { Project = "FrameOps", Env = var.env }
}

resource "aws_s3_bucket" "athena_results" {
  # Results go into data bucket prefix, but ensure bucket exists (data module creates it)
  # This is a placeholder for policy — actual results use data bucket
  count  = 0
  bucket = "frameops-athena-results-${local.suffix}"
}

output "workgroup" { value = aws_athena_workgroup.frameops.name }
output "results_location" { value = aws_athena_workgroup.frameops.configuration[0].result_configuration[0].output_location }
