FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py .

# Vault path — mount your vault here at runtime
# docker run -e ADAM_VAULT_PATH=/vault -v /path/to/your/vault:/vault adam-mcp
ENV ADAM_VAULT_PATH=/vault

CMD ["python", "server.py"]
