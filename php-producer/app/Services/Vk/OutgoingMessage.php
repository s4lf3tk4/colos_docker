<?php

declare(strict_types=1);

namespace App\Services\Vk;

final class OutgoingMessage
{
    public function __construct(
        public readonly string $text,
        public readonly ?string $keyboard = null,
    ) {}
}