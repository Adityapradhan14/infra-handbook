# Variables, Locals & Outputs

*Hands-on notes, Terraform course day 5*

## Two ways to classify variables

* Based on purpose → input (`variable`), local (`locals`), output (`output`)
* Based on value → type constraints: primitive, complex, `any`

## Based on purpose

| | Block | Set from outside | Used as | Like |
|---|---|---|---|---|
| Input | `variable` | Yes | `var.x` | function parameter |
| Local | `locals` | No | `local.x` | variable inside a function |
| Output | `output` | No, read from outside | `terraform output x` | return value |

* Input → a value coming into the code; same code, different values per run or environment
* Local → a value the code computes itself, once, and reuses
* Output → a value going out after `apply`, for humans, scripts and other configs

## Input variables

```hcl
variable "environment" {
  type        = string
  default     = "dev"
  description = "Environment name, used in names and tags"
}

provider "aws" {
  region = var.aws_region
}
```

* `type` → what kind of value is allowed; a wrong type fails before anything touches AWS
* `default` → the fallback, used only when nothing else gives a value; makes the variable optional
* No `default` → required, Terraform asks for it in the terminal (`Enter a value:`)
* `description` → shown in prompts and docs, always write one
* `sensitive = true` → hidden in plan output, still stored in plain text in state
* `validation { }` → custom rules, e.g. only allow `dev`, `stage`, `prod`
* `default` must be a fixed value → no `var.x`, no resource attributes, no functions
* The code never changes between environments → `default = "dev"` stays in the file, the value is decided when Terraform runs

## Type constraints

Primitive → a single value

```hcl
variable "name"    { type = string }   # "web"
variable "port"    { type = number }   # 8080
variable "enabled" { type = bool }     # true
```

Complex → a collection

```hcl
variable "azs"    { type = list(string) }                         # ["us-east-1a", "us-east-1b"]
variable "users"  { type = set(string) }                          # ["alice", "bob"]
variable "tags"   { type = map(string) }                          # { env = "dev", team = "ops" }
variable "server" { type = object({ name = string, port = number }) }
variable "pair"   { type = tuple([string, number]) }              # ["web", 80]
```

* list → ordered, duplicates allowed, all items the same type, any length
* set → unordered, no duplicates
* map → any keys, every value the same type
* object → fixed keys, each with its own type
* tuple → fixed length, a type per position
* list vs tuple → same type and any length vs fixed length with a type per position
* map vs object → any keys with one value type vs fixed keys with their own types
* `any` → no type check, also what you get without `type`; convenient but loses safety
* `null` → not a type but a value meaning "not set"; an argument set to `null` is the same as leaving it out, so the provider default applies

## Locals

* A local is a nickname for a value → write it once, use it everywhere
* Use it for values that are repeated or built from other values

```hcl
locals {
  prefix = "${var.environment}-ap14"
}
```

* `local.prefix` → `"dev-ap14"`
* Defined in `locals` (plural), referenced as `local.` (singular)
* Can use anything → variables, other locals, resource attributes, functions, conditions
* Can't be set from outside → `-var` and tfvars have no effect on it
* No `type` argument → the type is inferred from the value
* Check a local without creating anything →

```bash
terraform console
> local.prefix
"dev-ap14"
> exit
terraform console -var="environment=prod"
> local.prefix
"prod-ap14"
```

## Variable vs local

| | `variable` | `locals` |
|---|---|---|
| Who sets the value | Whoever runs Terraform | Only the code |
| Changes per run without editing code | Yes | No |
| Expressions and references | No, `default` is a fixed value | Yes |
| Type check | `type = ...` | Inferred |
| Used as | `var.x` | `local.x` |

* The value should differ between runs or environments (region, env, instance size) → variable
* The value is derived from other values or repeated in many places (name prefix, common tags) → local
* Restaurant version → variable = the order form the customer fills in, local = the kitchen's own recipe

## Locals in real projects

* Common tags → every resource gets identical `Project`, `Environment`, `Owner`, `ManagedBy` tags for cost reports and ownership
* Naming convention → one `name_prefix` like `${var.project}-${var.env}`, nobody types names by hand
* Environment-based values → `instance_type = var.environment == "prod" ? "t3.small" : "t3.micro"`
* Calculations once → `subnet_cidrs = [for i in range(3) : cidrsubnet(var.vpc_cidr, 8, i)]`
* Shortening long expressions → `account_id = data.aws_caller_identity.current.account_id`
* Don't overdo it → a local used once, or locals chained five deep, make code harder to read

## Repeated tags: the problem locals solve

Without a local → the same tags typed on every resource; adding `Owner` means editing every block and missing one.

```hcl
locals {
  tags = {
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

resource "aws_s3_bucket" "first_bucket" {
  bucket = local.bucket
  tags   = local.tags
}
```

* One change in `locals` → every resource using `local.tags` follows
* `tags = local.tags` alone → the resource gets only the shared tags and loses its own `Name`

## merge

* `merge(map1, map2, ...)` → joins maps into one map
* `tags` takes one map, and a resource needs the shared tags plus its own `Name` → `tags` can't be written twice, so the maps are merged

