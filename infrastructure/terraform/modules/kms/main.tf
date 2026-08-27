terraform {
  required_version = ">= 1.5"
  required_providers { aws = { source = "hashicorp/aws", version = ">= 5.0" } }
}
variable "env" {
  type    = string
  default = "dev"
}

resource "aws_kms_key" "frameops" {
  description             = "FrameOps ${var.env} key"
  deletion_window_in_days = 7
  enable_key_rotation     = true
  tags                    = { Project = "FrameOps", Env = var.env }
}

resource "aws_kms_alias" "frameops" {
  name          = "alias/frameops-${var.env}"
  target_key_id = aws_kms_key.frameops.key_id
}

output "key_id" { value = aws_kms_key.frameops.key_id }
output "alias" { value = aws_kms_alias.frameops.name }
