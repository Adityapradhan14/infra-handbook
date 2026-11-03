# Type Constraints

*Hands-on notes, Terraform course day 7*

## Why types

* `type` on a variable → Terraform checks the value before `plan` touches anything → wrong input fails early with a clear error
* No `type` → defaults to `any` → anything is accepted, mistakes surface later as confusing provider or API errors
* Always set `type` and `description` on every variable

## Type family

* Primitive → `string`, `number`, `bool` → a single value
* Collection → `list`, `set`, `map` → many values, all of the same type
* Structural → `tuple`, `object` → a fixed shape, a different type per element
* Tuple is to list what object is to map → same structure, but mixed types allowed

| Type | Access by | Duplicates | Mixed types | Example |
|---|---|---|---|---|
| `list(string)` | position `[0]` | allowed | no | `["a", "b", "a"]` |
| `set(string)` | nothing (loop or `contains`) | dropped | no | `["a", "b"]` |
| `map(string)` | key `["dev"]` | keys unique | no | `{ dev = "t2.micro" }` |
| `tuple([string, number])` | position `[0]` | allowed | yes, per position | `["t2.micro", 2]` |
| `object({ a = string })` | name `.a` | fields unique | yes, per field | `{ a = "x" }` |

## Primitive types

* `string` → text → `"t3.micro"`
* `number` → integers and floats → `2`, `3.5`
* `bool` → `true` / `false`
* Auto conversion → `"5"` given to a `number` becomes `5`; `"true"` given to a `bool` becomes `true`; `"abc"` to `number` errors

```hcl
variable "instance_type" {
  description = "Type of ec2 instance"
  type        = string
  default     = "t3.micro"
}

variable "count_instance" {
  description = "Number of aws instances"
  type        = number
  default     = 1
}

variable "monitoring" {
  description = "enable monitoring"
  type        = bool
  default     = true
}
```

## List

* Ordered, allows duplicates, all elements the same type → `list(string)`
* Access by index → `var.cidr_block[0]`
* `length(var.x)` → number of elements
* Pairs with `count` → resources keyed by index → `aws_instance.x[0]`, `[1]`

```hcl
variable "cidr_block" {
  description = "cidr ranges for security group rules"
  type        = list(string)
  default     = ["10.0.0.0/8", "192.168.0.0/16", "172.16.0.0/12"]
}

# var.cidr_block[1] → "192.168.0.0/16"
```

## Set

* Unordered, unique, all elements the same type → `set(string)`
* Duplicates dropped at the moment the variable is read → never created, not deleted later
* No index → `var.regions_allowed[0]` → `Error: Invalid index`
* Displayed sorted (strings lexically), so the written order is not kept
* Native uses → `for_each` (each resource keyed by value) and `contains(set, value)` (membership check)
* For sets in `for_each` → `each.key == each.value`
* `tolist(set)[0]` → works, but that is a list operation; `[0]` is whatever sorts first

```hcl
variable "regions_allowed" {
  description = "the regions where it will be created"
  type        = set(string)
  default     = ["us-east-2", "us-east-1", "us-east-1"]
}

# var.regions_allowed → ["us-east-1", "us-east-2"]   (deduped + sorted)
```

## List vs set: why it matters

* `count` + list → identity is position → remove a middle item → every later index shifts → those resources replaced
* `for_each` + set → identity is value → remove an item → only that resource destroyed

```
List: apple banana orange apple  → remove banana
  [0] apple  → apple    no change
  [1] banana → orange   replaced
  [2] orange → apple    replaced
  [3] apple  → (gone)   destroyed

Set: { apple, banana, orange }  → remove banana
  ["apple"]  no change
  ["banana"] destroyed
  ["orange"] no change
```

* Why providers use sets → e.g. `vpc_security_group_ids` is a set → reordering IDs shows no diff in `plan`
* Pick a set when swapping two items wouldn't change the meaning → regions to deploy to, bucket names, SG IDs, users
* Pick a list when order or position matters → AZs mapped to CIDRs by index, priority order, "take the first one"

## Map

* Key = value pairs; keys are always strings and unique; values all the same type → `map(string)`
* Access by key → `var.instance_types["dev"]` | `var.instance_types[var.environment]`
* No index → `var.m[0]` errors
* `lookup(map, key, default)` → safe access when the key may be missing
* `keys(map)` / `values(map)` → lists, sorted by key
* `merge(a, b)` → combines maps; on a key clash `b` wins
* `tags = { ... }` is just a map
* Pairs with `for_each` → `each.key` = key, `each.value` = value (unlike sets, they differ)

