# AWS Auth & S3

*Hands-on notes, Terraform course day 3*

## How Terraform gets into AWS

* Terraform calls AWS APIs through the provider → every call must be signed with AWS credentials
* Authentication → who are you (access keys, SSO session, role)
* Authorization → what are you allowed to do (IAM policies attached to that user or role)
* `AccessDenied` → you're authenticated but not authorized | `No valid credential sources found` → not authenticated at all
* Credentials never go in `.tf` files → the code is committed to Git, and leaked keys get abused within minutes

## Authentication methods

* AWS CLI config → `aws configure`, writes `~/.aws/credentials` (keys) and `~/.aws/config` (region, output)
* Environment variables → `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`
* Named profiles → `aws configure --profile dev`, then `export AWS_PROFILE=dev` or `profile = "dev"` in the provider block
* SSO (IAM Identity Center) → `aws configure sso` then `aws sso login`, short-lived credentials, no keys on disk
* IAM role → EC2 instance profile, ECS task role, or OIDC from GitHub Actions; credentials are issued automatically and rotate

## Which credentials win

The AWS provider checks these in order and uses the first one it finds (simplified):

1. Arguments in the `provider "aws"` block (`profile`, `assume_role`) → don't put keys here
2. Environment variables → `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`, or `AWS_PROFILE`
3. Shared files → `~/.aws/credentials` and `~/.aws/config`, `default` profile if none is named
4. Container or instance role → ECS task role, EC2 instance profile

* Gotcha → a stale `AWS_ACCESS_KEY_ID` exported in the shell overrides the profile you think you're using
* `aws sts get-caller-identity` → shows exactly which account and user/role the current credentials belong to; run it before any `apply`

## Region

* Set in the provider block → `region = "us-east-1"`
* If missing, the provider falls back to `AWS_REGION` or the profile's region in `~/.aws/config`
* Always set it explicitly → otherwise the same code deploys to different regions on different machines
* Resources not showing in the console → the console is in a different region; switch it at the top right

## Setup on Ubuntu

```bash
uname -m      # x86_64 or aarch64
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
aws --version

aws configure                 # access key, secret, default region, output format
aws sts get-caller-identity   # confirm who you are
```

* ARM machines → `awscli-exe-linux-aarch64.zip`
* Use an IAM user or SSO, never the root account's keys
* Least privilege → give the Terraform user only what it needs; `AdministratorAccess` is fine for a personal lab, not for real work

## S3 basics

* S3 → object storage: files (objects) stored in containers (buckets), accessed over HTTPS
* Object → data + metadata, addressed by a key like `dev/terraform.tfstate`; the `/` is part of the name, S3 has no real folders
* Durability → 11 nines (99.999999999%), data is copied across multiple AZs
* Uses → static files, backups, logs, data lakes, Terraform state
* Buckets live in one region → but the S3 console lists buckets from every region (check the AWS Region column)
* S3 is not inside a VPC → it's a regional service reached over the internet or a VPC endpoint

## Bucket naming rules

* Globally unique across all AWS accounts, everywhere → `test-bucket` is already taken by someone
* 3–63 characters, lowercase letters, numbers, `-` and `.` only
* Must start and end with a letter or number, no `_`, no uppercase, not formatted like an IP address
* Name can't be changed → rename = create a new bucket and copy the data
* Tip → add something unique: initials, account alias, a random suffix

## S3 bucket in Terraform

```hcl
resource "aws_s3_bucket" "first_bucket" {
  bucket = "my-tf-test-bucket-ap14"

  tags = {
    Name        = "Demo"
    Environment = "Dev"
  }
}
```

* `aws_s3_bucket` → only creates the bucket and its tags
* Settings are separate resources (provider v4+) → versioning, encryption, public access, lifecycle each get their own block pointing at the bucket

```hcl
resource "aws_s3_bucket_versioning" "first_bucket" {
  bucket = aws_s3_bucket.first_bucket.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_public_access_block" "first_bucket" {
  bucket                  = aws_s3_bucket.first_bucket.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
```

