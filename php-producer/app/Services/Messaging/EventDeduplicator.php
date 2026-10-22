<?php

declare(strict_types=1);

namespace App\Services\Messaging;

use Illuminate\Support\Facades\Cache;
use Illuminate\Support\Facades\Log;
use Throwable;

/**
 * VK может доставить одно событие несколько раз. В legacy это решалось
 * JSON-файлом cache/events.json; здесь — атомарный lock файлового кеша на TTL окна.
 */
final class EventDeduplicator
{
    public function __construct(
        private readonly int $ttlSeconds = 60,
    ) {}

    public function isDuplicate(string $eventId): bool
    {
        if ($eventId === '') {
            return false;
        }

        try {
            // Первый, кто взял lock, обрабатывает событие; остальные — дубли.
            return ! Cache::lock('vk:event:'.$eventId, $this->ttlSeconds)->get();
        } catch (Throwable $e) {
            // Ошибка кеша не блокирует обработку (как и в legacy).
            Log::warning('EventDeduplicator: защита от дублей недоступна', ['error' => $e->getMessage()]);

            return false;
        }
    }
}