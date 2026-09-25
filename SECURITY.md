# Security Policy

## Supported Versions

Security fixes are applied to the latest code on the `main` branch. There are no tagged releases; always use the most recent commit of `main`.

## Reporting a Vulnerability

Please do **not** open a public GitHub issue for an exploitable vulnerability.

Report it privately using GitHub's vulnerability reporting for this repository:

1. Open the repository on GitHub → **Security** tab → **Report a vulnerability**.
2. Include a description, reproduction steps, and the potential impact.

If the private reporting form is not available on this repository, open a normal issue asking to establish a private channel first, without including exploit details.

> Note: this project does not have a dedicated security email. GitHub's private vulnerability reporting is the supported channel.

## Scope

**In scope**

- Authentication and JWT handling (`app/auth/security.py`, `app/api/auth_router.py`)
- Role-based access control bypasses (student / faculty / facilities / admin)
- File upload abuse (`app/api/reports_router.py`): MIME validation, filename handling, size limits
- SQL injection, XSS via Jinja templates, or CSRF affecting the app
- Leakage of `SECRET_KEY` or other configuration into source or logs

**Out of scope**

- Vulnerabilities in third-party dependencies (report upstream)
- Denial of service against demo deployments
- The demo/persona login accounts — they are intentionally fake sample data, not real credentials

## Security Practices for Contributors

- Never commit `.env` or real credentials — only the placeholders in `.env.example`.
- Set `SECRET_KEY` explicitly in any non-local deployment; the random per-process fallback is development-only.
- New endpoints must enforce the existing dependency-injected auth/RBAC checks.
- Upload handlers must keep validating extension, MIME type, and the 10 MB size limit.
