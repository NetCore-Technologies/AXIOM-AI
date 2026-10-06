# Security Policy

## Supported Versions

AXIOM is currently under active development.

Security fixes will generally target the latest version on the `main` branch.

| Version        | Supported |
| -------------- | --------- |
| `main`         | ✅         |
| Older releases | ❌         |

---

## Reporting a Vulnerability

Please **do not open a public GitHub issue for a security vulnerability**.

Instead, report security issues privately through the repository's GitHub security reporting mechanism.

When reporting a vulnerability, please include:

* a clear description of the issue
* affected component or feature
* steps to reproduce
* potential impact
* relevant logs or proof of concept
* any suggested mitigation

Please avoid including secrets, credentials, private datasets, API keys, or other sensitive information in the report.

---

## What to Report

Examples of security issues include:

* remote code execution
* arbitrary command execution
* authentication bypass
* privilege escalation
* unsafe model loading
* malicious model or dataset execution
* path traversal
* insecure API endpoints
* accidental exposure of credentials
* unauthorized access to private data
* vulnerabilities in AXIOM's deployment mechanisms

---

## Model and Dataset Security

AI systems introduce risks beyond traditional software.

AXIOM may eventually process:

* downloaded models
* user-provided datasets
* generated files
* external repositories
* inference inputs
* training artifacts

Treat third-party models and datasets as **untrusted inputs** unless their origin and integrity are known.

Do not run untrusted model files or training code with unnecessary system privileges.

---

## Disclosure

We aim to investigate valid security reports promptly and coordinate responsible disclosure where appropriate.

Once an issue has been fixed, relevant security information may be published through the repository's release notes or security advisories.

---

## Scope

This policy applies to the AXIOM open-source project and its official repositories.

Third-party integrations, hosted infrastructure, and external services may have separate security policies.
