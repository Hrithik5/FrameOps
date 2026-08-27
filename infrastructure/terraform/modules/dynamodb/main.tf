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

resource "aws_dynamodb_table" "assets" {
  name         = "frameops-${var.env}-assets"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "PK"
  range_key    = "SK"

  # PK=ASSET#<asset_id>, SK=ASSET#<asset_id> for asset, SK=JOB#<job_id> for jobs 
  attribute {
    name = "PK"
    type = "S"
  }
  attribute {
    name = "SK"
    type = "S"
  }
  attribute {
    name = "GSI1PK"
    type = "S"
  }
  attribute {
    name = "GSI1SK"
    type = "S"
  }

  global_secondary_index {
    name            = "GSI1"
    hash_key        = "GSI1PK"
    range_key       = "GSI1SK"
    projection_type = "ALL"
  }

  point_in_time_recovery { enabled = true }

  server_side_encryption { enabled = true }

  ttl {
    attribute_name = "ttl"
    enabled        = false
  }

  tags = {
    Project = "FrameOps"
    Env     = var.env
  }
}

output "table_name" { value = aws_dynamodb_table.assets.name }
output "table_arn" { value = aws_dynamodb_table.assets.arn }
