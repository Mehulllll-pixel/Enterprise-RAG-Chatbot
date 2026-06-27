# Security Policy

We take the security of the Enterprise RAG Chatbot seriously. Please review the security policy below for guidance on reporting vulnerabilities.

---

## Supported Versions

Only the latest release version on the `master` branch receives active security updates and patches.

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

**Do not report security vulnerabilities via public GitHub issues.**

If you discover a vulnerability, please report it privately through one of the following methods:
1.  **Email:** Send a detailed description of the vulnerability to `security@enterprise-rag.ai`.
2.  **Encrypted Message:** Include a proof of concept (PoC), steps to reproduce the issue, and potential impacts.

We will acknowledge receipt of your report within **48 hours** and provide a timeline for coordination and resolution.

## Security Practices

*   **Dependency Audits:** All backend python dependencies and frontend node modules are regularly scanned for vulnerabilities.
*   **Encrypted Secrets:** Production environment variables and encryption keys should always be managed securely and never committed to source control.
