<?php

declare(strict_types=1);

namespace App\Services\Users;

use App\Models\User;
use App\Services\Vk\OutgoingMessage;
use Illuminate\Support\Facades\Log;
use Throwable;

final class SubscriptionStatusService
{
    public function __construct(
        private readonly UserStateService $userStates,
    ) {}

    public function describe(string $peerId): OutgoingMessage
    {
        try {
            $user = User::query()->find($peerId);

            if ($user === null) {
                // Как в legacy StationCheck: при отсутствии пользователя создаём его.
                $this->userStates->resolve($peerId);
                $user = User::query()->find($peerId);
            }

            if ($user === null) {
                return new OutgoingMessage('Ошибка при создании пользователя. Попробуйте позже.');
            }

            $text = "Состояние вашего аккаунта:\n\n📊 Статус: ".$user->status;

            if ($user->status === 'guest') {
                $text .= "\n\n♻ Осталось запросов: ".$user->requests;
            } else {
                $text .= " 👑 \n\n";
                $text .= '⏳Подписка до: '.($user->time_status?->format('d/m/Y') ?? '—');
            }

            return new OutgoingMessage($text);
        } catch (Throwable $e) {
            Log::error('SubscriptionStatusService: '.$e->getMessage(), ['peer_id' => $peerId]);

            return new OutgoingMessage('⚠️Не удалось получить статус подписки. Попробуйте позже.');
        }
    }
}