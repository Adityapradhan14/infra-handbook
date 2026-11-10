# Lifecycle Rules

*Hands-on notes, Terraform course day 9*

## What they are

* `lifecycle` → meta-argument block inside a resource → changes how Terraform creates, updates and destroys that one resource
* Rules covered → `create_before_destroy`, `prevent_destroy`, `ignore_changes`, `precondition`, `postcondition`, `replace_triggered_by`
* The `lifecycle` block itself takes literal values only → no variables or expressions in `create_before_destroy`, `prevent_destroy`, `ignore_changes` → conditions and `replace_triggered_by` are the exceptions
* `precondition` / `postcondition` / `replace_triggered_by` need Terraform 1.2+

| Rule | Does | Typical use |
|---|---|---|
| `create_before_destroy` | Builds the replacement first, then deletes the old | Zero-downtime replacement |
| `prevent_destroy` | Errors on any plan that would destroy the resource | Prod databases, state buckets |
| `ignore_changes` | Skips drift on the listed attributes | ASG capacity, tags changed outside Terraform |
| `precondition` | Checks inputs before the resource is created | Guardrails on variables |
| `postcondition` | Checks the result after the resource is built | Verify what AWS returned |
| `replace_triggered_by` | Replaces this resource when another one changes | Rebuild on a related change |

## create_before_destroy

* Default replacement order → destroy old, then create new → downtime in between
* `create_before_destroy = true` → create new, then destroy old → both exist for a moment
* Spreads to dependencies → resources the flagged one depends on get it implicitly
* Gotcha → unique names collide while both exist → a fixed `name` on a security group fails → use `name_prefix`

```hcl
resource "aws_instance" "example" {
  ami           = "ami-02a9cdd4e98bc3c78"
  instance_type = var.instance_type

  lifecycle {
    create_before_destroy = true
  }
}
```

## prevent_destroy

* `prevent_destroy = true` → any plan that would destroy the resource fails with `Instance cannot be destroyed`
* Blocks `terraform destroy` too → set it back to `false` before cleaning up a lab
* Also blocks replacement → a replace still destroys the old one → changing `ami` or `region` errors instead of replacing
* In-place updates (like `tags`) still work
* Gotcha → it only guards while the block exists → delete the resource block from the code and the guard goes with it

```hcl
lifecycle {
  create_before_destroy = true
  prevent_destroy       = true
}
```

## ignore_changes

* `ignore_changes = [attr]` → Terraform stops comparing those attributes → manual changes stay
* Value in config is still used on first create → ignored only from then on
* Update-only → does not stop a replacement caused by other attributes
* Gotcha → also ignores your own edits to the `.tf` → change `tags` in the file and the plan shows `No changes`
* Takes bare attribute references → `[tags]`, `[tags["Name"]]` → not strings, not `var.` expressions
* `ignore_changes = all` → Terraform only creates and destroys → avoid

```hcl
lifecycle {
  ignore_changes = [tags]
}
```

### Real use: Auto Scaling Group

* `desired_capacity` in the config is only the starting count → scaling policies, schedules or someone in the console change it later
* Without the rule → next `apply` sees 4 vs 2 and scales the group back down
* With it → autoscaling owns the value → `min_size` and `max_size` are still managed by Terraform
* Editing `desired_capacity` in the `.tf` later does nothing → to change it use the CLI or console, remove it from `ignore_changes` temporarily, or raise `min_size`

```hcl
resource "aws_autoscaling_group" "app_servers" {
  name             = "app-servers-asg"
  min_size         = 1
  max_size         = 5
  desired_capacity = 2

  launch_template {
    id      = aws_launch_template.app_server.id
    version = "$Latest"
  }

  lifecycle {
    ignore_changes = [desired_capacity]
  }
}
```

### Lab: with and without

* Two instances, one with `ignore_changes = [tags]` and one without
* Change `Env` to `prod` on both in the console → `terraform plan`
* Result → only the one without the rule is shown as `~ update in-place`, the other is not mentioned

## precondition

* Runs before the resource is created or changed → false condition fails the plan with your `error_message` → nothing is created
* Can reference variables, data sources and other resources → not just the one variable
* No `self` → the resource does not exist yet
* Variable `validation` is for one variable only → use `precondition` for cross-resource checks

```hcl
lifecycle {
  precondition {
    condition     = contains(["t2.micro", "t3.micro"], var.instance_type)
    error_message = "Only t2.micro or t3.micro allowed (free tier)."
  }
}
```

## postcondition

