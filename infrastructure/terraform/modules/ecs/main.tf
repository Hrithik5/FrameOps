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

variable "vpc_id" {
  type    = string
  default = ""
}

variable "private_subnets" {
  type    = list(string)
  default = []
}

variable "ecs_task_role_arn" {
  type    = string
  default = ""
}

variable "ecs_execution_role_arn" {
  type    = string
  default = ""
}

variable "assets_bucket" {
  type    = string
  default = ""
}

variable "data_bucket" {
  type    = string
  default = ""
}

resource "aws_ecs_cluster" "frameops" {
  name = "frameops-${var.env}"
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
  tags = { Project = "FrameOps", Env = var.env }
}

resource "aws_ecr_repository" "metadata" {
  name                 = "frameops-metadata"
  image_tag_mutability = "MUTABLE"
  force_delete         = true
  tags                 = { Project = "FrameOps", Env = var.env }
}

resource "aws_ecr_repository" "transcode" {
  name                 = "frameops-transcode"
  image_tag_mutability = "MUTABLE"
  force_delete         = true
  tags                 = { Project = "FrameOps", Env = var.env }
}

resource "aws_ecr_repository" "thumbnail" {
  name                 = "frameops-thumbnail"
  image_tag_mutability = "MUTABLE"
  force_delete         = true
  tags                 = { Project = "FrameOps", Env = var.env }
}

resource "aws_ecr_repository" "audio" {
  name                 = "frameops-audio"
  image_tag_mutability = "MUTABLE"
  force_delete         = true
  tags                 = { Project = "FrameOps", Env = var.env }
}

resource "aws_ecr_repository" "document" {
  name                 = "frameops-document"
  image_tag_mutability = "MUTABLE"
  force_delete         = true
  tags                 = { Project = "FrameOps", Env = var.env }
}

resource "aws_iam_role" "execution" {
  count = var.ecs_execution_role_arn == "" ? 1 : 0
  name  = "frameops-${var.env}-ecs-execution"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Action = "sts:AssumeRole", Effect = "Allow", Principal = { Service = "ecs-tasks.amazonaws.com" } }]
  })
  tags = { Project = "FrameOps", Env = var.env }
}

resource "aws_iam_role_policy_attachment" "execution" {
  count      = var.ecs_execution_role_arn == "" ? 1 : 0
  role       = aws_iam_role.execution[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_cloudwatch_log_group" "ecs" {
  name              = "/ecs/frameops-${var.env}"
  retention_in_days = 30
  tags              = { Project = "FrameOps", Env = var.env }
}

locals {
  execution_role = var.ecs_execution_role_arn != "" ? var.ecs_execution_role_arn : aws_iam_role.execution[0].arn
  task_role      = var.ecs_task_role_arn != "" ? var.ecs_task_role_arn : "arn:aws:iam::559050238050:role/frameops-${var.env}-ecs-worker"
}

# Metadata task — 512/1024 (Spec §44) — uses ECR image if pushed, else busybox for test
resource "aws_ecs_task_definition" "metadata" {
  family                   = "frameops-${var.env}-metadata"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "512"
  memory                   = "1024"
  execution_role_arn       = local.execution_role
  task_role_arn            = local.task_role
  container_definitions = jsonencode([{
    name      = "metadata"
    image     = "${aws_ecr_repository.metadata.repository_url}:latest"
    essential = true
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.ecs.name
        awslogs-region        = var.region
        awslogs-stream-prefix = "metadata"
      }
    }
    environment = [
      { name = "ENV", value = var.env },
      { name = "ASSETS_BUCKET", value = var.assets_bucket },
      { name = "DATA_BUCKET", value = var.data_bucket }
    ]
  }])
  tags = { Project = "FrameOps", Env = var.env }
}

