# FrameOps dev ap-south-1 — composes all modules (not applied until approval)
terraform {
  required_version = ">= 1.5"
  backend "s3" {
    # bucket = "frameops-tfstate-dev-ap-south-1"
    # key    = "dev/ap-south-1/terraform.tfstate"
    # region = "ap-south-1"
    # dynamodb_table = "frameops-tflock-dev"
  }
  required_providers {
    aws = { source = "hashicorp/aws", version = ">= 5.0" }
  }
}

provider "aws" {
  region = "ap-south-1"
}

module "s3" { source = "../../../modules/s3" }
module "sqs" { source = "../../../modules/sqs" }
module "lambda" { source = "../../../modules/lambda" }
module "dynamodb" { source = "../../../modules/dynamodb" }
module "ecs" { source = "../../../modules/ecs" }
module "step_functions" { source = "../../../modules/step-functions" }
module "glue" { source = "../../../modules/glue" }
module "athena" { source = "../../../modules/athena" }
module "monitoring" { source = "../../../modules/monitoring" }
module "iam" { source = "../../../modules/iam" }
module "vpc" { source = "../../../modules/vpc" }
