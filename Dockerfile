FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY axiom ./axiom
RUN pip install --no-cache-dir .
EXPOSE 8765
CMD ["axiom", "daemon"]
