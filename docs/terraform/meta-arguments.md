# Meta-Arguments

*Hands-on notes, Terraform*

## What they are

* Meta-argument → special argument that works on any resource (most also on modules) regardless of provider → changes how Terraform manages the block, not what it configures
* The main ones → `count`, `for_each`, `depends_on`, `provider`, `lifecycle`
* Terraform has no real loops → `count` and `for_each` are how you get loop-like behaviour → it builds every copy in one plan, not step by step

## count

* `count = N` → creates N copies of the block, identified by number → `aws_s3_bucket.bucket1[0]`, `[1]`, `[2]`
* `count.index` → zero-based number of the current copy → runs `0` to `count - 1` → only valid inside a block that sets `count`
* Without `count.index` every copy gets the same config → two buckets with the same name fail
* `count = length(var.list)` → follows the list size automatically → never goes out of range
* On/off toggle → `count = var.enabled ? 1 : 0`
* Weakness → copies are tied to position → remove an item from the middle and the later ones shift down → Terraform destroys and recreates them

```hcl
resource "aws_s3_bucket" "bucket1" {
  count  = length(var.bucket_names)
  bucket = var.bucket_names[count.index]

  tags = var.tag-s3
}

variable "bucket_names" {
  description = "list of bucket names"
  type        = list(string)
  default     = ["my-unique-ap14-tf", "my-unique-ap1404-tf", "my-unique-ap140604-tf"]
}
```

## for_each

* `for_each` → creates one copy per item, identified by name → `aws_s3_bucket.bucket2["my-unique-ap14-tf"]`
* Accepts only a map or a set of strings → not a number, not a plain list → convert a list with `toset(var.list)`
* `each.key` / `each.value` → the `for_each` version of `count.index`
* Set → `each.key` and `each.value` are the same thing, the item itself → use `each.value`
* Map → `each.key` is the left side, `each.value` is the right side
* Sets have no index → `var.set[each.key]` does not work
* Cannot use `count` and `for_each` on the same block
* Remove one item → only that copy is destroyed → the rest are untouched

```hcl
resource "aws_s3_bucket" "bucket2" {
  for_each = toset(var.bucket_names)
  bucket   = each.value

  tags = var.tag-s3
}
```

### With a map

```hcl
variable "bucket_map" {
  description = "map of purpose => bucket name"
  type        = map(string)
  default = {
    logs   = "my-unique-ap14-logs-tf"
    data   = "my-unique-ap1404-data-tf"
    backup = "my-unique-ap140604-backup-tf"
  }
}

resource "aws_s3_bucket" "bucket3" {
  for_each = var.bucket_map
  bucket   = each.value

  tags = merge(var.tag-s3, {
    Purpose = each.key
  })
}

output "bucket_arns" {
  value = { for k, b in aws_s3_bucket.bucket3 : k => b.arn }
}
```

* `each.value` → the real bucket name
* `each.key` → label used for the `Purpose` tag
* `merge()` → combines the existing tag map with the extra tag (assumes `tag-s3` is a `map(string)`)
* `for` expression in `output` → builds a map of `purpose => arn`

## count vs for_each

| | `count` | `for_each` |
|---|---|---|
| Identified by | number `[0]` | name `["logs"]` |
| Input | a number | map or set of strings |
| Current item | `count.index` | `each.key` / `each.value` |
| Remove from the middle | later copies shift, may be recreated | only that copy is destroyed |
| Best for | N identical copies, on/off toggle | distinct things that each have an identity |

## depends_on

* `depends_on` → forces one resource to be created after another when Terraform cannot see the link
* Normal ordering → Terraform reads references → if B uses an attribute of A, A goes first (implicit dependency)
* Needed only for hidden dependencies → B needs A but never references it → e.g. an IAM policy that must exist before an instance boots
* Takes a list of resource references, no attributes → `[aws_iam_role_policy.s3_access]`, not `[aws_iam_role_policy.s3_access.id]`
* Works on modules too → `depends_on = [module.network]`
* Destroy order is reversed
* Use sparingly → prefer a real reference → overuse makes plans less precise

```hcl
resource "aws_instance" "app" {
  ami                  = "ami-123"
  instance_type        = "t3.micro"
  iam_instance_profile = aws_iam_instance_profile.app.name

  depends_on = [aws_iam_role_policy.s3_access]
}
```

## provider and lifecycle

* `provider` → picks a non-default provider config, e.g. an alias for another region → `provider = aws.mumbai`
* Modules use `providers = { aws = aws.mumbai }` (plural)
* `lifecycle` → controls create, update and destroy behaviour

```hcl
lifecycle {
  create_before_destroy = true
  prevent_destroy       = true
  ignore_changes        = [tags]
  replace_triggered_by  = [aws_launch_template.lt]
}
```

* `create_before_destroy` → build the new one first, then delete the old
* `prevent_destroy` → any plan that would destroy it errors out → safety rail for prod databases
* `ignore_changes` → ignore drift on the listed attributes
* `replace_triggered_by` → replace this resource when the listed one changes

## Lab: count and for_each on S3 buckets

Errors I hit while practising:

| Symptom | Cause | Fix |
|---|---|---|
| `Invalid index` on `var.bucket_names[count.index]` | `count = 4` but the list has 3 items, so index `3` does not exist | Use `count = length(var.bucket_names)` |
| `The given "for_each" argument value is unsuitable` | `for_each = length(...)` passes a number | Pass a set or map: `for_each = toset(var.bucket_names)` |
| Cannot look up `var.bucket_set_names[each.key]` | A set has no index | Use `each.value` directly |

Notes:

* `count = 2` with a 3-item list → creates only the first two buckets, the third name is ignored
* The plan fails before anything is created → no partial apply

!!! question "Interview points"

    * What is a meta-argument? → an argument available on any resource regardless of provider, e.g. `count`, `for_each`, `depends_on`, `provider`, `lifecycle`
    * What is `count.index`? → the zero-based index of the current copy of a resource that uses `count`
    * `count` vs `for_each`? → `count` identifies copies by position, `for_each` by key → prefer `for_each` for distinct resources
    * Why is `for_each` safer than `count` when removing an item? → with `count` the indexes shift and later resources get destroyed and recreated, with `for_each` only the removed key is touched
    * What types does `for_each` accept? → a map or a set of strings, so wrap a list in `toset()`
    * What are `each.key` and `each.value` for a set? → both are the item itself
    * What happens with `count = 4` on a 3-item list? → plan fails with `Invalid index`, nothing is created
    * Can you use `count` and `for_each` on the same resource? → no
    * When do you need `depends_on`? → only for hidden dependencies, where B needs A but does not reference any of its attributes
    * What does `prevent_destroy` do? → makes Terraform error on any plan that would destroy the resource
