#!/usr/bin/env python3
"""
MCP HTTP client for read-no-evil-mcp secure email access.
Speaks the MCP Streamable HTTP protocol to a remote server.

Zero dependencies — uses only Python stdlib (3.8+).

Usage:
    rnoe-mail.py accounts
    rnoe-mail.py list [--limit N] [--days N]
    rnoe-mail.py read <uid>
    rnoe-mail.py send --to ADDR --subject SUBJ --body BODY [--cc ADDR]
    rnoe-mail.py folders
    rnoe-mail.py move <uid> --to FOLDER
    rnoe-mail.py delete <uid>
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request


class McpClient:
    """Minimal MCP Streamable HTTP client using only stdlib."""

    def __init__(self, server_url):
        self.server_url = server_url.rstrip("/")
        self.endpoint = self.server_url + "/mcp"
        self.session_id = None
        self._id_counter = 0

    def _next_id(self):
        self._id_counter += 1
        return self._id_counter

    def _post(self, payload):
        """POST JSON to the MCP endpoint. Returns (parsed_body, headers)."""
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.endpoint,
            data=data,
            headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream"},
        )
        if self.session_id:
            req.add_header("Mcp-Session-Id", self.session_id)

        try:
            resp = urllib.request.urlopen(req)
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {e.code}: {body}")
        except urllib.error.URLError as e:
            raise ConnectionError(f"Cannot connect to {self.server_url}: {e.reason}")

        headers = resp.headers
        content_type = headers.get("Content-Type", "")
        raw = resp.read().decode("utf-8")

        if "text/event-stream" in content_type:
            parsed = self._parse_sse(raw)
        else:
            parsed = json.loads(raw) if raw.strip() else {}

        return parsed, headers

    @staticmethod
    def _parse_sse(raw):
        """Parse SSE stream, return the last JSON-RPC message with a result or error."""
        last_message = None
        for line in raw.splitlines():
            if line.startswith("data:"):
                payload = line[len("data:"):].strip()
                if payload:
                    try:
                        msg = json.loads(payload)
                        if "result" in msg or "error" in msg:
                            last_message = msg
                    except json.JSONDecodeError:
                        continue
        return last_message or {}

    def initialize(self):
        """Send MCP initialize + initialized notification."""
        init_req = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "rnoe-mail", "version": "0.3.0"},
            },
        }
        resp, headers = self._post(init_req)
        sid = headers.get("Mcp-Session-Id")
        if sid:
            self.session_id = sid

        # Send initialized notification (no id = notification)
        notif = {"jsonrpc": "2.0", "method": "notifications/initialized"}
        try:
            self._post(notif)
        except Exception:
            pass  # Notifications may return empty or 204

    def call_tool(self, name, arguments=None):
        """Call an MCP tool. Returns (text, is_error)."""
        req = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments or {}},
        }
        resp, _ = self._post(req)

        if "error" in resp:
            err = resp["error"]
            return err.get("message", str(err)), True

        result = resp.get("result", {})
        is_error = result.get("isError", False)

        # Extract text from content array
        content = result.get("content", [])
        texts = []
        for item in content:
            if item.get("type") == "text":
                texts.append(item.get("text", ""))
        text = "\n".join(texts) if texts else ""
        return text, is_error

    def close(self):
        """No persistent connection to close with HTTP transport."""
        pass


def detect_prompt_injection(text):
    """Check if server response indicates a blocked prompt injection."""
    if not text:
        return False
    lower = text.lower()
    return "blocked:" in lower and "prompt injection" in lower


def cmd_accounts(client, _args):
    text, is_error = client.call_tool("list_accounts")
    if is_error:
        print(text, file=sys.stderr)
        sys.exit(1)
    print(text)


def cmd_list(client, args):
    arguments = {"account": args.account, "folder": args.folder}
    if args.limit:
        arguments["limit"] = args.limit
    if args.days:
        arguments["days_back"] = args.days
    text, is_error = client.call_tool("list_emails", arguments)
    if is_error:
        print(text, file=sys.stderr)
        sys.exit(1)
    print(text)


def cmd_read(client, args):
    arguments = {"account": args.account, "folder": args.folder, "uid": args.uid}
    text, is_error = client.call_tool("get_email", arguments)
    if is_error:
        if detect_prompt_injection(text):
            print(text, file=sys.stderr)
            sys.exit(2)
        print(text, file=sys.stderr)
        sys.exit(1)
    if detect_prompt_injection(text):
        print(text, file=sys.stderr)
        sys.exit(2)
    print(text)


def cmd_send(client, args):
    arguments = {
        "account": args.account,
        "to": [x.strip() for x in args.to.split(",")],
        "subject": args.subject,
        "body": args.body,
    }
    if args.cc:
        arguments["cc"] = [x.strip() for x in args.cc.split(",")]
    text, is_error = client.call_tool("send_email", arguments)
    if is_error:
        print(text, file=sys.stderr)
        sys.exit(1)
    print(text)


def cmd_folders(client, args):
    arguments = {"account": args.account}
    text, is_error = client.call_tool("list_folders", arguments)
    if is_error:
        print(text, file=sys.stderr)
        sys.exit(1)
    print(text)


def cmd_move(client, args):
    arguments = {
        "account": args.account,
        "folder": args.folder,
        "uid": args.uid,
        "target_folder": args.to,
    }
    text, is_error = client.call_tool("move_email", arguments)
    if is_error:
        print(text, file=sys.stderr)
        sys.exit(1)
    print(text)


def cmd_delete(client, args):
    arguments = {"account": args.account, "folder": args.folder, "uid": args.uid}
    text, is_error = client.call_tool("delete_email", arguments)
    if is_error:
        print(text, file=sys.stderr)
        sys.exit(1)
    print(text)


def resolve_server_url(args):
    """Resolve server URL from CLI flag, env var, or default."""
    if args.server:
        return args.server
    url = os.environ.get("RNOE_SERVER_URL")
    if url:
        return url
    return "http://localhost:8000"


def main():
    parser = argparse.ArgumentParser(
        description="Secure email access via MCP server with prompt injection protection"
    )
    parser.add_argument("--server", help="MCP server URL (default: http://localhost:8000)")
    parser.add_argument("--account", "-a", default="default", help="Account ID (default: default)")
    parser.add_argument("--folder", "-f", default="INBOX", help="Folder (default: INBOX)")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # accounts
    subparsers.add_parser("accounts", help="List configured accounts")

    # list
    list_parser = subparsers.add_parser("list", help="List emails")
    list_parser.add_argument("--limit", "-n", type=int, default=20, help="Max emails (default: 20)")
    list_parser.add_argument("--days", "-d", type=int, default=30, help="Lookback days (default: 30)")

    # read
    read_parser = subparsers.add_parser("read", help="Read an email")
    read_parser.add_argument("uid", type=int, help="Email UID")

    # send
    send_parser = subparsers.add_parser("send", help="Send an email")
    send_parser.add_argument("--to", required=True, help="Recipient(s), comma-separated")
    send_parser.add_argument("--subject", "-s", required=True, help="Subject")
    send_parser.add_argument("--body", "-b", required=True, help="Body text")
    send_parser.add_argument("--cc", help="CC recipient(s), comma-separated")

    # folders
    subparsers.add_parser("folders", help="List folders")

    # move
    move_parser = subparsers.add_parser("move", help="Move email to folder")
    move_parser.add_argument("uid", type=int, help="Email UID")
    move_parser.add_argument("--to", required=True, help="Target folder")

    # delete
    delete_parser = subparsers.add_parser("delete", help="Delete an email")
    delete_parser.add_argument("uid", type=int, help="Email UID")

    args = parser.parse_args()

    server_url = resolve_server_url(args)

    client = McpClient(server_url)
    try:
        client.initialize()
    except ConnectionError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    commands = {
        "accounts": cmd_accounts,
        "list": cmd_list,
        "read": cmd_read,
        "send": cmd_send,
        "folders": cmd_folders,
        "move": cmd_move,
        "delete": cmd_delete,
    }

    try:
        commands[args.command](client, args)
    except ConnectionError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        client.close()


if __name__ == "__main__":
    main()
