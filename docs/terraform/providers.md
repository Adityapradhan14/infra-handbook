# Providers & Versioning

*Hands-on notes, Terraform course day 2*

## What is a provider

* Provider → a plugin that lets Terraform talk to an external API (AWS, Azure, GCP, Kubernetes, GitHub, Cloudflare, Datadog)
* Terraform core only knows HCL, state and the dependency graph → it has no idea how to create an EC2 instance; the AWS provider turns your resource blocks into AWS API calls
* Each provider defines its own resource types and data sources → `aws_instance`, `aws_vpc`, `github_repository`
* Separate binary → downloaded by `terraform init`, not bundled with Terraform
* Not only clouds → `random`, `local`, `tls`, `http`, `null` are utility providers

## Where providers come from

* Terraform Registry → `registry.terraform.io`, the default source
* Official → maintained by HashiCorp (`hashicorp/aws`, `hashicorp/random`)
* Partner → maintained by the vendor, verified by HashiCorp (`cloudflare/cloudflare`, `datadog/datadog`)
* Community → maintained by individuals, check activity and stars before trusting one
* Source address → `[hostname/]namespace/type`, e.g. `hashicorp/aws` = `registry.terraform.io/hashicorp/aws`

## Reading the provider docs

* Registry → AWS provider → Documentation → search a resource like `aws_vpc`
* Example Usage → copy-paste starting point
* Argument Reference → what you can set; each argument is marked required or optional
* Attribute Reference → what the resource exposes after creation (`id`, `arn`), used in references
* Import → how to bring an existing resource under Terraform

## Core version vs provider version

* Terraform core → the `terraform` binary (e.g. `1.9.x`), parses config, manages state, builds the plan
* Provider → one plugin per platform (e.g. AWS `6.x`), its own release cycle, much more frequent than core
* Pin core → `required_version` | pin providers → `required_providers`
* `terraform version` → shows core and every installed provider

## Configuration

```hcl
terraform {
  required_version = ">= 1.5.0"

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
```

* `terraform {}` → settings for Terraform itself, not for any cloud
* `required_providers` → which plugins this project needs
* `aws =` → local name, used in `provider "aws"` and matched to resource prefixes (`aws_`)
* `source` → where to download it from
* `version` → which versions are acceptable
* `provider "aws" {}` → how to configure it: region, default tags, assume role
* `terraform {}` decides what to download (used by `init`) | `provider {}` is used at `plan` / `apply`

## Credentials

* Never in the `.tf` file → it's committed to Git
* The AWS provider looks for credentials in this order (simplified):
    1. Env vars → `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_PROFILE`
    2. Shared files → `~/.aws/credentials`, `~/.aws/config` (from `aws configure`)
    3. IAM role → EC2 instance profile, ECS task role, or OIDC in CI
* Best practice → short-lived credentials: SSO locally, OIDC role in GitHub Actions, no long-lived access keys

## Why pin versions

* Compatibility → a provider version needs a minimum core version
* Stability → major versions (`5.x` → `6.x`) contain breaking changes: renamed arguments, removed resources
* Reproducibility → same versions on my laptop, a teammate's laptop and CI
* Features → new AWS services only appear in newer provider versions
* Fixes → bug and security fixes come in minor and patch releases
* Unpinned → `init` on a new machine silently pulls the latest major, and a plan that worked yesterday breaks today

## Version constraints

* `= 1.2.3` (or just `1.2.3`) → exactly this version
* `!= 1.2.3` → anything except this one (to skip a known-bad release)
* `>= 1.2` / `> 1.2` / `<= 1.2` / `< 1.2` → bounds
* `>= 1.2, < 2.0` → range, commas mean AND
* `~>` → pessimistic constraint: only the rightmost number you wrote can go up, everything left of it is locked

| Constraint | Means | Allows | Blocks |
|---|---|---|---|
| `~> 6.1.1` | `>= 6.1.1, < 6.2.0` | 6.1.2, 6.1.9 | 6.2.0, 7.0 |
| `~> 6.1` | `>= 6.1, < 7.0` | 6.2, 6.50 | 7.0 |
| `~> 6.0` | `>= 6.0, < 7.0` | any 6.x | 7.0 |

* `~>` never goes below what you wrote → `~> 6.1.1` won't pick 6.1.0
* Common choice → `~> 6.0` for providers (all of 6.x, no surprise major upgrade)

