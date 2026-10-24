FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY axiom ./axiom
RUN pip install --no-cache-dir .
EXPOSE 8765
CMD ["axiom", "daemon", "--host", "0.0.0.0", "--port", "8765", "--allow-network"]
