FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY core/ ./core/
COPY graph.py graph_init.py main.py rabbitmq.py ./

RUN useradd --create-home --shell /usr/sbin/nologin app && chown -R app:app /app
USER app

CMD ["python", "main.py"]