* Encryption → S3 encrypts every new object with SSE-S3 (AES-256) by default since 2023; add `aws_s3_bucket_server_side_encryption_configuration` only to switch to KMS
* `force_destroy = true` → `destroy` deletes the bucket even if it has objects; fine in labs, never on real data
* Without it → `BucketNotEmpty` error on destroy

## Lab: VPC and S3 with an implicit dependency

Task → provision a VPC and an S3 bucket, and make the bucket depend on the VPC without `depends_on`.

```hcl
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"
}

resource "aws_s3_bucket" "first_bucket" {
  bucket = "my-tf-test-bucket-ap14"

  tags = {
    Name        = "Demo"
    Environment = "Dev"
    Vpcid       = aws_vpc.my_vpc.id
  }
}

resource "aws_vpc" "my_vpc" {
  cidr_block = "10.0.0.0/16"

  tags = {
    Name = "tf-day3-vpc"
  }
}
```

* A bucket has no real link to a VPC → the dependency is created by using `aws_vpc.my_vpc.id` in the bucket's tags
* The VPC ID only exists after AWS creates the VPC → plan shows the tag as `(known after apply)`, and apply builds the VPC first
* The bucket is written above the VPC and it still works → Terraform reads every `.tf` file, builds a dependency graph, and ignores the order of blocks
* `destroy` reverses the graph → bucket first, then VPC
* Verify in the console → VPC → Your VPCs (`tf-day3-vpc`), S3 → bucket → Properties → Tags (`Vpcid`)

| Symptom | Cause | Fix |
|---|---|---|
| Resources missing in the console | Console set to another region | Switch region, or check `terraform state show` for the ARN |
| No `provider` block, still deployed | Region came from `~/.aws/config` | Always set `region` in the provider block |
| `BucketAlreadyExists` | Name taken by another account | Make the name unique |
| `BucketNotEmpty` on destroy | Objects still in the bucket | Empty it, or `force_destroy = true` in labs |
| `Reference to undeclared resource` | Typo in a reference | Match `type.name` exactly |
| `Cycle:` error | Two resources reference each other | Remove one of the references |

## Implicit vs explicit dependency

* Implicit → one resource references another's attribute; Terraform orders them automatically, preferred
* Explicit → `depends_on = [aws_vpc.my_vpc]`, only when the dependency is real but nothing is referenced
* No dependency at all → resources are created in parallel
* `terraform graph` → prints the dependency graph in DOT format

!!! tip "Quick revision"

    * `aws sts get-caller-identity` before every apply
    * Credentials → env vars, profile, SSO or role; never in code
    * Bucket names → globally unique, lowercase, 3–63 chars
    * Reference = implicit dependency, block order doesn't matter

!!! question "Interview points"

    * How does Terraform authenticate to AWS? → the provider uses the standard AWS credential chain: provider config, env vars, shared credentials/config files, then instance or container roles
    * Authentication vs authorization? → authentication proves identity (keys, SSO, role); authorization is what IAM policies allow that identity to do
    * Why not hardcode access keys in the provider block? → they end up in Git; use profiles, SSO or roles, and OIDC in CI
    * How do you check which AWS account Terraform will use? → `aws sts get-caller-identity`
    * Why must S3 bucket names be globally unique? → buckets share one global namespace and are addressed by DNS names like `bucket.s3.amazonaws.com`
    * Why are versioning and encryption separate resources from `aws_s3_bucket`? → since AWS provider v4 each bucket setting is its own resource, so it can be managed independently
    * How do you create a dependency between two resources? → reference an attribute of one in the other (implicit); use `depends_on` only for hidden dependencies
    * Does the order of resource blocks matter? → no, Terraform builds a dependency graph from references
    * Is an S3 bucket inside a VPC? → no, S3 is a regional service; a VPC reaches it over the internet or through a VPC endpoint
