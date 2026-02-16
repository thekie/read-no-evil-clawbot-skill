# OpenClaw Skill: read-no-evil-mcp

Secure email access for [OpenClaw](https://github.com/openclaw/openclaw) with prompt injection protection.

Uses [read-no-evil-mcp](https://github.com/thekie/read-no-evil-mcp) to scan emails for prompt injection attacks before your AI agent sees them.

## Features

- Secure email access: list, read, send, move, and delete emails
- Automatic prompt injection detection (server-side ML scanning)
- Full credential isolation — the AI agent never sees passwords or email server connections
- Zero dependencies — uses only Python stdlib (3.8+)

## Architecture

This skill is a thin HTTP client that speaks the [MCP Streamable HTTP protocol](https://modelcontextprotocol.io/) to a read-no-evil-mcp server. All email operations, credential management, and prompt injection scanning happen on the server side.

```
OpenClaw Agent  -->  rnoe-mail.py (HTTP client)  -->  read-no-evil-mcp server  -->  IMAP/SMTP
```

## Installation

### Via OpenClaw Hub
```bash
openclaw install read-no-evil-mcp
```

### Manual
```bash
git clone https://github.com/thekie/read-no-evil-openclaw-skill.git ~/.openclaw/skills/read-no-evil-mcp
```

No `pip install` required.

## Configuration

Before starting the server, create a config file for your email accounts:

```bash
# Interactive wizard — creates ~/.config/read-no-evil-mcp/config.yaml
scripts/setup-config.py create

# Add another account to existing config
scripts/setup-config.py add

# List configured accounts
scripts/setup-config.py list

# Remove an account
scripts/setup-config.py remove <account-id>

# Show full config
scripts/setup-config.py show
```

The wizard includes provider presets for Gmail, Outlook, and Yahoo with auto-detected IMAP/SMTP settings. It will also offer to create a `.env` file with password placeholder variables.

Passwords are never stored in the config file. They are passed as environment variables:
```
RNOE_ACCOUNT_<UPPERCASE_ID>_PASSWORD=your-app-password
```

## Server Setup

You need a running read-no-evil-mcp server. Three options:

### Option 1: Docker (recommended)

Run the interactive setup script:

```bash
scripts/setup-server.sh
```

This will:
1. Pull the official Docker image (`ghcr.io/thekie/read-no-evil-mcp:latest`)
2. Prompt for your config file path and email credentials
3. Start a container on port 8000

### Option 2: Existing server

If you already have a server running (locally or remotely), just point the skill at it:

```bash
# Local server on default port
rnoe-mail.py list

# Remote server
rnoe-mail.py --server http://myserver:8000 list

# Or set the env var
export RNOE_SERVER_URL=http://myserver:8000
rnoe-mail.py list
```

### Option 3: Run the server directly

See the [read-no-evil-mcp docs](https://github.com/thekie/read-no-evil-mcp) for running the server without Docker.

## Usage

```bash
# List accounts configured on the server
rnoe-mail.py accounts

# List recent emails
rnoe-mail.py list
rnoe-mail.py list --limit 10 --days 7

# Read email (scanned for prompt injection)
rnoe-mail.py read <uid>

# Send email
rnoe-mail.py send --to "user@example.com" --subject "Hello" --body "Message"

# List folders
rnoe-mail.py folders

# Move email to folder
rnoe-mail.py move <uid> --to "Archive"

# Delete email
rnoe-mail.py delete <uid>
```

## Server URL Resolution

The server URL is resolved in this order:

1. `--server URL` CLI flag
2. `RNOE_SERVER_URL` environment variable
3. Default: `http://localhost:8000`

## Security

- **Credential isolation**: Email passwords and server connections live only on the MCP server. The AI agent and this skill never have access to them.
- **Prompt injection protection**: All email content is scanned by the server's ML model before being returned to the client.
- **HTTPS warning**: The script warns if you use plain HTTP with a non-localhost server.

## Credits

- [read-no-evil-mcp](https://github.com/thekie/read-no-evil-mcp) — The MCP server for secure email access
- [ProtectAI](https://protectai.com/) — Prompt injection detection model

## License

Apache 2.0 — See [LICENSE](LICENSE)