```hcl
variable "tag-ec2" {
  description = "ec2-instance tags"
  type        = map(string)
  default = {
    Name        = "demo-tag"
    Environment = "dev"
    created_by  = "terraform-aditya"
  }
}

variable "instance_types" {
  type = map(string)
  default = {
    dev     = "t2.micro"
    staging = "t3.small"
    prod    = "t3.large"
  }
}

# instance_type = var.instance_types[var.environment]
```

* `for_each` over a map → key and value both used:

```hcl
variable "buckets" {
  type = map(string)
  default = {
    logs    = "Enabled"
    backups = "Suspended"
  }
}

resource "aws_s3_bucket" "b" {
  for_each = var.buckets
  bucket   = "${local.prefix}-${each.key}"
}

resource "aws_s3_bucket_versioning" "v" {
  for_each = var.buckets
  bucket   = aws_s3_bucket.b[each.key].id
  versioning_configuration {
    status = each.value
  }
}
```

## Element type is required

* `map()` / `list()` / `set()` with empty brackets → syntax error
* `map(any)` → Terraform infers one type for all values → `{ a = "x", b = 5 }` becomes `map(string)` → `5` silently turns into `"5"`
* Bare `map` → legacy shorthand for `map(any)` → still works, avoid
* Spell out the element type → `map(string)`, `list(number)`; for different types per key → use `object`

## Tuple

* Fixed length, ordered, each position has its own type → `tuple([number, string, number])`
* Wrong length or wrong type order → error
* Access by index like a list → `var.ingress_value[0]`
* Weak point → `[443, "tcp", 443]` doesn't say what each value means
* Rarely declared in real code; prefer `object`
* Any `[...]` literal is a tuple until converted to the declared type → why error messages mention "tuple" for a `list` variable

```hcl
variable "ingress_value" {
  type    = tuple([number, string, number])
  default = [443, "tcp", 443]
}

# from_port   = var.ingress_value[0]   → 443
# ip_protocol = var.ingress_value[1]   → "tcp"
# to_port     = var.ingress_value[2]   → 443
```

## Object

* Named fields, each with its own type → `object({ instance_type = string, count = number })`
* Access by name → `var.server.instance_type`
* Every declared field must be given; wrong field type → error; extra undeclared fields → silently dropped
* Field order doesn't matter (unlike tuple)
* `optional(type, default)` → field can be omitted (Terraform 1.3+) → `count = optional(number, 1)`

```hcl
variable "server" {
  description = "ec2 instance settings"
  type = object({
    instance_type = string
    count         = optional(number, 1)
    monitoring    = optional(bool, false)
  })
  default = {
    instance_type = "t3.micro"
    monitoring    = true
  }
}

resource "aws_instance" "app" {
  count         = var.server.count
  ami           = "ami-xxxxxxxxxxxxxxxxx"
  instance_type = var.server.instance_type
  monitoring    = var.server.monitoring
}
```

* The same ingress rule as an object → readable, self-documenting:

```hcl
variable "ingress" {
  type = object({
    from_port = number
    protocol  = string
    to_port   = number
  })
  default = { from_port = 443, protocol = "tcp", to_port = 443 }
}

# from_port = var.ingress.from_port
```

## Tuple vs object

| | Tuple | Object |
|---|---|---|
| Identified by | position `[0]` | name `.instance_type` |
| Syntax | `[ ]` | `{ }` |
| Order matters | yes | no |
| Optional fields | no | yes, `optional()` |
| Readability | poor, what does `2` mean | clear, `count = 2` |

## Map vs object

* Map → any keys decided by the caller, one value type → a collection of things
* Object → fixed field names decided in the type, mixed types → one thing with properties
* Combined → `map(object({...}))` → many things, each with the same shape → the most common `for_each` pattern

```hcl
variable "servers" {
  type = map(object({
    instance_type = string
    monitoring    = bool
  }))
  default = {
    web = { instance_type = "t2.micro", monitoring = false }
    api = { instance_type = "t3.small", monitoring = true }
  }
}

resource "aws_instance" "s" {
  for_each      = var.servers
  ami           = "ami-xxxxxxxxxxxxxxxxx"
  instance_type = each.value.instance_type
  monitoring    = each.value.monitoring
  tags          = { Name = each.key }
}
```

