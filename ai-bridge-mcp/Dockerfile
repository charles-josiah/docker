FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Instala o binário do Antigravity CLI (agy) -- Go binary único, sem runtime extra
RUN curl -fsSL https://antigravity.google/cli/install.sh | bash
ENV PATH="/root/.local/bin:${PATH}"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py .

EXPOSE 8000

# Healthcheck: só confirma que a porta está aceitando conexões
# (não bate num endpoint autenticado, então não precisa do token aqui)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import socket; socket.create_connection(('localhost', 8000), 3)" || exit 1

CMD ["python", "server.py"]
