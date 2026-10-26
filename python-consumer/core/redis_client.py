import logging

from redis.asyncio import Redis

from .settings import REDIS_SOCKET_TIMEOUT, REDIS_URL

log = logging.getLogger(__name__)

_redis: Redis | None = None


def get_redis() -> Redis:
    global _redis
    if _redis is None:
        _redis = Redis.from_url(
            REDIS_URL,
            decode_responses=False,          # картинка хранится как bytes
            socket_timeout=REDIS_SOCKET_TIMEOUT,
            socket_connect_timeout=REDIS_SOCKET_TIMEOUT,
            health_check_interval=30,
        )
        log.info("Redis-клиент создан: %s", REDIS_URL)
    return _redis


async def ping_redis() -> bool:
    try:
        await get_redis().ping()
        return True
    except Exception as exc:
        log.warning("Redis недоступен: %s", exc)
        return False


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None
