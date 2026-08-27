terraform {
  required_version = ">= 1.5"
  # backend "s3" disabled for local plan — uncomment before real apply
  # backend "s3" {
  #   bucket         = "frameops-tfstate-dev-ap-south-1"
  #   key            = "dev/ap-south-1/terraform.tfstate"
  #   region         = "ap-south-1"
  #   dynamodb_table = "frameops-tflock-dev"
  # }
  required_providers {
    aws = { source = "hashicorp/aws", version = ">= 5.0" }
  }
}

provider "aws" {
  region = "ap-south-1"
  default_tags { tags = { Project = "FrameOps", Env = "dev" } }
}

locals {
  env        = "dev"
  region     = "ap-south-1"
  account_id = "559050238050"
}

module "vpc" {
  source = "../../../modules/vpc"
  env    = local.env
  region = local.region
}

module "kms" {
  source = "../../../modules/kms"
  env    = local.env
}

module "s3" {
  source     = "../../../modules/s3"
  env        = local.env
  region     = local.region
  account_id = local.account_id
}

module "sqs" {
  source = "../../../modules/sqs"
  env    = local.env
  region = local.region
}

module "dynamodb" {
  source = "../../../modules/dynamodb"
  env    = local.env
  region = local.region
}

module "iam" {
  source = "../../../modules/iam"
  env    = local.env
  region = local.region
}

module "eventbridge" {
  source  = "../../../modules/eventbridge"
  env     = local.env
  region  = local.region
  sqs_arn = module.sqs.queue_arn
}

module "ecs" {
  source                 = "../../../modules/ecs"
  env                    = local.env
  region                 = local.region
  vpc_id                 = module.vpc.vpc_id
  private_subnets        = module.vpc.private_subnets
  ecs_task_role_arn      = module.iam.ecs_role
  ecs_execution_role_arn = ""
  assets_bucket          = module.s3.assets_bucket
  data_bucket            = module.s3.data_bucket
}

module "step_functions" {
  source          = "../../../modules/step-functions"
  env             = local.env
  region          = local.region
  sfn_role_arn    = ""
  ecs_cluster_arn = module.ecs.cluster_arn
  finalizer_arn   = ""
  definition_json = file("${path.module}/../../../../../workflows/processing/definition.asl.json")
}

module "lambda" {
  source            = "../../../modules/lambda"
  env               = local.env
  region            = local.region
  sqs_arn           = module.sqs.queue_arn
  sqs_queue_name    = module.sqs.queue_name
  assets_bucket     = module.s3.assets_bucket
  table_name        = module.dynamodb.table_name
  state_machine_arn = module.step_functions.state_machine_arn
  lambda_role_arn   = module.iam.lambda_role
}

module "glue" {
  source      = "../../../modules/glue"
  env         = local.env
  region      = local.region
  data_bucket = module.s3.data_bucket
  account_id  = local.account_id
}

module "athena" {
  source      = "../../../modules/athena"
  env         = local.env
  region      = local.region
  data_bucket = module.s3.data_bucket
  account_id  = local.account_id
}

module "monitoring" {
  source = "../../../modules/monitoring"
  env    = local.env
  region = local.region
}

output "assets_bucket" { value = module.s3.assets_bucket }
output "data_bucket" { value = module.s3.data_bucket }
output "queue_url" { value = module.sqs.queue_url }
output "dlq_url" { value = module.sqs.dlq_url }
output "table_name" { value = module.dynamodb.table_name }
output "state_machine_arn" { value = module.step_functions.state_machine_arn }
output "cluster_name" { value = module.ecs.cluster_name }
output "validator_lambda" { value = module.lambda.validator_name }
