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

resource "aws_vpc" "frameops" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
  tags                 = { Name = "frameops-${var.env}", Project = "FrameOps" }
}

resource "aws_subnet" "private_a" {
  vpc_id            = aws_vpc.frameops.id
  cidr_block        = "10.0.1.0/24"
  availability_zone = "${var.region}a"
  tags              = { Name = "frameops-${var.env}-private-a" }
}

resource "aws_subnet" "private_b" {
  vpc_id            = aws_vpc.frameops.id
  cidr_block        = "10.0.2.0/24"
  availability_zone = "${var.region}b"
  tags              = { Name = "frameops-${var.env}-private-b" }
}

# VPC endpoints to avoid NAT cost in dev (Spec §44)
resource "aws_vpc_endpoint" "s3" {
  vpc_id       = aws_vpc.frameops.id
  service_name = "com.amazonaws.${var.region}.s3"
  tags         = { Name = "frameops-${var.env}-s3" }
}

resource "aws_vpc_endpoint" "dynamodb" {
  vpc_id       = aws_vpc.frameops.id
  service_name = "com.amazonaws.${var.region}.dynamodb"
  tags         = { Name = "frameops-${var.env}-dynamodb" }
}

# Security group for ECS Fargate tasks
resource "aws_security_group" "ecs_tasks" {
  name        = "frameops-${var.env}-ecs-tasks"
  description = "Allow ECS tasks egress"
  vpc_id      = aws_vpc.frameops.id
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = { Name = "frameops-${var.env}-ecs-tasks", Project = "FrameOps" }
}

# ECR and Logs endpoints for Fargate image pull without NAT
resource "aws_vpc_endpoint" "ecr_api" {
  vpc_id              = aws_vpc.frameops.id
  service_name        = "com.amazonaws.${var.region}.ecr.api"
  vpc_endpoint_type   = "Interface"
  private_dns_enabled = true
  subnet_ids          = [aws_subnet.private_a.id, aws_subnet.private_b.id]
  security_group_ids  = [aws_security_group.ecs_tasks.id]
  tags                = { Name = "frameops-${var.env}-ecr-api" }
}

resource "aws_vpc_endpoint" "ecr_dkr" {
  vpc_id              = aws_vpc.frameops.id
  service_name        = "com.amazonaws.${var.region}.ecr.dkr"
  vpc_endpoint_type   = "Interface"
  private_dns_enabled = true
  subnet_ids          = [aws_subnet.private_a.id, aws_subnet.private_b.id]
  security_group_ids  = [aws_security_group.ecs_tasks.id]
  tags                = { Name = "frameops-${var.env}-ecr-dkr" }
}

resource "aws_vpc_endpoint" "logs" {
  vpc_id              = aws_vpc.frameops.id
  service_name        = "com.amazonaws.${var.region}.logs"
  vpc_endpoint_type   = "Interface"
  private_dns_enabled = true
  subnet_ids          = [aws_subnet.private_a.id, aws_subnet.private_b.id]
  security_group_ids  = [aws_security_group.ecs_tasks.id]
  tags                = { Name = "frameops-${var.env}-logs" }
}

output "vpc_id" { value = aws_vpc.frameops.id }
output "private_subnets" { value = [aws_subnet.private_a.id, aws_subnet.private_b.id] }
output "ecs_security_group" { value = aws_security_group.ecs_tasks.id }