# Transcode task — 1024/2048 (Spec §44)
resource "aws_ecs_task_definition" "transcode" {
  family                   = "frameops-${var.env}-transcode"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "1024"
  memory                   = "2048"
  execution_role_arn       = local.execution_role
  task_role_arn            = local.task_role
  container_definitions = jsonencode([{
    name      = "transcode"
    image     = "${aws_ecr_repository.transcode.repository_url}:latest"
    essential = true
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.ecs.name
        awslogs-region        = var.region
        awslogs-stream-prefix = "transcode"
      }
    }
    environment = [
      { name = "ENV", value = var.env },
      { name = "ASSETS_BUCKET", value = var.assets_bucket },
      { name = "DATA_BUCKET", value = var.data_bucket }
    ]
  }])
  tags = { Project = "FrameOps", Env = var.env }
}

# Thumbnail task — 512/1024
resource "aws_ecs_task_definition" "thumbnail" {
  family                   = "frameops-${var.env}-thumbnail"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "512"
  memory                   = "1024"
  execution_role_arn       = local.execution_role
  task_role_arn            = local.task_role
  container_definitions = jsonencode([{
    name      = "thumbnail"
    image     = "${aws_ecr_repository.thumbnail.repository_url}:latest"
    essential = true
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.ecs.name
        awslogs-region        = var.region
        awslogs-stream-prefix = "thumbnail"
      }
    }
    environment = [
      { name = "ENV", value = var.env },
      { name = "ASSETS_BUCKET", value = var.assets_bucket },
      { name = "DATA_BUCKET", value = var.data_bucket }
    ]
  }])
  tags = { Project = "FrameOps", Env = var.env }
}

# Audio task — 512/1024
resource "aws_ecs_task_definition" "audio" {
  family                   = "frameops-${var.env}-audio"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "512"
  memory                   = "1024"
  execution_role_arn       = local.execution_role
  task_role_arn            = local.task_role
  container_definitions = jsonencode([{
    name      = "audio"
    image     = "${aws_ecr_repository.audio.repository_url}:latest"
    essential = true
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.ecs.name
        awslogs-region        = var.region
        awslogs-stream-prefix = "audio"
      }
    }
    environment = [
      { name = "ENV", value = var.env },
      { name = "ASSETS_BUCKET", value = var.assets_bucket },
      { name = "DATA_BUCKET", value = var.data_bucket }
    ]
  }])
  tags = { Project = "FrameOps", Env = var.env }
}

# Document task — 512/1024
resource "aws_ecs_task_definition" "document" {
  family                   = "frameops-${var.env}-document"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "512"
  memory                   = "1024"
  execution_role_arn       = local.execution_role
  task_role_arn            = local.task_role
  container_definitions = jsonencode([{
    name      = "document"
    image     = "${aws_ecr_repository.document.repository_url}:latest"
    essential = true
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.ecs.name
        awslogs-region        = var.region
        awslogs-stream-prefix = "document"
      }
    }
    environment = [
      { name = "ENV", value = var.env },
      { name = "ASSETS_BUCKET", value = var.assets_bucket },
      { name = "DATA_BUCKET", value = var.data_bucket }
    ]
  }])
  tags = { Project = "FrameOps", Env = var.env }
}

output "cluster_arn" { value = aws_ecs_cluster.frameops.arn }
output "cluster_name" { value = aws_ecs_cluster.frameops.name }
output "metadata_task_arn" { value = aws_ecs_task_definition.metadata.arn }
output "transcode_task_arn" { value = aws_ecs_task_definition.transcode.arn }
output "thumbnail_task_arn" { value = aws_ecs_task_definition.thumbnail.arn }
output "audio_task_arn" { value = aws_ecs_task_definition.audio.arn }
output "document_task_arn" { value = aws_ecs_task_definition.document.arn }
output "metadata_repo" { value = aws_ecr_repository.metadata.repository_url }
output "transcode_repo" { value = aws_ecr_repository.transcode.repository_url }
output "thumbnail_repo" { value = aws_ecr_repository.thumbnail.repository_url }
output "audio_repo" { value = aws_ecr_repository.audio.repository_url }
output "document_repo" { value = aws_ecr_repository.document.repository_url }
output "log_group" { value = aws_cloudwatch_log_group.ecs.name }
