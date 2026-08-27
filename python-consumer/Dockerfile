FROM ultralytics/ultralytics:latest

WORKDIR /app

# Копируем все нужные Python-скрипты
COPY core/core.py ./core.py
COPY core/settings.py ./settings.py
COPY serializer.py .
COPY graph_init.py .
COPY rabbitmq.py .
COPY main.py .


# Копируем requirements и устанавливаем
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "main.py"]
