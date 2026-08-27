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

variable "account_id" {
  type    = string
  default = "559050238050"
}

locals {
  suffix = "${var.env}-${var.account_id}"
}

resource "aws_s3_bucket" "assets" {
  bucket        = "frameops-assets-${local.suffix}"
  force_destroy = true
  tags = {
    Project = "FrameOps"
    Env     = var.env
  }
}

resource "aws_s3_bucket_versioning" "assets" {
  bucket = aws_s3_bucket.assets.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "assets" {
  bucket = aws_s3_bucket.assets.id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "AES256" }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "assets" {
  bucket                  = aws_s3_bucket.assets.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "assets" {
  bucket = aws_s3_bucket.assets.id
  rule {
    id     = "quarantine"
    status = "Enabled"
    filter { prefix = "quarantine/" }
    expiration { days = 90 }
  }
  rule {
    id     = "raw-retention"
    status = "Enabled"
    filter { prefix = "raw/" }
    noncurrent_version_expiration { noncurrent_days = 90 }
  }
}

resource "aws_s3_bucket_notification" "assets" {
  bucket      = aws_s3_bucket.assets.id
  eventbridge = true
}

resource "aws_s3_bucket" "data" {
  bucket        = "frameops-data-${local.suffix}"
  force_destroy = true
  tags = {
    Project = "FrameOps"
    Env     = var.env
  }
}

resource "aws_s3_bucket_versioning" "data" {
  bucket = aws_s3_bucket.data.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "data" {
  bucket = aws_s3_bucket.data.id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "AES256" }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "data" {
  bucket                  = aws_s3_bucket.data.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

output "assets_bucket" { value = aws_s3_bucket.assets.bucket }
output "assets_arn" { value = aws_s3_bucket.assets.arn }
output "data_bucket" { value = aws_s3_bucket.data.bucket }
output "data_arn" { value = aws_s3_bucket.data.arn }
