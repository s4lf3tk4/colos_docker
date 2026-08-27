# import asyncio
# import json
# import sys
# from aio_pika import Message, DeliveryMode

# from core import RABBITMQ_HOST, RABBITMQ_PORT, RABBITMQ_USER, RABBITMQ_PASS
# from rabbitmq import get_connection, declare_queues
# from serializer import convert_to_serializable
# from graph_init import graph_start


# async def main():
#     """
#     Точка входа:
#         - подключается к RabbitMQ;
#         - слушает очередь request_queue;
#         - для каждого сообщения извлекает request, correlation_id, user_id;
#         - вызывает graph_start(request, user_id), который запускает граф;
#         - получаем состояние графа: последний ответ от ии (messages[-1]) и определяемые объекты и размеры (size_info), которые сериализуем;
#         - из результата извлекает текстовый ответ, размеры;
#         - формирует JSON-ответ и отправляет его в response_queue с тем же correlation_id;
#     """
#     connection = await get_connection()
#     async with connection:
#         channel = await connection.channel()
#         queue = await declare_queues(channel)

#         async with queue.iterator() as queue_iter:

#             print("Ожидание сообщений")
#             async for message in queue_iter:
#                 async with message.process(requeue=False):
#                     body = message.body.decode()
#                     try:
#                         data = json.loads(body)
#                     except json.JSONDecodeError:
#                         print(" [!] Получено невалидное JSON-сообщение, пропускаем")
#                         continue

#                     request = data.get("request_text")
#                     correlation_id = data.get("correlation_id")
#                     user_id = data.get("user_id")
#                     if not request or not correlation_id or not user_id:
#                         print(" [!] Сообщение без 'request_text' или 'correlation_id' или 'user_id'")
#                         continue

#                     print(f" [x] Получена задача: {request} (corr_id={correlation_id})")

#                     result = await graph_start(request, user_id)

#                     final_response_ai = result["ai_response"]

#                     response = {
#                         "correlation_id": correlation_id,
#                         "status": "ok",
#                         "result": {
#                             "message": final_response_ai,
#                         }
#                     }

#                     response_body = json.dumps(response, default=convert_to_serializable).encode()
#                     await channel.default_exchange.publish(
#                         Message(
#                             body=response_body,
#                             delivery_mode=DeliveryMode.PERSISTENT,
#                             correlation_id=correlation_id
#                         ),
#                         routing_key="response_queue"
#                     )
#                     print(f" [x] Ответ отправлен для corr_id={correlation_id}")


# if __name__ == "__main__":
#     try:
#         asyncio.run(main())
#     except KeyboardInterrupt:
#         print("Остановка потребителя.")
#         sys.exit(0)

import asyncio
import json
from aio_pika import Message, DeliveryMode
from rabbitmq import get_connection, declare_queues
from serializer import convert_to_serializable
from graph_init import graph_start


MAX_CONCURRENT = 5
semaphore = asyncio.Semaphore(MAX_CONCURRENT)

async def process_message(message, channel):
    """Обработка одного сообщения"""
    async with message.process(requeue=False):
        body = message.body.decode()

        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            print(" [!] Получено невалидное JSON-сообщение, пропускаем")
            return

        request = data.get("request_text")
        correlation_id = data.get("correlation_id")
        user_id = data.get("user_id")

        if not request or not correlation_id or not user_id:
            print(" [!] Сообщение без обязательных полей")
            return

        print(f" [x] Получена задача: {request} (corr_id={correlation_id})")

        try:
            result = await graph_start(request, user_id)
            final_response = result["ai_response"]
        except Exception as e:
            print(f"Ошибка при обработке: {e}")
            final_response = f"Ошибка при обработке: {e}"

        await send_response_to_rabbit(channel, final_response, correlation_id)

async def send_response_to_rabbit(channel, final_response, correlation_id) -> None:
    """Отправка ответа в RabbitMQ"""
    try:
        response = {
            "correlation_id": correlation_id,
            "status": "ok",
            "result": {
                "message": final_response,
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
    except Exception as e:
        print(f"Ошибка при отправке: {e}")

async def main():
    """Главная функция"""
    connection = await get_connection()
    async with connection:
        channel = await connection.channel()

        await channel.set_qos(prefetch_count=MAX_CONCURRENT)

        queue = await declare_queues(channel)

        workers = []
        for i in range(MAX_CONCURRENT):
            worker = asyncio.create_task(worker_loop(i, queue, channel))
            workers.append(worker)

        print(f"Запущено {MAX_CONCURRENT} воркеров")

        await asyncio.gather(*workers)

async def worker_loop(worker_id, queue, channel):
    """Один воркер, который постоянно берет сообщения из очереди"""
    print(f"Воркер {worker_id} запущен")

    async with queue.iterator() as queue_iter:
        async for message in queue_iter:
            try:
                async with semaphore:
                    await process_message(message, channel)
            except asyncio.CancelledError:
                print(f"Воркер {worker_id} остановлен")
                return
            except Exception as e:
                print(f"❌ Воркер {worker_id} ошибка обработки: {e}", flush=True)
                import traceback
                traceback.print_exc()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Остановка потребителя")
