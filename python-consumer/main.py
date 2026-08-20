import asyncio
import json
import sys
from aio_pika import Message, DeliveryMode

from core import RABBITMQ_HOST, RABBITMQ_PORT, RABBITMQ_USER, RABBITMQ_PASS
from rabbitmq import get_connection, declare_queues
from serializer import convert_to_serializable
from graph_init import graph_start


async def main():
    """
    Точка входа:
        - подключается к RabbitMQ;
        - слушает очередь request_queue;
        - для каждого сообщения извлекает request, correlation_id, user_id;
        - вызывает graph_start(request, user_id), который запускает граф;
        - получаем состояние графа: последний ответ от ии (messages[-1]) и определяемые объекты и размеры (size_info), которые сериализуем;
        - из результата извлекает текстовый ответ, размеры;
        - формирует JSON-ответ и отправляет его в response_queue с тем же correlation_id;
    """
    connection = await get_connection()
    async with connection:
        channel = await connection.channel()
        queue = await declare_queues(channel)

        async with queue.iterator() as queue_iter:

            print("Ожидание сообщений")
            async for message in queue_iter:
                async with message.process(requeue=False):
                    body = message.body.decode()
                    try:
                        data = json.loads(body)
                    except json.JSONDecodeError:
                        print(" [!] Получено невалидное JSON-сообщение, пропускаем")
                        continue

                    request = data.get("request_text")
                    correlation_id = data.get("correlation_id")
                    user_id = data.get("user_id")
                    if not request or not correlation_id or not user_id:
                        print(" [!] Сообщение без 'request_text' или 'correlation_id' или 'user_id'")
                        continue

                    print(f" [x] Получена задача: {request} (corr_id={correlation_id})")

                    result = await graph_start(request, user_id)

                    last_message = result["messages"][-1] if result.get("messages") else None
                    output_text = last_message.content if last_message else ""

                    sizes = result.get("size_info", [])

                    # Формируем ответ (уже сериализуемый)
                    response = {
                        "correlation_id": correlation_id,
                        "status": "ok",
                        "result": {
                            "message": output_text,
                            "sizes": sizes,
                        }
                    }

                    response_body = json.dumps(response, default=convert_to_serializable).encode()
                    await channel.default_exchange.publish(
                        Message(
                            body=response_body,
                            delivery_mode=DeliveryMode.PERSISTENT,
                            correlation_id=correlation_id
                        ),
                        routing_key="response_queue"
                    )
                    print(f" [x] Ответ отправлен для corr_id={correlation_id}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Остановка потребителя.")
        sys.exit(0)
