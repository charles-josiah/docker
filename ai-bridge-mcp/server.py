"""
ai-bridge-mcp
-------------
Servidor MCP (Model Context Protocol) que expõe duas ferramentas:

  - ask_chatgpt(prompt, model, system) -> chama a API da OpenAI
  - ask_agy(prompt)                    -> chama o Gemini via Antigravity CLI (agy) local, login Google

Transporte: Streamable HTTP (exigido pelos conectores remotos do Claude —
STDIO não funciona porque o Claude se conecta a partir da nuvem da
Anthropic, não da sua máquina local).

Autenticação: Bearer token estático via header Authorization, validado em
um middleware Starlette. Simples e suficiente para uso pessoal; para uso
em equipe, trocar por OAuth 2.1 (ver docs do MCP Python SDK).
"""

import json
import logging
import os
import subprocess
import sys

import httpx
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

# ---------------------------------------------------------------------------
# Configuração via variáveis de ambiente
# ---------------------------------------------------------------------------
MCP_BEARER_TOKEN = os.environ.get("MCP_BEARER_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
HOST = os.environ.get("MCP_HOST", "0.0.0.0")
PORT = int(os.environ.get("MCP_PORT", "8000"))

if not MCP_BEARER_TOKEN:
    print("ERRO: defina MCP_BEARER_TOKEN no ambiente antes de subir o servidor.", file=sys.stderr)
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("ai-bridge-mcp")

# ---------------------------------------------------------------------------
# Servidor MCP e ferramentas
# ---------------------------------------------------------------------------
mcp = FastMCP(
    "ai-bridge",
    stateless_http=True,
    # DNS-rebinding protection valida o header Host contra uma lista fixa.
    # Como o Bearer token já protege toda chamada, e a URL do túnel (Cloudflare
    # Quick Tunnel) muda a cada restart do container, desligamos essa checagem
    # em vez de tentar manter a lista de hosts sincronizada.
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
)


@mcp.tool()
async def ask_chatgpt(prompt: str, model: str = "gpt-4o", system: str = "") -> str:
    """Envia uma pergunta para o ChatGPT (OpenAI) e retorna a resposta em texto.

    Use esta ferramenta quando quiser uma segunda opinião, comparar respostas
    ou aproveitar um ponto forte específico do ChatGPT.

    Args:
        prompt: A pergunta ou instrução a enviar.
        model: Modelo da OpenAI a usar (padrão: gpt-4o).
        system: Instrução de sistema opcional para orientar o modelo.
    """
    if not OPENAI_API_KEY:
        return "Erro: OPENAI_API_KEY não configurada no servidor."

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
                json={"model": model, "messages": messages},
            )
    except httpx.RequestError as e:
        logger.error(f"Falha de rede chamando OpenAI: {e}")
        return f"Erro de rede ao chamar a OpenAI: {e}"

    if resp.status_code != 200:
        logger.error(f"OpenAI retornou {resp.status_code}: {resp.text[:500]}")
        return f"Erro da OpenAI ({resp.status_code}): {resp.text[:500]}"

    data = resp.json()
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError):
        return f"Resposta inesperada da OpenAI: {json.dumps(data)[:500]}"


@mcp.tool()
async def ask_agy(prompt: str) -> str:
    """Envia uma pergunta ao Gemini via Antigravity CLI (agy) local no container.

    Usa a cota gratuita do login Google (separada da API paga usada por
    ask_gemini). Sujeita a throttling do free tier -- pode falhar ou
    demorar em uso mais pesado. Requer autenticação prévia via
    'docker exec -it ai-bridge-mcp agy' (uma vez só, token persiste no
    volume montado).

    Args:
        prompt: A pergunta ou instrução a enviar.
    """
    try:
        result = subprocess.run(
            ["agy", "-p", prompt],
            capture_output=True,
            text=True,
            timeout=120,
        )
    except FileNotFoundError:
        return "Erro: 'agy' não encontrado no PATH do container."
    except subprocess.TimeoutExpired:
        return "Erro: agy demorou mais de 120s para responder (timeout)."

    if result.returncode != 0:
        stderr = result.stderr.strip()[:500]
        return f"Erro: agy retornou código {result.returncode}. {stderr}"

    output = result.stdout.strip()
    if not output:
        return "Aviso: agy não retornou nenhum texto (stdout vazio). Talvez precise autenticar: 'docker exec -it ai-bridge-mcp agy'."
    return output


# ---------------------------------------------------------------------------
# Autenticação Bearer + montagem do app HTTP
# ---------------------------------------------------------------------------
class BearerAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        auth_header = request.headers.get("authorization", "")
        expected = f"Bearer {MCP_BEARER_TOKEN}"
        if auth_header != expected:
            logger.warning(f"Tentativa de acesso não autorizada de {request.client.host if request.client else '?'}")
            return JSONResponse({"error": "unauthorized"}, status_code=401)

        return await call_next(request)


app = mcp.streamable_http_app()
app.add_middleware(BearerAuthMiddleware)


if __name__ == "__main__":
    import uvicorn

    logger.info(f"Subindo ai-bridge-mcp em {HOST}:{PORT} (path /mcp)")
    uvicorn.run(app, host=HOST, port=PORT)
