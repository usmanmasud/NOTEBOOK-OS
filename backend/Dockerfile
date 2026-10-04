# Build context: repository root (needs backend/ and the fictional samples/).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 \
    SAMPLES_DIR=/app/samples LOCAL_STORAGE_DIR=/app/data/uploads
WORKDIR /app

COPY backend/requirements.txt backend/requirements-cloud.txt ./
RUN pip install -r requirements-cloud.txt

COPY backend/ .
COPY samples/ /app/samples/
RUN useradd --create-home --uid 10001 notebookos \
    && mkdir -p /app/data/uploads && chown -R notebookos /app/data
USER notebookos

EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"
CMD ["sh", "./entrypoint.sh"]