* `list(object({...}))` → same idea but ordered and index-keyed → fine for `count`, worse for `for_each`

## Validation blocks

* Type checks the shape; `validation` checks business rules → allowed values, formats, ranges
* `condition` must be true, else `error_message` is shown at `plan`
* Several `validation` blocks per variable are allowed
* Since Terraform 1.9 a condition can reference other variables

```hcl
variable "environment" {
  type    = string
  default = "dev"

  validation {
    condition     = contains(["dev", "staging", "preprod", "prod"], var.environment)
    error_message = "Environment must be dev, staging, preprod or prod."
  }
}

variable "vpc_cidr" {
  type    = string
  default = "10.0.0.0/16"

  validation {
    condition     = can(cidrhost(var.vpc_cidr, 0))
    error_message = "VPC CIDR must be a valid IPv4 CIDR block."
  }
}

variable "count_instance" {
  type    = number
  default = 1

  validation {
    condition     = var.count_instance >= 1 && var.count_instance <= 3
    error_message = "Instance count must be between 1 and 3."
  }
}

variable "region" {
  type    = string
  default = "us-east-1"

  validation {
    condition     = contains(var.regions_allowed, var.region)
    error_message = "Region must be one of the allowed regions."
  }
}
```

* `contains(list_or_set, value)` → allowed-values check
* `can(expr)` → true if `expr` doesn't error → format checks like `cidrhost`, `regex`
* `length(var.x) > 0` → non-empty check
* `can(regex("^t3\\.", var.instance_type))` → pattern check

## Type conversion functions

* `tolist(set)` → set → list (sorted order)
* `toset(list)` → list → set (dedupes) → common before `for_each`
* `tomap({...})` → object → map (all values must convert to one type)
* `tonumber("5")` → `5` | `tostring(5)` → `"5"` | `tobool("true")` → `true`
* Prefer declaring the right type over converting at every use

## Lab: type constraints on EC2, SG and S3

Config (course day 7, `~> 6.0` AWS provider, S3 backend with `use_lockfile`):

```hcl
# variables.tf
variable "cidr_block" {
  description = "cidr ranges for security group rules"
  type        = list(string)
  default     = ["10.0.0.0/8", "192.168.0.0/16", "172.16.0.0/12"]
}

variable "regions_allowed" {
  description = "the regions where it will be created"
  type        = set(string)
  default     = ["us-east-1", "us-east-2"]
}

variable "tag-ec2" {
  description = "ec2-instance tags"
  type        = map(string)
  default = {
    Name        = "demo-tag"
    Environment = "dev"
    created_by  = "terraform-aditya"
  }
}

variable "ingress_value" {
  type    = tuple([number, string, number])
  default = [443, "tcp", 443]
}
```

```hcl
# main.tf
resource "aws_instance" "my_instance" {
  count                       = var.count_instance
  ami                         = "ami-xxxxxxxxxxxxxxxxx"
  instance_type               = var.instance_type
  region                      = tolist(var.regions_allowed)[0]   # resource-level region needs AWS provider v6+
  monitoring                  = var.monitoring
  associate_public_ip_address = var.public_ip
  tags                        = var.tag-ec2
}
```

```hcl
# sg.tf
resource "aws_vpc_security_group_ingress_rule" "allow_tls_ipv4" {
  security_group_id = aws_security_group.allow_tls.id
  cidr_ipv4         = var.cidr_block[1]
  from_port         = var.ingress_value[0]
  ip_protocol       = var.ingress_value[1]
  to_port           = var.ingress_value[2]
}

resource "aws_vpc_security_group_egress_rule" "allow_all_traffic_ipv4" {
  security_group_id = aws_security_group.allow_tls.id
  cidr_ipv4         = var.cidr_block[0]
  ip_protocol       = "-1"
}
```

What each type does here:

* `list(string)` → `cidr_block[1]` / `[0]` → pick CIDRs by position
* `set(string)` → `regions_allowed` → unique regions; needs `tolist()` to pick one
* `map(string)` → `tag-ec2` → passed straight to `tags`
* `tuple([number, string, number])` → `ingress_value` → port, protocol, port by position

Set demo in `for_each` (one instance per region, AMI looked up per region because AMI IDs are regional):

