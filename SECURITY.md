# Security Policy

## Supported Versions

We actively support the following versions with security updates:

| Version | Supported          |
| ------- | ------------------ |
| latest  | :white_check_mark: |
| < latest| :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability in this repository, please **do not** create a public GitHub issue.

Instead, please report it using one of the following methods:

1. **Email**: Send details to kevin.griesmar@gmail.com
2. **GitHub Security Advisory**: Use the [GitHub Security Advisory](https://github.com/iFocus-Innovations-LLC/cryptotronbot-portfolio/security/advisories/new) feature

### What to Include

When reporting a vulnerability, please include:
- Description of the vulnerability
- Steps to reproduce the issue
- Potential impact
- Suggested fix (if any)
- Your GitHub username (for credit in the security advisory)

### Response Timeline

- **Initial Response**: Within 48 hours
- **Status Update**: Within 7 days
- **Resolution**: As quickly as possible, typically within 30 days depending on severity

## Security Scanning

This repository uses automated security scanning:

- **GitHub Code Scanning (CodeQL)**: Runs on every push and PR
- **Dependabot**: Monitors dependencies for vulnerabilities
- **Bandit**: Python security linter
- **Safety**: Checks for known vulnerabilities in dependencies
- **Secret Scanning**: Detects accidentally committed secrets

## Security Best Practices

### For Contributors

- Never commit secrets, API keys, or passwords
- Use environment variables for sensitive configuration
- Review dependencies before adding new packages
- Follow secure coding practices
- Update dependencies regularly

### For Users

- Keep your instance updated
- Use strong, unique passwords
- Enable 2FA where available
- Review access permissions regularly
- Report security issues responsibly

## Known Security Considerations

- JWT_SECRET_KEY should be set via environment variable in production (not hardcoded)
- Database credentials should use environment variables
- API keys should be stored securely (not in source code)
- Use HTTPS in production environments

## Security Updates

Security updates will be released as:
- **Critical**: Immediately (within 24 hours)
- **High**: Within 7 days
- **Medium**: Within 30 days
- **Low**: Next scheduled release

---

Thank you for helping keep this project secure! 🔒

