# Terraform

Notes on Infrastructure as Code with Terraform, written as I work through it: what it is, the HCL language, how Terraform talks to AWS, how it keeps track of what it built, and how to make configs reusable with variables.

<div class="ih-chapters" markdown>

1. [IaC & Terraform](iac-and-terraform.md)
    What IaC is, why it exists, declarative vs imperative, the `init` → `plan` → `apply` workflow
2. [HCL Syntax](hcl-syntax.md)
    Blocks, labels, arguments, references, types, expressions, meta-arguments
3. [Providers & Versioning](providers.md)
    `required_providers`, the provider block, `~>` constraints, the lock file, first resource
4. [AWS Auth & S3](aws-auth-and-s3.md)
    Credential chain, `aws sts get-caller-identity`, S3 buckets, implicit dependencies
5. [State & Remote Backend](state-and-remote-backend.md)
    `terraform.tfstate`, S3 backend, native locking, migration, state commands, `import`
6. [Variables, Locals & Outputs](variables-locals-outputs.md)
    Input variables, type constraints, locals, `merge`, precedence, `TF_VAR_`, outputs
7. [Type Constraints](type-constraints.md)
    `list`, `set`, `map`, `tuple`, `object`, `optional()`, validation blocks
8. [Meta-Arguments](meta-arguments.md)
    `count`, `for_each`, `depends_on`, `lifecycle`

</div>
