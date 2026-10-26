import logging

import aio_pika
from aio_pika.abc import AbstractChannel, AbstractQueue, AbstractRobustConnection

from core import (
    RABBITMQ_HOST,
    RABBITMQ_PASS,
    RABBITMQ_PORT,
    RABBITMQ_REQUEST_QUEUE,
    RABBITMQ_RESPONSE_QUEUE,
    RABBITMQ_USER,
)

log = logging.getLogger(__name__)


async def connect() -> AbstractRobustConnection:
    log.info("подключаюсь к RabbitMQ %s:%s", RABBITMQ_HOST, RABBITMQ_PORT)
    return await aio_pika.connect_robust(
        host=RABBITMQ_HOST,
        port=RABBITMQ_PORT,
        login=RABBITMQ_USER,
        password=RABBITMQ_PASS,
    )


async def declare_request_queue(channel: AbstractChannel) -> AbstractQueue:
    return await channel.declare_queue(RABBITMQ_REQUEST_QUEUE, durable=True)


async def declare_response_queue(channel: AbstractChannel) -> AbstractQueue:
    return await channel.declare_queue(RABBITMQ_RESPONSE_QUEUE, durable=True)
