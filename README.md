# 🦞 read-no-evil-mcp

**Secure email access for your AI agent — with prompt injection protection built in.**

Your [Clawbot](https://clawhub.ai) agent can read, send, and manage emails without worrying about prompt injection attacks hiding in message content.

## Features

- 📧 List, read, send, move, and delete emails via a secure gateway
- 🛡️ Automatic prompt injection detection using ML — malicious emails are flagged before your agent sees them
- 🔒 Full credential isolation — your passwords and email connections never touch the AI agent
- ⚙️ Configurable permissions per account (read-only, send, delete, move)
- 🐍 Zero dependencies — pure Python stdlib, no pip install needed

## Install

```bash
clawhub install read-no-evil-mcp
```

Requires a running [read-no-evil-mcp](https://github.com/thekie/read-no-evil-mcp) server (Docker recommended, see server repo for setup).

## Usage

```bash
# List configured email accounts
rnoe-mail.py accounts

# List recent emails
rnoe-mail.py list --limit 10 --days 7

# Read an email (scanned for prompt injection!)
rnoe-mail.py read <uid>

# Send an email
rnoe-mail.py send --to "user@example.com" --subject "Hello" --body "Message"

# List folders
rnoe-mail.py folders

# Move email to a folder
rnoe-mail.py move <uid> --to "Archive"

# Delete an email
rnoe-mail.py delete <uid>
```

## Security

All email content is scanned server-side by an ML model before reaching your agent. If a prompt injection is detected, the email is blocked and the script exits with code 2. Your email credentials never leave the server — the AI agent only sees sanitized content over HTTP.

## Credits

- [read-no-evil-mcp](https://github.com/thekie/read-no-evil-mcp) — The MCP server powering secure email access
- [ProtectAI](https://protectai.com/) — Prompt injection detection model

## License

Apache 2.0 — See [LICENSE](LICENSE)