```hcl
tags = merge(local.tags, {
  Name  = "${local.prefix}-demo-bucket"
  Vpcid = aws_vpc.my_vpc.id
})
```

* Read it as "the shared tags, plus these for this resource"
* Same key in both maps → the later map wins → `merge({ env = "dev" }, { env = "prod" })` gives `{ env = "prod" }`
* Try it → `terraform console`, then `merge({a = 1}, {b = 2})`
* Dropping `Vpcid = aws_vpc.my_vpc.id` from the tags also drops the implicit dependency on the VPC

## Conditional expression

* `condition ? value_if_true : value_if_false`
* `var.environment == "prod" ? "t3.small" : "t3.micro"` → prod gets `t3.small`, everything else `t3.micro`

## Ways to set a variable (precedence)

Lowest to highest priority; a later source overrides an earlier one.

1. `default` in the `variable` block
2. Environment variable → `export TF_VAR_environment=stage`
3. `terraform.tfvars` → loaded automatically
4. `terraform.tfvars.json` → loaded automatically, after `terraform.tfvars`
5. `*.auto.tfvars` / `*.auto.tfvars.json` → loaded automatically, in alphabetical order
6. `-var="environment=prod"` and `-var-file="prod.tfvars"` on the command line → the last one given wins

* No value from anywhere and no `default` → Terraform prompts for it
* Memory trick → the closer the value is to the moment you run the command, the stronger it is
* `prod.tfvars` / `dev.tfvars` → not loaded automatically, only with `-var-file`; this is how teams keep one file per environment

```hcl
# terraform.tfvars  (plain name = value lines, no variable block)
environment = "demo"
bucket_name = "terraform-demo-bucket"
```

## TF_VAR_ environment variables

```bash
export TF_VAR_environment=stage
echo $TF_VAR_environment
terraform console          # > var.environment → "stage"
unset TF_VAR_environment
terraform console          # > var.environment → "dev"
```

* Terraform reads any shell variable named `TF_VAR_<name>` as the value of `variable "<name>"`; the name is case-sensitive
* `export` → makes it visible to programs run from this terminal; it lasts until the terminal closes or `unset`
* Don't put it in `~/.bashrc` → you forget it's set and deploy the wrong environment
* Used for → CI jobs setting values per environment, and secrets like `TF_VAR_db_password` kept out of files and Git
* Weaker than tfvars files → with `terraform.tfvars` setting `environment = "demo"`, `TF_VAR_environment` has no effect

## Outputs

```hcl
output "bucket_name" {
  description = "Name of the S3 bucket"
  value       = aws_s3_bucket.first_bucket.bucket
}

output "environment" {
  value = var.environment
}

output "tags" {
  value = local.tags
}
```

* Printed at the end of every `apply`, stored in state
* Can show a resource attribute, an input, or a local → handy to check what a local computed
* `terraform output` → all outputs, any time after apply
* `terraform output bucket_name` → one output
* `terraform output -raw bucket_name` → bare value without quotes, for scripts → `aws s3 ls s3://$(terraform output -raw bucket_name)`
* `terraform output -json` → everything as JSON, for scripts and CI
* `sensitive = true` → shown as `(sensitive value)` in the CLI, still in state
* Other configs and modules read outputs → that's how one stack passes a VPC ID to another

## Unique names with random_string

```hcl
resource "random_string" "suffix" {
  length  = 6
  special = false
  upper   = false
}

locals {
  full_bucket_name = "${var.environment}-${var.bucket_name}-${random_string.suffix.result}"
}
```

* From the `random` provider (`hashicorp/random`) → creates nothing in AWS, only generates values; add it to `required_providers` and run `terraform init`
* `special = false`, `upper = false` → S3 names allow only lowercase letters, numbers and `-`
* Generated once and stored in state → it doesn't change on every run
* Solves globally unique bucket names without hand-made suffixes

## File layout

```
provider.tf       → terraform {} and provider {}
variables.tf      → input variables
locals.tf         → locals
main.tf           → resources
output.tf         → outputs
terraform.tfvars  → values for the variables
```

* Terraform loads every `.tf` file in the folder as one config → the split is only for humans, like block order
* Standard layout in real repos

## Lab: refactoring the day 4 config

