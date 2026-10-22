<?php

declare(strict_types=1);

namespace App\Services\Messaging;

use App\Services\Users\SubscriptionStatusService;
use App\Services\Vk\OutgoingMessage;
use App\Services\Vk\ServiceMessages;

final class CommandRegistry
{
    public function __construct(
        private readonly SubscriptionStatusService $subscriptions,
    ) {}

    /**
     * Ключи — текст кнопки в нижнем регистре (mb_strtolower).
     *
     * @return array<string, callable(string): OutgoingMessage>
     */
    public function handlers(): array
    {
        return [
            'начать'                 => static fn (string $peerId): OutgoingMessage => ServiceMessages::start(),
            '📋 получить анализ'     => static fn (string $peerId): OutgoingMessage => ServiceMessages::photoSending(),
            'настройки'              => static fn (string $peerId): OutgoingMessage => ServiceMessages::options(),
            'назад'                  => static fn (string $peerId): OutgoingMessage => ServiceMessages::back(),
            'узнать статус подписки' => fn (string $peerId): OutgoingMessage => $this->subscriptions->describe($peerId),
        ];
    }
}