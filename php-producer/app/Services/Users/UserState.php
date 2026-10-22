<?php

declare(strict_types=1);

namespace App\Services\Users;

final class UserState
{
    public function __construct(
        public readonly string $status,
        public readonly ?int $requests,
    ) {}

    public function canMakeRequest(): bool
    {
        return $this->status === 'prem' || ($this->requests ?? 0) > 0;
    }

    public function isGuest(): bool
    {
        return $this->status === 'guest';
    }
}