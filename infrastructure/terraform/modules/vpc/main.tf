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
  default = "ap-south-1"
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

output "vpc_id" { value = aws_vpc.frameops.id }
output "private_subnets" { value = [aws_subnet.private_a.id, aws_subnet.private_b.id] }
