# State & Remote Backend

*Hands-on notes, Terraform course day 4*

## How Terraform updates infrastructure

* Goal → keep the actual state of infra the same as the desired state in code
* Desired state → your `.tf` files | Recorded state → `terraform.tfstate` | Real state → what actually exists in AWS
* Every `plan` / `apply`:
    1. Read the code (desired)
    2. Read the state file (what Terraform thinks it manages)
    3. Refresh → ask AWS for the current real values
    4. Diff → only resources that differ are created, updated or destroyed
* Running `apply` again with no code change → `No changes`, so Terraform is idempotent

## The state file

* `terraform.tfstate` → JSON, written after every `apply`
* Maps each resource in code to a real object → `aws_vpc.my_vpc` ↔ `vpc-0abc...`
* Stores → every attribute (IDs, ARNs, tags, IPs), dependencies, provider info, and outputs
* `serial` → increases on every write | `lineage` → unique ID of this state's history, stops one state being written over another
* `terraform.tfstate.backup` → the previous version, kept by the local backend only

```json
{
  "version": 4,
  "terraform_version": "1.17.0",
  "serial": 1,
  "lineage": "140fd82e-...",
  "resources": [
    {
      "type": "aws_vpc",
      "name": "my_vpc",
      "instances": [
        { "attributes": { "id": "vpc-0abc...", "cidr_block": "10.0.0.0/16" } }
      ]
    }
  ]
}
```

## Why Terraform needs state

* Code says what should exist, AWS has what does exist → state is the link between the two
* Without it, Terraform can't tell whether `aws_vpc.my_vpc` already exists or which of 40 VPCs it owns
* Resource removed from code but still in state → Terraform destroys it
* Resource created by hand → not in state, Terraform ignores it until `terraform import`
* State lost → Terraform forgets it owns anything, next `apply` tries to create everything again (duplicates or `AlreadyExists` errors)
* Drift → someone changes infra in the console; `plan` shows the difference and `apply` puts it back to the code

## Problems with local state

* Lives on one laptop → laptop dies or folder is deleted, state is gone
* Team → everyone has a different copy, they overwrite each other
* CI → GitHub Actions can't read your laptop
* Secrets → DB passwords, keys and tokens are stored in plain text, even with `sensitive = true`; committing it to Git leaks them
* No locking → two `apply` runs at once can corrupt it

## Best practices

1. Never edit the state file by hand → use the `terraform state` commands
2. Store it remotely → S3, Terraform Cloud, GCS, Azure Blob
3. Enable locking → no concurrent writes
4. Enable versioning on the bucket → roll back to an older state if it gets corrupted
5. Separate state per environment → `dev/terraform.tfstate`, `prod/terraform.tfstate`, so a dev mistake can't touch prod
6. Restrict access → state contains secrets, only Terraform's role and admins should read it
7. Encrypt at rest and in transit → `encrypt = true`, HTTPS
8. Never commit it → `.gitignore` has `*.tfstate` and `*.tfstate.*`

## Remote backend with S3

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
```

* `backend "s3"` → goes inside the `terraform {}` block
* `bucket` → must already exist before `terraform init`
* `key` → path of the state object inside the bucket; one bucket can hold many states (`dev/`, `prod/`, `network/`)
* `region` → region of the state bucket, not where resources are deployed; that's the `provider` block, and the two can differ
* `encrypt = true` → server-side encryption of the state object
* `use_lockfile = true` → S3 native locking
* No variables allowed in the backend block → it's read before variables exist; `bucket = var.x` fails
* Any change to the backend block → rerun `terraform init`

## The state bucket

Create it outside this config, by hand or in a separate bootstrap config.

```bash
aws s3api create-bucket --bucket your-terraform-state-bucket --region us-east-1
aws s3api put-bucket-versioning --bucket your-terraform-state-bucket \
  --versioning-configuration Status=Enabled
aws s3api put-bucket-encryption --bucket your-terraform-state-bucket \
  --server-side-encryption-configuration '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
aws s3api put-public-access-block --bucket your-terraform-state-bucket \
  --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

