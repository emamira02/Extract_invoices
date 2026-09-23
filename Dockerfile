FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app.py ./
COPY invoice_extractor/ ./invoice_extractor/
COPY ui/ ./ui/
COPY sample_data/ ./sample_data/
COPY .streamlit/config.toml ./.streamlit/config.toml

RUN useradd --create-home appuser && mkdir -p /app/data && chown appuser /app/data
USER appuser
ENV HISTORY_DB_PATH=/app/data/history.db

EXPOSE 8501
HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')"
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501"]
