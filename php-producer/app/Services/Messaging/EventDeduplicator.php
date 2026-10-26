<?php

declare(strict_types=1);

namespace App\Services\Messaging;

use Illuminate\Support\Facades\Cache;
use Illuminate\Support\Facades\Log;
use Throwable;

/**
 * VK может доставить одно и то же событие повторно.
 * Ключ живёт в Redis ровно сутки: SET NX (атомарно) + TTL.
 * Первый запрос создаёт ключ и обрабатывается, повторы в течение суток — дубли.
 */
final class EventDeduplicator
{
    private const STORE = 'redis';

    public function __construct(
        private readonly int $ttlSeconds = 86400,
    ) {}

    public function isDuplicate(string $eventId): bool
    {
        if ($eventId === '') {
            return false;
        }

        try {
            // add() атомарно возвращает false, если ключ уже существует — это дубль.
            return ! Cache::store(self::STORE)->add(
                'vk:event:'.$eventId,
                1,
                now()->addSeconds($this->ttlSeconds),
            );
        } catch (Throwable $e) {
            // Redis недоступен — не блокируем обработку, как и раньше.
            Log::warning('EventDeduplicator: Redis недоступен, защита от дублей отключена', [
                'error' => $e->getMessage(),
            ]);

            return false;
        }
    }
}