# HCL Syntax

*Hands-on notes, Terraform course day 2*

## The three building blocks

* Block → a container with a type, optional labels, and a body in `{ }`
* Argument → `name = value` inside a block
* Expression → the value side: a literal, a reference, a function call, a condition

```hcl
<BLOCK TYPE> "<LABEL 1>" "<LABEL 2>" {
  <ARGUMENT> = <EXPRESSION>

  <NESTED BLOCK> {
    <ARGUMENT> = <EXPRESSION>
  }
}
```

* Arguments use `=` | nested blocks don't → `lifecycle { ... }`, not `lifecycle = { ... }`
* Labels are always quoted → `resource aws_vpc main` is invalid

## Block types and labels

| Block | Labels | Example | Purpose |
|---|---|---|---|
| `terraform` | 0 | `terraform { ... }` | Settings: versions, providers, backend |
| `provider` | 1 | `provider "aws" { ... }` | Configure a provider |
| `resource` | 2 | `resource "aws_vpc" "main" { ... }` | Something Terraform creates and manages |
| `data` | 2 | `data "aws_ami" "ubuntu" { ... }` | Read something that already exists |
| `variable` | 1 | `variable "region" { ... }` | Input |
| `output` | 1 | `output "vpc_id" { ... }` | Value printed after apply, readable by other modules |
| `locals` | 0 | `locals { ... }` | Named internal values |
| `module` | 1 | `module "network" { ... }` | Reuse another folder of `.tf` code |

## Resource block

```hcl
resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"

  tags = {
    Name = "main-vpc"
  }
}
```

* `aws_vpc` → resource type, the `aws_` prefix tells Terraform which provider owns it
* `main` → local name, only meaningful inside your code
* Address → `aws_vpc.main`, must be unique in the module
* `tags = { ... }` → a map argument, so it takes `=`

## References

* Resource attribute → `<TYPE>.<NAME>.<ATTRIBUTE>` → `aws_vpc.main.id`
* Variable → `var.region`
* Local → `local.name_prefix` (the block is `locals`, the reference is singular `local`)
* Data source → `data.aws_ami.ubuntu.id`
* Module output → `module.network.vpc_id`
* A reference creates an implicit dependency → Terraform builds the referenced resource first

```hcl
resource "aws_subnet" "public" {
  vpc_id     = aws_vpc.main.id    # VPC is created first
  cidr_block = "10.0.1.0/24"
}
```

* Arguments vs attributes → arguments are what you set (`cidr_block`), attributes are what the resource exposes after creation (`id`, `arn`); both are listed on the registry docs page

## Variables, locals, outputs

```hcl
variable "region" {
  type        = string
  default     = "us-east-1"
  description = "AWS region"
}

locals {
  name_prefix = "dev-${var.region}"
}

output "vpc_id" {
  value = aws_vpc.main.id
}
```

* Variable without `default` → required, Terraform asks for it
* Setting variables (highest priority first) → `-var` / `-var-file` on the CLI → `*.auto.tfvars` → `terraform.tfvars` → `TF_VAR_region` env var → `default`
* `sensitive = true` → hides the value in plan output (still stored in state)
* `validation { }` block → custom rules, e.g. only allow certain instance types

## Data sources

```hcl
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"]   # Canonical's public account

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"]
  }
}
```

* Reads, never creates → used to look up AMIs, existing VPCs, the current account ID
* Used as → `data.aws_ami.ubuntu.id`

## Types

```hcl
name    = "web"                        # string
port    = 8080                         # number
enabled = true                         # bool
azs     = ["us-east-1a", "us-east-1b"] # list
tags    = { env = "dev", team = "ops" } # map
```

* Strings → double quotes only
* Type constraints for variables → `string`, `number`, `bool`, `list(string)`, `map(string)`, `set(string)`, `object({ name = string, port = number })`
* Multi-line string → heredoc

```hcl
user_data = <<-EOT
  #!/bin/bash
  apt-get update -y
EOT
```

## Expressions

* Interpolation → `"${var.env}-web"`, only inside strings; a bare reference is just `var.env`
* Conditional → `var.env == "prod" ? "m5.large" : "t3.micro"`
* Index / key → `var.azs[0]`, `var.tags["env"]`
* Functions → `upper("abc")`, `length(var.azs)`, `join("-", ["a", "b"])`, `lookup(var.amis, var.region)`, `cidrsubnet("10.0.0.0/16", 8, 1)` → `10.0.1.0/24`
* `for` expression → `[for az in var.azs : upper(az)]`
* Splat → `aws_instance.web[*].id` → list of all IDs
* Try functions live in the console → `terraform console`, then type `cidrsubnet("10.0.0.0/16", 8, 1)`

## Meta-arguments

Work on any resource, regardless of provider.

```hcl
resource "aws_instance" "web" {
  count         = 3
  ami           = data.aws_ami.ubuntu.id
  instance_type = "t3.micro"

  tags = {
    Name = "web-${count.index}"
  }

  depends_on = [aws_vpc.main]

  lifecycle {
    create_before_destroy = true
  }
}
```

* `count` → N copies, `count.index` is 0, 1, 2 | addresses → `aws_instance.web[0]`
* `for_each` → one copy per item of a map or set, `each.key` / `each.value` | addresses → `aws_s3_bucket.b["logs"]`
* `count` vs `for_each` → removing an item from the middle of a `count` list shifts every index after it and recreates those resources; `for_each` keys stay stable, so prefer it for named things
* `depends_on` → explicit dependency, only when there is no reference to create one
* `provider` → use an aliased provider, e.g. `provider = aws.mumbai`
* `lifecycle` → `create_before_destroy`, `prevent_destroy`, `ignore_changes = [tags]`

## Comments and formatting

* `#` or `//` → single line | `/* ... */` → multi-line
* Two-space indent, aligned `=` → `terraform fmt` does it, `terraform fmt -check` fails CI if code isn't formatted

## Common mistakes

| Mistake | Fix |
|---|---|
| `lifecycle = { ... }` | Nested blocks take no `=` |
| `resource aws_vpc main` | Labels must be quoted |
| `vpc_id = "${aws_vpc.main.id}"` | Just `aws_vpc.main.id` |
| `locals.name` | Reference is `local.name` |
| Single quotes `'web'` | HCL strings use double quotes |
| Same type + name twice | Addresses must be unique |

!!! tip "Quick revision"

    * Block → `type "label" "label" { }`, argument → `name = value`
    * `resource` and `data` take 2 labels, `provider` / `variable` / `output` / `module` take 1
    * Reference → `type.name.attribute`, `var.x`, `local.x`, `data.type.name.attr`
    * Prefer `for_each` over `count` for anything with a name

!!! question "Interview points"

    * Resource vs data source? → resource creates and manages infra; data source only reads existing infra
    * `count` vs `for_each`? → `count` indexes by number so removing a middle item recreates later ones; `for_each` keys by name so changes stay targeted
    * How does Terraform decide creation order? → builds a dependency graph from references; `depends_on` for hidden dependencies
    * When do you need `depends_on`? → when one resource relies on another without referencing any of its attributes, e.g. an app needing an IAM policy attached first
    * Variable precedence? → `-var` / `-var-file` > `*.auto.tfvars` > `terraform.tfvars` > `TF_VAR_` env vars > `default`
    * Does `sensitive = true` keep a value out of state? → no, only out of CLI output; state still has it in plain text
    * What does `create_before_destroy` do? → builds the replacement first, then deletes the old one, avoiding downtime
    * Variable vs local? → variable is an input set from outside; local is a computed value used inside the module
