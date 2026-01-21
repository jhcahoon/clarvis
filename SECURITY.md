# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.x.x   | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability in Clarvis, please report it responsibly:

1. **Do NOT** open a public GitHub issue for security vulnerabilities
2. Email security concerns to the maintainer (see GitHub profile for contact)
3. Include as much detail as possible:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

You can expect:
- Acknowledgment within 48 hours
- Status update within 7 days
- Credit in the security advisory (if desired)

## Security Considerations

### API Keys and Credentials

- **Never commit API keys** to version control
- Store all secrets in `.env` (which is gitignored)
- Required API keys are documented in `.env.example`
- Use environment variables for sensitive configuration

### Email Security

The Gmail Agent operates in **read-only mode** by default:
- Send, delete, and modify operations are blocked
- Only read operations are permitted
- OAuth tokens are stored locally in `~/.gmail-mcp/`

### Network Security

- The Clarvis API server binds to `0.0.0.0:8000` by default
- **Do NOT** expose the API server directly to the internet
- Keep the server behind a firewall on your local network
- Use Home Assistant's authentication for external access

### Home Assistant Integration

- The custom component communicates with the local Clarvis API
- API host and port are configurable during setup
- No external cloud services are required for core functionality

### Local Data Storage

- Notes and reminders are stored locally in `~/.clarvis/notes/`
- Gmail credentials are stored locally in `~/.gmail-mcp/`
- No user data is sent to external servers except via API calls to:
  - Anthropic (Claude API)
  - Google (Gmail API)

### Best Practices

1. **Rotate API keys** periodically
2. **Use least-privilege access** for all integrations
3. **Keep dependencies updated** with `uv sync`
4. **Review OAuth scopes** - Gmail integration only needs read access
5. **Monitor API usage** via Anthropic and Google dashboards

## Dependency Security

We use:
- `uv` for reproducible dependency resolution
- `ruff` for code linting including security checks
- Dependabot (if enabled) for dependency updates

To check for known vulnerabilities:
```bash
# Check dependencies
pip-audit
```
