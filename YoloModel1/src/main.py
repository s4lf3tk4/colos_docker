import os
import json
import aio_pika
from aio_pika import Message, DeliveryMode

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", 5672))
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "user")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "password")

async def api_connection():
    connection = await aio_pika.connect_robust(
        host=RABBITMQ_HOST,
        port=RABBITMQ_PORT,
        login=RABBITMQ_USER,
        password=RABBITMQ_PASS
    )
    async with connection:
        channel = await connection.channel()

        # Объявляем очереди (durable)
        await channel.declare_queue("request_queue", durable=True)
        await channel.declare_queue("response_queue", durable=True)

        queue = await channel.declare_queue("request_queue", durable=True)

        async with queue.iterator() as queue_iter:
            print(" [*] Ожидание сообщений... Нажмите CTRL+C для выхода")
            async for message in queue_iter:
                async with message.process(requeue=False):
                    # Декодируем тело
                    body = message.body.decode()
                    try:
                        data = json.loads(body)
                    except json.JSONDecodeError:
                        print(" [!] Получено невалидное JSON-сообщение, пропускаем")
                        continue

                    request = data.get("request_text")
                    correlation_id = data.get("correlation_id")
                    if not request or not correlation_id:
                        print(" [!] Сообщение без 'request_text' или 'correlation_id'")
                        continue

                    print(f" [x] Получена задача: {request} (corr_id={correlation_id})")

                    result = await graph_start(request)

                    # Извлекаем последнее сообщение (текстовый ответ)
                    last_message = result["messages"][-1] if result.get("messages") else None
                    output_text = last_message.content if last_message else ""

                    response = {
                        "correlation_id": correlation_id,
                        "status": "ok",
                        "result": {"message": output_text}
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
