# Terraform

Dev and prod have separate state files — never share state .

Remote backend:
- `s3://frameops-tfstate-dev-ap-south-1` + `frameops-tflock-dev`
- `s3://frameops-tfstate-prod-ap-south-1` + `frameops-tflock-prod`

```bash
cd environments/dev/ap-south-1
terraform init
terraform plan
terraform apply  # dev only; prod requires manual approval per Spec 
```
