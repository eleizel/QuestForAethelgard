# Security Policy

Quest for Aethelgard is a local single-player application. Its primary security
boundaries are save-file parsing, local asset loading, packaged dependencies,
and browser storage when running as a web build.

## Reporting a vulnerability

Do not publish save-file parsing, path traversal, packaged-secret, or remote
code execution vulnerabilities in a public issue first. Contact the repository
maintainer privately through the hosting platform and include reproduction
steps, affected version/commit, impact, and a minimal proof of concept.

## Supported policy

Security fixes target the current default branch. Save parsing rejects invalid
or future schemas, and corrupt desktop saves are preserved for recovery rather
than executed or deserialized unsafely.
