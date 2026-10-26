# core/images.py
import asyncio
import base64
import ipaddress
import urllib.parse
from io import BytesIO

import aiohttp
from PIL import Image

from .redis_client import get_redis
from .settings import (
    IMAGE_FETCH_TIMEOUT,
    IMAGE_JPEG_QUALITY,
    IMAGE_MAX_BYTES,
    IMAGE_MAX_SIDE,
    IMAGE_TTL,
)

IMG_KEY = "img:{uid}"
ALLOWED_HOSTS = ("userapi.com", "vkuserphoto.ru", "vk.com")

_session: aiohttp.ClientSession | None = None


def session() -> aiohttp.ClientSession:          # одна сессия на процесс
    global _session
    if _session is None or _session.closed:
        _session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=IMAGE_FETCH_TIMEOUT)
        )
    return _session


async def close_session() -> None:               # вызывается из main.py при остановке
    global _session
    if _session is not None and not _session.closed:
        await _session.close()
    _session = None


async def _host_is_public(host: str) -> bool:
    loop = asyncio.get_running_loop()
    try:
        infos = await loop.getaddrinfo(host, None)
    except OSError:
        return False
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            return False
    return True


async def is_allowed_photo_url(url: str) -> bool:
    p = urllib.parse.urlparse(url)
    host = (p.hostname or "").lower()
    if p.scheme not in ("http", "https"):
        return False
    if not any(host == s or host.endswith("." + s) for s in ALLOWED_HOSTS):
        return False
    return await _host_is_public(host)


async def fetch_image(url: str) -> bytes:
    if not await is_allowed_photo_url(url):      # ← был пропущен await
        raise ValueError("Недопустимый источник изображения")

    async with session().get(url) as r:
        if r.status != 200:
            raise ValueError(f"HTTP {r.status}")
        if not (r.content_type or "").startswith("image/"):
            raise ValueError(f"Ожидалось изображение, получено {r.content_type}")

        buf = bytearray()
        async for chunk in r.content.iter_chunked(64 * 1024):
            buf.extend(chunk)
            if len(buf) > IMAGE_MAX_BYTES:
                raise ValueError("Изображение слишком большое")

    return bytes(buf)


def shrink_to_jpeg(
    data: bytes,
    max_size: int = IMAGE_MAX_SIDE,
    quality: int = IMAGE_JPEG_QUALITY,
) -> bytes:
    img = Image.open(BytesIO(data))
    img.load()

    ratio = min(max_size / img.width, max_size / img.height)
    if ratio < 1:
        img = img.resize(
            (int(img.width * ratio), int(img.height * ratio)),
            Image.Resampling.LANCZOS,
        )

    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")

    out = BytesIO()
    img.save(out, format="JPEG", quality=quality, optimize=True)
    return out.getvalue()


async def store_last_image(uid: str, url: str) -> None:
    """Скачивает фото по URL из сообщения VK, сжимает и кладёт JPEG в Redis под uid."""
    raw = await fetch_image(url)
    jpeg = shrink_to_jpeg(raw)
    await get_redis().set(IMG_KEY.format(uid=uid), jpeg, ex=IMAGE_TTL)


async def recall_image(uid: str) -> bytes | None:
    return await get_redis().get(IMG_KEY.format(uid=uid))


def to_data_url(jpeg: bytes) -> str:
    return "data:image/jpeg;base64," + base64.b64encode(jpeg).decode("ascii")
