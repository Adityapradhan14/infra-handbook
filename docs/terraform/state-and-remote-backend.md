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
aws s3api put-public-access-block --bucket your-terraform-state-bucket \
  --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
```

* Any region other than `us-east-1` → add `--create-bucket-configuration LocationConstraint=ap-south-1`
* Don't store state in a bucket the same config creates → chicken-and-egg on `init`, and `destroy` would delete the bucket holding its own state
* Versioning → every apply keeps the old state as a previous version, the backend equivalent of `.backup`, but keeps all of them

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

## State commands

* `terraform state list` → every resource Terraform manages
* `terraform state show aws_vpc.my_vpc` → all stored attributes of one resource
* `terraform state pull` → download and print the current state (works with remote backends)
* `terraform state mv <old> <new>` → rename or move a resource in state without destroying it
* `terraform state rm <address>` → stop managing a resource, the real resource is not deleted
* `terraform import <address> <id>` → bring an existing resource under management
* `terraform plan -refresh-only` → show drift without changing anything
* `terraform show` → human-readable view of the current state

!!! tip "Quick revision"

    * State = map from code to real resources, holds secrets, never commit it
    * Backend → S3 bucket created outside the config, versioning on, `encrypt = true`, `use_lockfile = true`
    * Native lock → `.tflock` + `If-None-Match`, conflict = `412 PreconditionFailed`
    * Locking protects state, Git and CI protect code

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
