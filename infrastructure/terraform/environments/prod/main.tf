# FrameOps prod — isolated state (Spec §32: no shared state)
terraform {
  required_version = ">= 1.5"
  backend "s3" {
    # bucket = "frameops-tfstate-prod-ap-south-1"
    # key    = "prod/ap-south-1/terraform.tfstate"
    # region = "ap-south-1"
    # dynamodb_table = "frameops-tflock-prod"
  }
  required_providers {
    aws = { source = "hashicorp/aws", version = ">= 5.0" }
  }
}

provider "aws" {
  region = "ap-south-1"
  default_tags { tags = { Project = "FrameOps", Env = "prod" } }
}

# Prod composes same modules with stricter vars (e.g., retention, PITR)
module "s3" { source = "../../modules/s3" }
module "kms" { source = "../../modules/kms" }
module "vpc" { source = "../../modules/vpc" }
module "iam" { source = "../../modules/iam" }
