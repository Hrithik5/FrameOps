# FrameOps — monitoring module (ap-south-1, local-first)
# Spec §32 — drafted, not applied until approval
terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
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

# TODO: implement monitoring resources per Spec §8, §19-27
output "module" {
  value = "monitoring"
}
