# IaC & Terraform

*Hands-on notes, Terraform course day 1*

## What is Infrastructure as Code

* IaC → defining and managing infrastructure (servers, databases, networks, load balancers) in code instead of clicking through a console and setting it up by hand
* The code is the source of truth → what's in Git is what should exist in the cloud
* Manual setup ("ClickOps") → slow, not repeatable, no history of who changed what, and dev/staging/prod slowly drift apart

## Why IaC

* Less manual effort → no repeating the same console clicks for every environment
* Repeatable and fast → same code gives the same infra every time, so new environments take minutes
* Version control → every change is a commit: reviewed in a PR, tracked, and reversible
* Consistency → dev, staging and prod come from the same code, so no "works in staging" surprises
* Scaling → 1 server to 10 is a one-number change (`count = 10`)
* Lower cost → fewer human errors, and unused environments can be torn down with one command
* Disaster recovery → if a region or account is lost, the code rebuilds it

## Types of IaC tools

| Type | Job | Tools |
|---|---|---|
| Provisioning | Create the infra (VPC, EC2, RDS, IAM) | Terraform, OpenTofu, Pulumi, CloudFormation |
| Configuration management | Install and configure software on existing machines | Ansible, Chef, Puppet |

* They're used together → Terraform creates the EC2 instance, Ansible installs nginx on it
* CloudFormation → AWS only | Terraform → any cloud or API

## Declarative vs imperative

* Imperative → you write the steps: "create a VPC, then a subnet, then an instance"
* Declarative → you write the end state: "there should be a VPC, a subnet and an instance"
* Terraform is declarative → it compares the desired state (your code) with the current state and works out the steps itself
* Idempotent → running `apply` twice with no code change does nothing the second time

## What is Terraform

* IaC tool by HashiCorp → define cloud infra in code, declaratively, with state tracking and multi-cloud support
* License → source-available (BSL) since August 2023, not open source anymore | OpenTofu → the open-source fork under the Linux Foundation, mostly drop-in compatible
* Written in Go, ships as a single `terraform` binary

## Core features

* HCL → HashiCorp Configuration Language, built for describing infra: human readable, machine friendly, declarative (see [HCL Syntax](hcl-syntax.md))
* Providers → plugins that connect Terraform to AWS, Azure, GCP, Kubernetes, GitHub, Cloudflare and thousands more (see [Providers & Versioning](providers.md))
* State → `terraform.tfstate` records what Terraform manages and maps each resource in code to a real object (e.g. `aws_vpc.main` → `vpc-0abc...`)
* Plan → a preview before anything changes
* Dependency graph → Terraform works out what depends on what and creates things in the right order, in parallel where it can
* Same workflow for every platform → learn it once, use it everywhere

## Reading a plan

* `+` → create
* `~` → update in place
* `-` → destroy
* `-/+` → destroy and recreate (replacement), usually because an argument that can't change in place was modified, like an instance's AMI
* Summary line → `Plan: 2 to add, 1 to change, 0 to destroy.`
* Always read `-/+` lines carefully → a replaced database loses its data

## State file

* `terraform.tfstate` → JSON, created after the first `apply`
* Can contain secrets in plain text (DB passwords, keys) → never commit it, add `*.tfstate*` to `.gitignore`
* Teams keep it in a remote backend (S3 + locking) so everyone works from the same state
* Drift → someone changes a resource in the console, so real infra no longer matches state; the next `plan` shows it

## Workflow

1. Write → HCL code in `.tf` files
2. `terraform init` → download providers, set up the backend and the `.terraform/` directory
3. `terraform fmt` → format the code
4. `terraform validate` → check syntax and internal consistency, catch mistakes early (no cloud calls)
5. `terraform plan` → preview what will change
6. `terraform apply` → create or modify the resources (shows the plan again and asks for `yes`)
7. `terraform destroy` → remove everything this config manages

```bash
terraform init
terraform fmt
terraform validate
terraform plan
terraform apply
terraform destroy
```

* `terraform plan -out=tfplan` then `terraform apply tfplan` → applies exactly what you reviewed, the standard in CI
* `-auto-approve` → skip the `yes` prompt; fine in CI, risky by hand

## Project files

* `main.tf` → resources
* `providers.tf` or `versions.tf` → `terraform {}` and `provider {}` blocks
* `variables.tf` → inputs | `outputs.tf` → outputs | `terraform.tfvars` → values for the inputs
* Terraform loads every `.tf` file in the folder → file names are just for humans
* Commit → `.tf` files, `.terraform.lock.hcl` | Don't commit → `.terraform/`, `*.tfstate*`, `*.tfvars` with secrets

!!! tip "Quick revision"

    * IaC = infra in code, Terraform = declarative provisioning tool
    * `init` → `fmt` → `validate` → `plan` → `apply` → `destroy`
    * Plan symbols → `+` create, `~` update, `-` destroy, `-/+` replace
    * State maps code to real resources, never commit it

!!! question "Interview points"

    * What is IaC and why use it? → managing infra through versioned code instead of manual setup; repeatable, reviewable, consistent across environments
    * Terraform vs Ansible? → Terraform provisions infrastructure (declarative, stateful), Ansible configures software on machines (procedural, agentless); commonly used together
    * Declarative vs imperative? → declarative describes the end state and the tool works out the steps; imperative lists the steps
    * What is the Terraform state file? → JSON mapping of resources in code to real objects; used to calculate diffs; may contain secrets, so store it remotely and encrypted
    * What does `terraform plan` do? → compares code with state and real infra, shows what would be created, changed or destroyed without changing anything
    * What does `-/+` in a plan mean? → the resource will be destroyed and recreated, so check it for data loss
    * Is Terraform open source? → not since 2023 (BSL licence); OpenTofu is the open-source fork
    * What is drift? → real infra changed outside Terraform; `plan` detects it and `apply` brings it back to the code
