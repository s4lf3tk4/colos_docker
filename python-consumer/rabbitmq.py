import aio_pika
from core import RABBITMQ_HOST, RABBITMQ_PORT, RABBITMQ_USER, RABBITMQ_PASS

async def get_connection():
    """Возвращает подключение к RabbitMQ."""
    return await aio_pika.connect_robust(
        host=RABBITMQ_HOST,
        port=RABBITMQ_PORT,
        login=RABBITMQ_USER,
        password=RABBITMQ_PASS
    )

async def declare_queues(channel):
    """Объявляет очереди request_queue и response_queue."""
    await channel.declare_queue("request_queue", durable=True)
    await channel.declare_queue("response_queue", durable=True)
    return await channel.declare_queue("request_queue", durable=True)
