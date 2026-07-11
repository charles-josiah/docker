# ai-bridge-mcp

An MCP (Model Context Protocol) server that gives Claude two tools:

- **`ask_chatgpt`** — calls the OpenAI API (ChatGPT) directly.
- **`ask_agy`** — calls Google's Gemini through the [Antigravity CLI](https://antigravity.google) (`agy`), running locally inside the container and authenticated with a personal Google login (separate free-tier quota from the paid API).

This lets Claude pull in a second opinion from another model mid-conversation — e.g. "ask ChatGPT what it thinks about this" — without leaving the chat.

## Why two different backends for Gemini?

`ask_chatgpt` uses OpenAI's standard pay-as-you-go API. There's no equivalent `ask_gemini` over the Gemini API here on purpose: without billing enabled on the Google Cloud project behind the key, every call returns `429 insufficient_quota`. `ask_agy` sidesteps that by shelling out to the Antigravity CLI, which authenticates via your personal Google account and draws from a separate (free-tier) quota pool instead of the billed API. It's subject to that tier's own throttling, but it's a real, working alternative when you don't want to enable API billing.

## Architecture

```
Claude Desktop (your machine)
      │  mcp-remote (local process, spawned by Desktop)
      │  Tailscale (private network)
      ▼
OCI instance (or any Docker host reachable over your private network)
      │
      ▼
ai-bridge-mcp container
  ├── Streamable HTTP server (FastMCP + Starlette), port 8000
  ├── Bearer token auth on every request
  ├── ask_chatgpt → https://api.openai.com
  └── ask_agy → local `agy` binary → Google OAuth session
```

### Important: this is not a public Custom Connector

Claude's **Custom Connectors** (the ones added via Settings → Connectors in claude.ai, Claude Desktop, or Cowork) connect from **Anthropic's cloud infrastructure**, not from your device. That means a connector server needs to be reachable from the public internet — a private IP (Tailscale, VPC, LAN) will never work there, no matter the firewall rules.

This project intentionally does **not** use that mechanism. Instead, it's wired into `claude_desktop_config.json` via [`mcp-remote`](https://www.npmjs.com/package/mcp-remote), which spawns a small bridge process **on your own machine**. That process is what actually talks to the server over HTTP — so it can use your private network (Tailscale, VPN, LAN) exactly like any other app on your device would. The trade-off: this only works in the **Claude Desktop app**, on the specific machine where you configured it — not in the browser, mobile, or Cowork.

If you do want a public Custom Connector instead, you'd need the server reachable from the internet (e.g. behind a real public IP + HTTPS, or a tunnel like Cloudflare Tunnel), with the Bearer token as the only thing standing between the internet and your tools.

## Deploy

```bash
git clone <this repo>
cd ai-bridge-mcp

cp .env.example .env
# edit .env:
#   - generate MCP_BEARER_TOKEN with: openssl rand -hex 32
#   - fill in OPENAI_API_KEY (platform.openai.com/api-keys)

docker compose up -d --build
docker compose logs -f
```

The server listens on port `8000`, path `/mcp` (e.g. `http://<host>:8000/mcp`).

## One-time setup: authenticating `agy`

`ask_agy` needs a Google login inside the container. This step is interactive and can't be automated — do it once:

```bash
docker exec -it ai-bridge-mcp agy
```

This will detect the headless/remote environment and print a Google sign-in URL. Open it in your own browser, log in, and paste back the code or callback URL when prompted. The resulting token is written to `~/.gemini` inside the container, which is mounted as the `agy_config` named volume — so it survives rebuilds and restarts. You only need to do this once per volume.

Quick test after authenticating:

```bash
docker exec -it ai-bridge-mcp agy -p "hello, who are you?"
```

## Configuring Claude Desktop

Add this to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "ai-bridge": {
      "command": "npx",
      "args": [
        "mcp-remote@latest",
        "http://<host>:8000/mcp",
        "--allow-http",
        "--header",
        "Authorization:${AUTH_HEADER}"
      ],
      "env": {
        "AUTH_HEADER": "Bearer <your MCP_BEARER_TOKEN>"
      }
    }
  }
}
```

Use `--allow-http` only if you're on a private/encrypted network already (Tailscale, VPN) where an extra TLS layer would be redundant. Restart Claude Desktop after editing the config.

**Note on tool list caching:** the set of tools available to a conversation is fetched once, early in that conversation's lifetime. If you add or rename a tool on the server, existing conversations won't see the change — start a new conversation to pick up the current tool list.

## Testing without Claude Desktop

Use the official [MCP Inspector](https://github.com/modelcontextprotocol/inspector) to validate the server directly:

```bash
npx @modelcontextprotocol/inspector
```

Pick "Streamable HTTP" transport, point it at `http://localhost:8000/mcp`, and set the `Authorization` header manually under Auth Settings.

## Costs

- `ask_chatgpt` draws from your OpenAI API billing — a few cents per question at typical usage.
- `ask_agy` draws from the Antigravity CLI's own quota (tied to your Google account tier), separate from any Anthropic or OpenAI billing.

## Security notes

- Every request requires the exact `Authorization: Bearer <token>` header — anything else gets `401`.
- DNS-rebinding protection (Host header validation) is intentionally disabled in `server.py`, since the Bearer token is the real access control here and the reachable hostname/IP can vary (Tailscale IP, tunnel hostname, etc).
- Treat `MCP_BEARER_TOKEN`, `OPENAI_API_KEY`, and the `agy_config` volume's contents as secrets. Never commit `.env` or paste real values into chat with any AI assistant, including Claude.

## Project structure

```
ai-bridge-mcp/
├── server.py           # MCP server (FastMCP + Starlette + Bearer auth + agy subprocess)
├── requirements.txt
├── Dockerfile           # installs Python deps + the agy binary
├── docker-compose.yml   # persists agy's auth token via a named volume
├── .env.example
└── README.md
```