```hcl
data "aws_ami" "ubuntu" {
  for_each    = var.regions_allowed
  region      = each.key
  most_recent = true
  owners      = ["099720109477"]   # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"]
  }
}

resource "aws_instance" "per_region" {
  for_each      = var.regions_allowed
  region        = each.key
  ami           = data.aws_ami.ubuntu[each.key].id
  instance_type = var.instance_type
  tags          = { Name = "${local.prefix}-${each.key}" }
}
```

* `plan` shows `aws_instance.per_region["us-east-1"]` and `["us-east-2"]` → keyed by value
* A duplicate region in the default → still only 2 instances
* `count` and `for_each` can't be used on the same resource

Check types in the console:

```bash
terraform console
```

```
> var.cidr_block[0]
"10.0.0.0/8"
> var.regions_allowed[0]
Error: Invalid index
> tolist(var.regions_allowed)[0]
"us-east-1"
> var.tag-ec2["created_by"]
"terraform-aditya"
> var.ingress_value[1]
"tcp"
> toset(["a", "b", "a"])
toset(["a", "b"])
> exit
```

Errors I hit:

| Symptom | Cause | Fix |
|---|---|---|
| `Error: Invalid index` on `var.regions_allowed[0]` | sets have no positions | `tolist(var.regions_allowed)[0]`, or use the set natively with `for_each` |
| `InvalidParameterValue: Invalid value 'us-east-1' for InstanceType` | `instance_type` was fed a region value; AWS rejects it at `apply`, `validate` can't catch it | point `instance_type` at the instance type variable; `grep -n instance_type *.tf *.tfvars` |
| Apply failed halfway, bucket and SG already created | apply is not atomic; created resources are already in state | fix the code, run `apply` again → only the failed resource is created |
| `Unsupported argument "region"` on a resource | resource-level `region` only exists in AWS provider v6+ | `version = "~> 6.0"` in `required_providers`, then `terraform init -upgrade` |
| `Invalid type specification` for `map()` | element type missing | `map(string)` |
| Resource block not closed | `}` after `tags` closed only `tags` | add the resource's closing `}`; `terraform fmt` + `validate` catch it |
| `InvalidAMIID.NotFound` | AMI IDs are per region | look up the AMI with a `data "aws_ami"` per region |

Check and deploy:

1. `terraform fmt`
2. `terraform validate`
3. `terraform plan`
4. `terraform apply`
5. `terraform destroy` when done (EC2 costs money)

!!! tip "Quick revision"

    * Primitive → `string`, `number`, `bool` | Collection → `list`, `set`, `map` | Structural → `tuple`, `object`
    * List → position, dupes | Set → unique, no index | Map → key → value
    * Tuple → fixed types by position | Object → fixed types by name
    * `count` + list → index shift recreates | `for_each` + set/map → stable keys
    * `optional(type, default)` → omit object fields
    * `validation` → `contains`, `can`, `length`, `regex`
    * `tolist` / `toset` / `tomap` → convert when needed

!!! question "Interview points"

    * Why declare types on variables? → bad input fails at `plan` with a clear message instead of a confusing provider error mid-apply
    * List vs set? → list is ordered, allows duplicates and has index access; set is unordered, unique and has no index
    * Why use a set instead of a list? → `for_each` needs stable keys; reordering causes no diff; duplicates are impossible
    * Why is `for_each` preferred over `count`? → `count` keys by index, so removing a middle item shifts and recreates later resources; `for_each` keys by value, so only the removed one is destroyed
    * Can you index a set? → no, `Invalid index`; use `tolist()` or loop over it with `for_each`
    * `each.key` vs `each.value`? → same for a set; for a map, key is the map key and value is its value
    * Map vs object? → map has any keys with one value type; object has fixed field names with their own types
    * Tuple vs object? → both have a fixed shape with mixed types; tuple by position, object by name; object is more readable and supports `optional()`
    * What does `map(any)` do with `{ a = "x", b = 5 }`? → picks one type for all values, so `5` becomes `"5"`
    * How do you make an object field optional? → `optional(type, default)`, Terraform 1.3+
    * How do you restrict a variable to allowed values? → `validation` block with `contains([...], var.x)` and an `error_message`
    * What's the most common real-world `for_each` type? → `map(object({...}))`: many items, each with the same shape
    * Does `terraform validate` catch a wrong value like a region in `instance_type`? → no, it checks syntax and types only; the AWS API rejects it at `apply`