```hcl
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }

  backend "s3" {
    bucket       = "your-terraform-state-bucket"
    key          = "dev/terraform.tfstate"
    region       = "us-east-1"
    encrypt      = true
    use_lockfile = true
  }
}

provider "aws" {
  region = var.aws_region
}

variable "aws_region" {
  type        = string
  default     = "us-east-1"
  description = "AWS region to deploy into"
}

variable "environment" {
  type        = string
  default     = "dev"
  description = "Environment name, used in names and tags"
}

locals {
  prefix   = "${var.environment}-ap14"
  bucket   = "${var.environment}-bucket-${var.aws_region}-ap14"
  name_vpc = "${var.environment}-second-vpc"

  tags = {
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

resource "aws_vpc" "my_vpc" {
  cidr_block = "10.0.0.0/16"

  tags = merge(local.tags, {
    Name = "${local.prefix}-my-vpc"
  })
}

resource "aws_vpc" "second_vpc" {
  cidr_block = "10.1.0.0/16"

  tags = merge(local.tags, {
    Name = local.name_vpc
  })
}

resource "aws_instance" "my_instance" {
  ami           = "ami-xxxxxxxxxxxxxxxxx"
  instance_type = "t3.micro"

  tags = merge(local.tags, {
    Name = "${local.prefix}-my-demo"
  })
}

resource "aws_s3_bucket" "first_bucket" {
  bucket = local.bucket

  tags = merge(local.tags, {
    Name  = local.bucket
    Vpcid = aws_vpc.my_vpc.id
  })
}

resource "aws_s3_bucket_versioning" "first_bucket" {
  bucket = aws_s3_bucket.first_bucket.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "first_bucket" {
  bucket = aws_s3_bucket.first_bucket.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
    bucket_key_enabled = true
  }
}
```

1. `terraform fmt` and `terraform validate`
2. `terraform plan` → names like `dev-ap14-my-vpc`, `dev-bucket-us-east-1-ap14`
3. `terraform plan -var="environment=prod"` → every name and tag switches to `prod`, no code edited
4. `terraform destroy` when done → the EC2 instance costs money while running

| Symptom | Cause | Fix |
|---|---|---|
| `Blocks of type "provider" are not expected here` | `provider` block placed inside `terraform {}` | Move it to the top level |
| Variable declared but changes nothing | `aws_region` not used in the provider | `region = var.aws_region` |
| Bucket named for one region, created in another | Name uses `var.aws_region`, provider is hardcoded | Use the variable in both |
| `Environment = dev` on a prod resource | Tag hardcoded instead of `var.environment` | Take every tag from `local.tags` |
| `dev-bucketus-east-1-ap14` | Missing `-` in the interpolation | Check with `terraform console` → `local.bucket` |
| Plan shows `-/+` on the bucket | Bucket name changed, S3 can't rename | Expected for a lab bucket; fails with `BucketNotEmpty` if it has objects |
| Plan wants to destroy a VPC you didn't touch | Its block was removed but it's still in state (e.g. an imported one) | Put the block back, or `terraform state rm` it |
| EC2 instance not in your VPC | No `subnet_id`, so it lands in the default VPC | Add a subnet in your VPC and set `subnet_id` |
| AMI not found after changing region | AMI IDs are region-specific | Look it up with a `data "aws_ami"` source |
| `VpcLimitExceeded` | Default limit of 5 VPCs per region, default VPC included | Destroy unused VPCs |
| Empty `locals {}` | Valid but useless | Remove it or put repeated values in it |

* Two VPCs with the same CIDR → AWS allows it, but overlapping VPCs can never be peered; give each its own range
* Switching `environment` with one fixed backend `key` → not a separate environment; it renames the dev resources and replaces the bucket in the same state. Separate environments need separate state (different `key`, or workspaces)

!!! tip "Quick revision"

    * Input = `var.x` from outside, local = `local.x` computed inside, output = printed after apply
    * Precedence → default < `TF_VAR_` < `terraform.tfvars` < `.tfvars.json` < `*.auto.tfvars` < `-var` / `-var-file`
    * `merge(local.tags, { Name = ... })` → shared tags plus the resource's own
    * `terraform console` → test any variable, local or function without touching AWS
    * One state per environment, not one variable per environment

!!! question "Interview points"

    * Variable vs local? → a variable is an input set from outside per run; a local is a value computed inside the module and can't be overridden
    * Why can't a variable's default use another variable? → defaults must be fixed values; computed values belong in locals
    * What is the variable precedence order? → default, then `TF_VAR_` env vars, `terraform.tfvars`, `terraform.tfvars.json`, `*.auto.tfvars` in alphabetical order, and `-var` / `-var-file` on the command line last and strongest
    * `terraform.tfvars` vs `prod.tfvars`? → `terraform.tfvars` and `*.auto.tfvars` load automatically; any other name loads only with `-var-file`
    * How do you pass secrets to Terraform? → `TF_VAR_` env vars or a secrets manager, mark the variable `sensitive = true`; the value still lands in state, so the state must be protected
    * How do you enforce common tags on all resources? → a `common_tags` local merged into each resource's tags with `merge()`, or the AWS provider's `default_tags` block
    * list vs set vs tuple? → list is ordered with duplicates, set is unordered and unique, tuple has a fixed length with a type per position
    * map vs object? → map has any keys with one value type; object has fixed keys with their own types
    * What are outputs used for? → showing values after apply, feeding scripts via `-raw` / `-json`, and passing values between modules and stacks
    * Does `sensitive = true` hide a value from state? → no, only from CLI output
    * How do you get unique S3 bucket names? → add a suffix from `random_string` (stored in state so it stays stable) or include account and region in the name
    * Is changing a variable enough to create a separate prod environment? → no, with the same backend key it modifies the same resources; prod needs its own state