## Lock file

* `terraform init` → picks the newest version matching the constraint, downloads it into `.terraform/`, writes the exact version and checksums to `.terraform.lock.hcl`
* Next `init` → uses the locked version, even if a newer one matching the constraint exists
* `terraform init -upgrade` → ignore the lock, take the newest allowed version, rewrite the lock
* Commit `.terraform.lock.hcl` → everyone and CI get the same provider build | don't commit `.terraform/` (binaries, hundreds of MB)
* `terraform providers lock -platform=linux_amd64 -platform=darwin_arm64` → record checksums for other OSes, so a Mac teammate and a Linux CI runner both pass verification
* Constraint vs lock → constraint is the allowed range, lock is the exact version chosen inside it

## Multiple providers and aliases

```hcl
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}

provider "aws" {
  region = "us-east-1"            # default
}

provider "aws" {
  alias  = "mumbai"
  region = "ap-south-1"
}

resource "aws_s3_bucket" "backup" {
  provider = aws.mumbai
  bucket   = "my-backup-bucket"
}
```

* A provider block without `alias` → the default for every `aws_` resource
* `alias` → a second configuration of the same provider, picked with `provider = aws.<alias>`
* Use cases → multi-region (DR copies), multi-account (assume role into another account)

## Lab: first script

```hcl
# providers.tf
terraform {
  required_version = ">= 1.5.0"
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

# main.tf
resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"

  tags = {
    Name = "tf-lab-vpc"
  }
}

resource "aws_subnet" "public" {
  vpc_id     = aws_vpc.main.id
  cidr_block = "10.0.1.0/24"

  tags = {
    Name = "tf-lab-public"
  }
}
```

1. `terraform init` → downloads the AWS provider, creates `.terraform/` and `.terraform.lock.hcl`
2. `terraform fmt` and `terraform validate`
3. `terraform plan` → `Plan: 2 to add, 0 to change, 0 to destroy.`
4. `terraform apply` → VPC first, then the subnet, because the subnet references `aws_vpc.main.id`
5. `terraform destroy` → removes both, subnet first

* `vpc_id = aws_vpc.main.id` → internal reference: the VPC ID isn't known until AWS creates it, so it shows as `(known after apply)` in the plan
* Optional arguments not set → provider defaults apply (e.g. `instance_tenancy = "default"`)

| Symptom | Cause | Fix |
|---|---|---|
| `Inconsistent dependency lock file` | Constraint changed after the lock was written | `terraform init -upgrade` |
| `No valid credential sources found` | No AWS credentials found | `aws configure` or export `AWS_PROFILE` |
| `Unsupported Terraform Core version` | Local `terraform` older than `required_version` | Upgrade Terraform |
| `Could not load plugin` / provider not found | Skipped `init` or typo in `source` | Fix `source`, rerun `terraform init` |

!!! tip "Quick revision"

    * Provider = plugin that turns HCL into API calls, downloaded by `init`
    * `required_providers` → what to download, `provider {}` → how to configure it
    * `~>` → only the rightmost written number can increase
    * Commit `.terraform.lock.hcl`, never `.terraform/`

!!! question "Interview points"

    * What is a Terraform provider? → a plugin that implements resources and data sources for an API and translates HCL into API calls
    * Why pin provider versions? → major versions have breaking changes; pinning keeps plans reproducible across machines and CI
    * What does `~> 6.1` allow? → `>= 6.1, < 7.0`, any 6.x from 6.1 up
    * What does `~> 6.1.1` allow? → `>= 6.1.1, < 6.2.0`, patch releases only
    * What is `.terraform.lock.hcl`? → records the exact provider versions and checksums chosen by `init`; commit it so everyone uses the same build
    * Constraint vs lock file? → constraint is the allowed range, the lock is the exact version picked inside it; `init -upgrade` moves it
    * How do you deploy to two regions in one config? → a second `provider` block with `alias`, then `provider = aws.<alias>` on the resources
    * Where should AWS credentials come from? → env vars, an AWS profile or an IAM role / OIDC; never hardcoded in `.tf` files
    * Terraform core vs provider version? → core is the CLI binary pinned by `required_version`; providers are separate plugins pinned in `required_providers`, each with its own releases