# verify
aws s3api get-bucket-versioning --bucket your-terraform-state-bucket   # "Status": "Enabled"
aws s3api get-bucket-encryption --bucket your-terraform-state-bucket   # "SSEAlgorithm": "AES256"
```

* Any region other than `us-east-1` → add `--create-bucket-configuration LocationConstraint=ap-south-1`
* Don't store state in a bucket the same config creates → chicken-and-egg on `init`, and `destroy` would delete the bucket holding its own state
* Versioning → every apply keeps the old state as a previous version, the backend equivalent of `.backup`, but keeps all of them
* Encryption → S3 already encrypts with AES256 by default; setting it makes it explicit
* Two buckets, two jobs → the backend bucket only stores state and is never in the config | a `resource "aws_s3_bucket"` is infra the config creates and destroys

## The state bucket as code (bootstrap)

The same bucket written in Terraform, in its own folder (e.g. `state-bootstrap/`) whose own state stays local.

```hcl
resource "aws_s3_bucket" "tf_state" {
  bucket = "your-terraform-state-bucket"

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_s3_bucket_versioning" "tf_state" {
  bucket = aws_s3_bucket.tf_state.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "tf_state" {
  bucket = aws_s3_bucket.tf_state.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "tf_state" {
  bucket                  = aws_s3_bucket.tf_state.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
```

* One bucket + three settings → since AWS provider v4 every bucket setting is its own resource pointing at the bucket
* `prevent_destroy = true` → any plan that would delete the bucket errors out instead
* `bucket = aws_s3_bucket.tf_state.id` → `type.name.attribute`; for S3 the `id` is the bucket name, and the reference makes the settings wait for the bucket
* Same local name `tf_state` on all four → allowed because the types differ, so the addresses are unique; it's a convention showing they belong together
* `"aws:kms"` instead of `"AES256"` → uses a KMS key (`aws/s3` if none is given), adds key access control and audit logs; add `bucket_key_enabled = true` to cut KMS calls
* An existing bucket (e.g. made by a script) can't be written like this directly → `apply` fails with "already exists"; it has to be imported (see Import below) or created under a new name
* `plan` → `4 to add`

## S3 native state locking

* Before → locking needed a separate DynamoDB table (`dynamodb_table = "tf-locks"`): extra service, extra IAM permissions, extra cost
* Terraform 1.10+ → `use_lockfile = true`, locking with S3 alone (stable from 1.11); DynamoDB locking is deprecated
* How it works → S3 conditional writes with the `If-None-Match` header
    1. Terraform tries to create `<key>.tflock`, e.g. `dev/terraform.tfstate.tflock`, only if it doesn't already exist
    2. Doesn't exist → the write succeeds, the lock is acquired
    3. Already exists → S3 rejects it with `412 PreconditionFailed`, Terraform reports `Error acquiring the state lock`
    4. Run finishes → the lock file is deleted (shows as a delete marker when versioning is on)
* Locks are taken by every command that writes or reads state for a run → `plan`, `apply`, `destroy`, `refresh`
* The second run fails immediately by default → `-lock-timeout=5m` makes it retry and wait
* Versioning → the course says it's required for native locking; Terraform's docs only strongly recommend it. Enable it anyway, for rollback

## Migrating local state to S3

1. Create the state bucket with versioning
2. Add the `backend "s3"` block
3. `terraform init -migrate-state` → answer `yes` to copy the local state to S3
4. `terraform state pull | head` → prints the state from S3
5. `terraform plan` → must say `No changes`
6. Delete the leftover local `terraform.tfstate` and `terraform.tfstate.backup` → they are stale, not used anymore, and still contain account IDs and secrets

* `.terraform/terraform.tfstate` → not infra state; it records which backend this folder uses
* Proof the local files were stale → the old backup still had a VPC ID that had since been destroyed and recreated

## Lab: testing the lock

1. Terminal 1 → `terraform destroy`, stop at the `Enter a value:` prompt (the lock is held while waiting)
2. Terminal 2 → `terraform destroy`
3. Terminal 2 fails →

```
Error: Error acquiring the state lock
Error message: operation error S3: PutObject, https response error StatusCode: 412
api error PreconditionFailed: At least one of the pre-conditions you specified did not hold
Lock Info:
  ID:        <lock-id>
  Path:      <state-bucket>/dev/terraform.tfstate
  Operation: OperationTypeApply
  Who:       <user>@<hostname>
  Version:   1.17.0
```

4. While terminal 1 waits → the S3 console shows `dev/terraform.tfstate.tflock` next to the state
5. Answer `yes` or `no` in terminal 1 → lock released, `.tflock` deleted, terminal 2 can run

* `Operation: OperationTypeApply` → `destroy` is an `apply` that removes everything
* `Who` → in a team, tells you who is holding the lock

| Symptom | Cause | Fix |
|---|---|---|
| `Error acquiring the state lock` | Another run holds the lock | Wait, or `-lock-timeout=5m` |
| Lock stays after a crash | Process killed mid-run, `.tflock` left behind | `terraform force-unlock <lock-id>`, only when no run is live |
| `Backend configuration changed` | Backend block edited | `terraform init -migrate-state` or `-reconfigure` |
| `NoSuchBucket` on init | State bucket doesn't exist | Create it first |
| `AccessDenied` on init | IAM user can't read/write the bucket | Grant `s3:ListBucket`, `s3:GetObject`, `s3:PutObject`, `s3:DeleteObject` on the bucket and key |
| `Unsupported argument "use_lockfile"` | Terraform older than 1.10 | Upgrade Terraform |

* Never `-lock=false` → that's exactly how state gets corrupted
* Never `force-unlock` a lock held by a live run

## Locking vs code conflicts

* Locking stops two runs writing state at the same time → it doesn't merge people's code
* Person A adds VPC 4 and 5 and applies | Person B never pulled A's code and applies → B's plan destroys VPC 4 and 5, because they're in state but not in B's code
* A saved plan made before someone else's apply → `Error: Saved plan is stale`, must re-plan
* Real fix → Git as the single source of truth, PRs with `plan` in CI, `apply` only from `main` via CI

## After destroy

* `terraform destroy` deletes the resources, not the state file → the state stays in S3 with `"resources": []`
* `serial` goes up (destroy is a write), `lineage` stays the same → the next `apply` continues the same history
* `terraform state list` → prints nothing
* With versioning on → every old copy and the `.tflock` delete markers stay visible under Show versions
* Delete the state object only when the config is retired for good → `aws s3 rm s3://<bucket>/dev/terraform.tfstate`

## State commands

None of these touch AWS; they only read or edit the state file. Only `apply` and `destroy` change real infra.

* `terraform state list` → every address Terraform manages, one per line

```
aws_s3_bucket.first_bucket
aws_s3_bucket_server_side_encryption_configuration.first_bucket
aws_s3_bucket_versioning.first_bucket
aws_vpc.my_vpc
```

* `terraform state show aws_vpc.my_vpc` → every stored attribute of one resource (`id`, `arn`, `cidr_block`, `tags`, `owner_id`); takes the full address from `state list`
* `terraform state pull` → downloads the state and prints the JSON; the only way to see the remote file from the terminal | `terraform state pull | grep serial`
* `terraform state mv <old> <new>` → rename a resource in state
* `terraform state rm <address>` → Terraform forgets the resource, it keeps running in AWS
* `terraform state push` → overwrite remote state with a local file; disaster recovery only
* `terraform show` → readable view of the whole current state
* `terraform plan -refresh-only` → show drift without changing anything

| Command | Changes state | Changes AWS |
|---|---|---|
| `state list` / `show` / `pull` | No | No |
| `state mv` | Renames an entry | No |
| `state rm` | Removes an entry | No |
| `import` | Adds an entry | No |
| `destroy` | Removes entries | Deletes resources |

* `terraform show` vs `terraform state show` → `show` takes a file (state or saved plan), `state show` takes an address

| Symptom | Cause | Fix |
|---|---|---|
| `Failed to read the given file as a state or plan file` | Ran `terraform show aws_s3_bucket.first_bucket`, so the address was read as a file name | `terraform state show aws_s3_bucket.first_bucket` |

## state mv: rename without recreating

1. Rename the block in code → `resource "aws_vpc" "my_vpc"` becomes `resource "aws_vpc" "main"`, and update every reference to `aws_vpc.main.id`
2. `terraform plan` → shows destroy `my_vpc` + create `main`, because Terraform sees a removed resource and a new one
3. `terraform state mv aws_vpc.my_vpc aws_vpc.main`
4. `terraform plan` → `No changes`, the same VPC is now tracked under the new address

* Use it whenever a resource is renamed or moved into a module, so refactoring never destroys real infra

## state rm vs destroy

| | Real resource in AWS | In state |
|---|---|---|
| `terraform destroy` | Deleted | Removed |
| `terraform state rm` | Still running | Removed |

* After `state rm` → also delete the block from code, otherwise the next `plan` wants to create it again and you get a duplicate
* Use it to keep a resource while destroying the rest, or to hand it over to another config

## Import

* Import → adopt a resource that already exists in AWS into Terraform's state
* Needed for anything created outside Terraform → console, CLI, scripts, or a resource dropped with `state rm`
* `terraform import <address> <real-id>` → address = where it lives in your code, id = which real object it is
* ID format is on each resource's registry page under Import → VPC = `vpc-...`, S3 bucket and its settings = the bucket name
* Import only writes state, never code → the resource block must exist first, or it fails with `resource address ... does not exist in the configuration`
* Code must describe the real resource → change the code to match AWS, never the other way round, until `plan` is clean
* `state rm` and `import` are an on/off switch → whatever is in state when `destroy` runs gets destroyed, imported or not

## Lab: recovering from state rm

1. `terraform state rm aws_vpc.my_vpc` → VPC still running, Terraform forgot it
2. Don't `apply` → it would create a second VPC
3. Find the real ID →

```bash
aws ec2 describe-vpcs --filters Name=tag:Name,Values=tf-day3-vpc \
  --query 'Vpcs[].VpcId' --output text
```

4. `terraform import aws_vpc.my_vpc vpc-xxxxxxxx` → `Import successful!`
5. `terraform state list` → all resources back | `terraform plan` → `No changes`

* It felt like one command because the resource block was still in code; only the state entry was missing

## Lab: importing a console-made VPC

1. Create a VPC in the console (VPC only)
2. Read its real settings →

```bash
aws ec2 describe-vpcs --vpc-ids vpc-xxxxxxxx \
  --query 'Vpcs[0].{CIDR:CidrBlock,Tags:Tags}'
```

3. Write a matching block →

```hcl
resource "aws_vpc" "demo_import_vpc" {
  cidr_block = "10.0.0.0/24"

  tags = {
    Name = "import-vpc"
  }
}
```

4. `terraform import aws_vpc.demo_import_vpc vpc-xxxxxxxx`
5. `terraform plan` →
    * `No changes` → code matches, done
    * `~ update in-place` → small difference (tags), fix the code and re-plan
    * `-/+ must be replaced` → wrong `cidr_block`, don't apply or the console VPC is deleted
6. From now on Terraform owns it → `terraform destroy` deletes it too | to keep it, `terraform state rm` it and delete the block
7. Removing the block from code later without `state rm` → the next plan destroys it

## Import block and generated code

Terraform 1.5+ can import from code and write the resource block for you.

```hcl
import {
  to = aws_vpc.demo_import_vpc
  id = "vpc-xxxxxxxx"
}
```

```bash
terraform plan -generate-config-out=generated.tf
terraform apply                       # 1 imported, 0 added, 0 changed, 0 destroyed
```

* `generated.tf` → a full resource block filled in from AWS; delete `null` lines and anything not needed
* Shows in `plan` as `1 to import` → reviewable in a PR, unlike the CLI command
* Delete the `import {}` block after the apply, its job is done
* Standard way to bring console-built infra into Terraform without writing every block by hand

!!! tip "Quick revision"

    * State = map from code to real resources, holds secrets, never commit it
    * Backend → S3 bucket created outside the config, versioning on, `encrypt = true`, `use_lockfile = true`
    * Native lock → `.tflock` + `If-None-Match`, conflict = `412 PreconditionFailed`
    * Locking protects state, Git and CI protect code
    * `state rm` = forget, `import` = adopt, `state mv` = rename, none of them touch AWS
    * Import needs a matching resource block first, then `plan` must say `No changes`

!!! question "Interview points"

    * What is the Terraform state file? → JSON mapping resources in code to real infrastructure, used to calculate diffs; may contain secrets
    * Why use a remote backend? → shared state for teams and CI, locking, encryption, versioned backups, no secrets in Git
    * How does S3 native state locking work? → Terraform creates a `.tflock` object with a conditional write (`If-None-Match`); if it already exists S3 returns 412 and the second run fails
    * Do you still need DynamoDB for locking? → no, from Terraform 1.10 `use_lockfile = true` locks with S3 alone; DynamoDB locking is deprecated
    * What happens if the state file is lost? → Terraform no longer knows what it manages; recover from a bucket version, or `terraform import` the resources back
    * How do you handle a stuck lock? → confirm no run is active, then `terraform force-unlock <lock-id>`
    * Can you use variables in the backend block? → no, the backend is configured before variables are evaluated; use `-backend-config` for dynamic values
    * How do you separate environments? → different state keys (`dev/`, `prod/`) or separate backends, so a change in one can't affect the other
    * `state rm` vs `destroy`? → `state rm` forgets the resource but leaves it running; `destroy` deletes the real resource
    * Two engineers apply different code against the same state, what happens? → locking serializes the runs but doesn't merge code; the second plan destroys whatever its code lacks, so use PRs and CI-only applies
    * What does `terraform import` do? → adds an existing real resource to state under an address in your code; it writes state only, so the matching resource block must exist first
    * How do you bring console-created infra into Terraform? → write matching resource blocks (or use an `import` block with `plan -generate-config-out`), import, then adjust code until `plan` shows no changes
    * You renamed a resource in code and the plan wants to recreate it, what do you do? → `terraform state mv <old> <new>` so the existing object is tracked under the new address
    * You ran `state rm` by mistake, how do you recover? → don't apply; find the real ID and `terraform import` it back, then confirm `plan` shows no changes
    * Does `destroy` delete the state file? → no, it deletes the resources and leaves an empty state with a higher serial
