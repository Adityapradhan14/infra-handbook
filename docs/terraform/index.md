# Terraform

Notes on Infrastructure as Code with Terraform, written as I work through it: what it is, the HCL language, and how Terraform talks to AWS through providers.

<div class="ih-chapters" markdown>

1. [IaC & Terraform](iac-and-terraform.md)
    What IaC is, why it exists, declarative vs imperative, the `init` → `plan` → `apply` workflow
2. [HCL Syntax](hcl-syntax.md)
    Blocks, labels, arguments, references, types, expressions, meta-arguments
3. [Providers & Versioning](providers.md)
    `required_providers`, the provider block, `~>` constraints, the lock file, first resource

</div>
