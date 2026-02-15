# Security Policy

## 🔒 Reporting a Vulnerability

We take the security of this project seriously. If you discover a security vulnerability, please follow these steps:

### How to Report

**DO NOT** create a public GitHub issue for security vulnerabilities.

Instead, please report security issues by:

1. **Email**: Send details to the repository maintainer
2. **GitHub Security Advisory**: Use GitHub's private vulnerability reporting feature

### What to Include

When reporting a vulnerability, please provide:

- **Description** of the vulnerability
- **Steps to reproduce** the issue
- **Potential impact** of the vulnerability
- **Suggested fix** (if you have one)
- Your **contact information** for follow-up

### Response Timeline

- **Initial Response**: Within 48 hours
- **Status Update**: Within 7 days
- **Fix Timeline**: Depends on severity
  - Critical: 7-14 days
  - High: 14-30 days
  - Medium: 30-90 days

## 🛡️ Security Best Practices

### Credentials Management

- **Never commit credentials** to the repository
- Use `.env` file for sensitive data (already in `.gitignore`)
- Rotate credentials regularly
- Use strong, unique passwords

### Environment Variables

The following sensitive variables should be kept secure:

- `CASINO_USERNAME` - Casino account username
- `CASINO_PASSWORD` - Casino account password
- `TELEGRAM_BOT_TOKEN` - Telegram bot authentication token
- `TELEGRAM_CHAT_ID` - Telegram chat identifier

### Session Management

- `storage_state.json` contains browser cookies and session data
- This file is in `.gitignore` - **never commit it**
- Session files should be stored securely
- Rotate sessions periodically

### API Security

If using the API server:

- Configure `CORS_ORIGINS` appropriately in `.env`
- Use HTTPS in production
- Implement rate limiting for public APIs
- Validate all input data

### Deployment Security

When deploying to production:

- Use firewalls to restrict access
- Keep system packages updated
- Use SSL/TLS certificates
- Implement monitoring and alerting
- Regular security audits

## 🔍 Security Auditing

### Automated Checks

This project uses:

- **pip-audit** - Scans Python dependencies for known vulnerabilities
- **ruff** - Lints code for potential security issues
- **GitHub Actions CI** - Runs security checks on every push

### Running Security Audits

```bash
# Check for vulnerable dependencies
pip-audit -r requirements.txt

# Scan code for security issues
ruff check .

# Check for hardcoded secrets (if bandit is installed)
bandit -r src/
```

## 🚨 Known Security Considerations

### Casino Terms of Service

- This scraper may violate casino terms of service
- Use at your own risk
- The tool is for educational purposes only

### Data Privacy

- Casino credentials are stored locally only
- No data is sent to third parties (except Telegram notifications if configured)
- Database contains game results only

### Browser Automation

- Playwright stores session data in `browser_data/` directory
- This directory may contain sensitive cookies
- Ensure proper file permissions

## 📋 Security Checklist

Before deploying to production:

- [ ] All credentials are in `.env` file (not hardcoded)
- [ ] `.env` is in `.gitignore`
- [ ] `storage_state.json` is in `.gitignore`
- [ ] CORS is properly configured
- [ ] Firewall rules are set up
- [ ] SSL/TLS is configured (if using HTTPS)
- [ ] Dependencies are up to date
- [ ] Security audit has been run
- [ ] Logs don't contain sensitive data
- [ ] Error messages don't expose internal details

## 🔐 Dependency Security

We regularly update dependencies to address security vulnerabilities.

### Current Security Status

- All dependencies are scanned with `pip-audit`
- Known vulnerabilities are tracked and resolved
- See CI/CD pipeline for latest security scan results

### Updating Dependencies

```bash
# Update all dependencies
pip install --upgrade -r requirements.txt

# Run security audit
pip-audit -r requirements.txt

# Test after updates
pytest -q
```

## 📞 Contact

For security concerns, please contact the repository maintainers through:

- GitHub Security Advisory
- Repository issues (for non-sensitive security discussions)

## 📄 Scope

This security policy applies to:

- Latest version on main branch
- Supported release versions
- All code in the repository

## ⚖️ Responsible Disclosure

We request that security researchers:

- Give us reasonable time to address vulnerabilities before public disclosure
- Do not access or modify data that doesn't belong to you
- Do not perform testing on production systems
- Respect user privacy

Thank you for helping keep this project secure! 🙏
