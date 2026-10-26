import asyncio
import json
import logging
import os
import signal

from aio_pika import DeliveryMode, Message
from aio_pika.abc import AbstractChannel, AbstractIncomingMessage, AbstractQueue

from core import RABBITMQ_PREFETCH, RABBITMQ_RESPONSE_QUEUE
from core.images import close_session as close_image_session
from core.redis_client import close_redis, ping_redis
from graph import close_llm_session
from graph_init import graph_start
from rabbitmq import connect, declare_request_queue, declare_response_queue

log = logging.getLogger("consumer")

MAX_CONCURRENT = RABBITMQ_PREFETCH
PUBLISH_ATTEMPTS = 2
SHUTDOWN_TIMEOUT = 30.0

ERROR_REPLY = "Сервис анализа временно недоступен. Попробуйте повторить запрос позже."
INVALID_REPLY = "Некорректный запрос: нужны request_text, correlation_id и user_id."
EMPTY_REPLY = "Не удалось получить ответ. Попробуйте переформулировать запрос."


def setup_logging() -> None:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    )


def _correlation_from_properties(message: AbstractIncomingMessage) -> str | None:
    value = message.correlation_id
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def _install_signal_handlers(stop: asyncio.Event) -> None:
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, stop.set)
        except (NotImplementedError, AttributeError):      # Windows
            try:
                signal.signal(sig, lambda *_: loop.call_soon_threadsafe(stop.set))
            except (ValueError, OSError):
                pass


async def publish_response(
    channel: AbstractChannel,
    correlation_id: str | None,
    status: str,
    message: str,
) -> None:
    body = json.dumps(
        {
            "correlation_id": correlation_id,
            "status": status,
            "result": {"message": message},
        },
        ensure_ascii=False,
    ).encode("utf-8")

    last_error: Exception | None = None
    for attempt in range(1, PUBLISH_ATTEMPTS + 1):
        try:
            await channel.default_exchange.publish(
                Message(
                    body=body,
                    content_type="application/json",
                    delivery_mode=DeliveryMode.PERSISTENT,
                    correlation_id=correlation_id,
                ),
                routing_key=RABBITMQ_RESPONSE_QUEUE,
            )
            log.info("ответ отправлен corr=%s status=%s", correlation_id, status)
            return
        except Exception as exc:
            last_error = exc
            log.warning("публикация не удалась (попытка %d/%d): %s",
                        attempt, PUBLISH_ATTEMPTS, exc)
            await asyncio.sleep(0.2 * attempt)

    raise RuntimeError(f"публикация ответа не удалась: {last_error}")


async def _reply_or_requeue(
    message: AbstractIncomingMessage,
    channel: AbstractChannel,
    correlation_id: str | None,
    text: str,
) -> None:
    """Гарантируем клиенту ответ. Если ответ не ушёл — возвращаем сообщение в очередь."""
    try:
        await publish_response(channel, correlation_id, "error", text)
        await message.ack()
    except Exception:
        log.exception("не удалось ответить corr=%s, возвращаю сообщение в очередь", correlation_id)
        await message.nack(requeue=True)


async def handle_message(
    message: AbstractIncomingMessage,
    channel: AbstractChannel,
) -> None:
    correlation_id = _correlation_from_properties(message)

    try:
        payload = json.loads(message.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        log.warning("некорректный JSON corr=%s: %s", correlation_id, exc)
        await _reply_or_requeue(message, channel, correlation_id, INVALID_REPLY)
        return

    if not isinstance(payload, dict):
        log.warning("ожидался объект JSON corr=%s", correlation_id)
        await _reply_or_requeue(message, channel, correlation_id, INVALID_REPLY)
        return

    correlation_id = str(payload.get("correlation_id") or correlation_id or "") or None
    text = payload.get("request_text")
    user_id = payload.get("user_id")

    if (
        correlation_id is None
        or not isinstance(text, str)
        or not text.strip()
        or user_id is None
        or str(user_id) == ""
    ):
        log.warning("некорректное сообщение: corr=%s, поля=%s",
                    correlation_id, sorted(payload))
        await _reply_or_requeue(message, channel, correlation_id, INVALID_REPLY)
        return

    log.info("принято corr=%s uid=%s len=%d", correlation_id, user_id, len(text))

    try:
        result = await graph_start(text.strip(), str(user_id))
        answer = str(result.get("ai_response") or "").strip() or EMPTY_REPLY
        await publish_response(channel, correlation_id, "ok", answer)
        await message.ack()
    except Exception:
        log.exception("ошибка обработки corr=%s", correlation_id)
        await _reply_or_requeue(message, channel, correlation_id, ERROR_REPLY)


async def worker(
    worker_id: int,
    queue: AbstractQueue,
    channel: AbstractChannel,
) -> None:
    log.info("воркер %d запущен", worker_id)
    async with queue.iterator() as iterator:
        async for message in iterator:
            try:
                await handle_message(message, channel)
            except Exception:
                log.exception("воркер %d: необработанная ошибка", worker_id)


async def main() -> None:
    setup_logging()
    stop = asyncio.Event()
    _install_signal_handlers(stop)

    connection = await connect()
    try:
        async with connection:
            publish_channel = await connection.channel()
            await declare_response_queue(publish_channel)

            consume_channel = await connection.channel()
            await consume_channel.set_qos(prefetch_count=MAX_CONCURRENT)
            queue = await declare_request_queue(consume_channel)

            if not await ping_redis():
                log.warning("Redis недоступен: память фото отключена, текст работает")

            workers = [
                asyncio.create_task(worker(index, queue, publish_channel), name=f"worker-{index}")
                for index in range(MAX_CONCURRENT)
            ]
            log.info("запущено %d воркеров (prefetch=%d)", MAX_CONCURRENT, MAX_CONCURRENT)

            stop_waiter = asyncio.create_task(stop.wait(), name="stop-waiter")
            done, _ = await asyncio.wait(
                [*workers, stop_waiter], return_when=asyncio.FIRST_COMPLETED
            )

            if stop_waiter in done:
                log.info("получен сигнал остановки, дожидаюсь текущих сообщений")
            else:
                log.error("воркер завершился аварийно, останавливаю сервис")

            for task in workers:
                task.cancel()
            stop_waiter.cancel()

            try:
                await asyncio.wait_for(
                    asyncio.gather(*workers, stop_waiter, return_exceptions=True),
                    timeout=SHUTDOWN_TIMEOUT,
                )
            except asyncio.TimeoutError:
                log.warning("воркеры не завершились за %.0f с", SHUTDOWN_TIMEOUT)
    finally:
        await close_image_session()
        await close_llm_session()
        await close_redis()
        log.info("потребитель остановлен")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("остановлено пользователем")