* Runs after the resource is built → can use `self` to check what actually came back
* Timing depends on the value:
    * Known at plan time (`instance_type`, `ami`) → fails during `plan` → nothing created
    * Known after apply (`public_ip`, `id`, `instance_state`) → can only be checked after creation → the resource already exists when it fails
* Multiple blocks allowed
* Works on data sources too → e.g. check an AMI's `architecture` after lookup

```hcl
lifecycle {
  postcondition {
    condition     = self.instance_type == "t2.micro"
    error_message = "Postcondition failed: expected t2.micro, got ${self.instance_type}."
  }
}
```

| | `precondition` | `postcondition` |
|---|---|---|
| Runs | Before create | After create |
| `self` | No | Yes |
| Checks | Inputs and assumptions | The actual result |
| Resource exists if it fails | No | Only for values known after apply |

## replace_triggered_by

* Forces replacement of this resource when the listed resource or attribute changes → even if its own arguments did not
* Takes references to resources or their attributes → not variables or literals
* Trick → `terraform_data` with `input = var.something` → a free resource that only stores a value → change the variable and everything that points at it is replaced
* Whole resource → triggers on update or replace → an attribute like `aws_security_group.web.id` → triggers only when that attribute changes
* `-replace=` on the CLI is a one-time manual replace → this is permanent and automatic
* Opposite of `ignore_changes`

```hcl
variable "app_version" {
  type    = string
  default = "v1"
}

resource "terraform_data" "version_app" {
  input = var.app_version
}

resource "aws_instance" "example" {
  ami           = "ami-02a9cdd4e98bc3c78"
  instance_type = var.instance_type

  lifecycle {
    create_before_destroy = true
    replace_triggered_by  = [terraform_data.version_app]
  }
}
```

* `terraform plan -var="app_version=v2"` showed:
    * `terraform_data.version_app` → `~ update in-place` (`input = "v1" -> "v2"`)
    * `aws_instance.example will be replaced due to changes in replace_triggered_by`
    * `+/-` = create replacement, then destroy → that is `create_before_destroy`
    * `Plan: 1 to add, 1 to change, 1 to destroy`
* Only a plan was read → `plan` changes nothing in AWS
* In this lab the new instance is identical → nothing uses `app_version` → it only demonstrates the mechanism
* Real use → boot-time work like `user_data` runs once at launch → a new instance is the only way to run it again
* Not used much in real configs → alternatives are `user_data_replace_on_change`, ASG instance refresh, new AMIs

## Errors I hit

| Symptom | Cause | Fix |
|---|---|---|
| `Invalid index` on `tolist(var.regions_allowed[0])` | `[0]` applied to the set before `tolist()` converted it | `tolist(var.regions_allowed)[0]` |
| `Resource precondition failed`, value shown as `"t3.micro "` | Trailing space in the variable default | Remove the space |
| `Resource postcondition failed` on `instance_type`, nothing created | `instance_type` is known at plan time, so the check ran during `plan` | Expected → fix the condition or the value |
| Postcondition on `public_ip` passed with `associate_public_ip_address = false` | Instance still got a public IP and state showed `true` → setting did not take effect in the default subnet (cause not confirmed) | Use a condition that cannot pass, like the `instance_type` one |

* The `Releasing state lock` line after a failed plan is just cleanup, not a second error
* `region` as an argument on `aws_instance` needs AWS provider v6+

!!! question "Interview points"

    * What does `create_before_destroy` do? → builds the replacement first and then destroys the old one → avoids downtime
    * Gotcha with `create_before_destroy`? → both resources exist at once → a fixed unique name collides → use `name_prefix`
    * What does `prevent_destroy` do? → makes Terraform error on any plan that would destroy the resource
    * Does `prevent_destroy` protect you if the block is deleted from the code? → no → the guard is gone with the block
    * Does `prevent_destroy` block replacement? → yes → replacement destroys the old resource
    * What does `ignore_changes` do? → Terraform skips drift on the listed attributes → it also ignores your own config edits to them
    * Real use of `ignore_changes`? → ASG `desired_capacity` managed by autoscaling, tags added by other tools
    * `precondition` vs `postcondition`? → precondition checks inputs before creation, postcondition checks the result after with `self`
    * Variable `validation` vs `precondition`? → `validation` checks one variable, `precondition` can check across variables, data sources and resources
    * When does a postcondition fail without creating anything? → when the attribute is known at plan time
    * What does `replace_triggered_by` do? → replaces a resource when another resource or attribute changes, even if its own arguments did not
    * How do you trigger replacement from a variable change? → put the variable in a `terraform_data` input and reference it in `replace_triggered_by`
