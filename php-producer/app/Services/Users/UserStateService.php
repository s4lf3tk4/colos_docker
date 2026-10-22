<?php

declare(strict_types=1);

namespace App\Services\Users;

use App\Models\User;
use Illuminate\Support\Facades\Log;
use Throwable;

final class UserStateService
{
    private const DEFAULT_REQUESTS = 5;

    public function resolve(string $peerId): UserState
    {
        try {
            $user = User::query()->find($peerId);

            if ($user === null) {
                User::query()->create([
                    'id'       => $peerId,
                    'status'   => 'guest',
                    'requests' => self::DEFAULT_REQUESTS,
                ]);

                return new UserState('guest', self::DEFAULT_REQUESTS);
            }

            // Подписка действует, пока time_status в будущем; иначе снова guest.
            if ($user->status === 'prem' && $user->time_status !== null && $user->time_status->isFuture()) {
                return new UserState('prem', null);
            }

            return new UserState('guest', (int) $user->requests);
        } catch (Throwable $e) {
            Log::error('UserStateService: не удалось получить состояние пользователя', [
                'peer_id' => $peerId,
                'error'   => $e->getMessage(),
            ]);

            return new UserState('error', null);
        }
    }

    public function decrement(string $peerId): void
    {
        try {
            User::query()
                ->whereKey($peerId)
                ->where('requests', '>', 0)
                ->decrement('requests');
        } catch (Throwable $e) {
            Log::error('UserStateService: не удалось списать запрос', [
                'peer_id' => $peerId,
                'error'   => $e->getMessage(),
            ]);
        }
    }
}