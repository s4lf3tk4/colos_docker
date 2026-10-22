<?php

declare(strict_types=1);

namespace App\Http\Controllers;

use App\Services\Messaging\MessageHandler;
use Illuminate\Http\Request;
use Illuminate\Http\Response;
use Illuminate\Support\Facades\Log;

final class VkWebhookController
{
    public function __invoke(Request $request, MessageHandler $handler): Response
    {
        $payload = $request->json()->all();

        if ($payload === []) {
            $payload = $request->all();
        }

        if ($payload === []) {
            Log::error('VK webhook: не удалось разобрать тело запроса', [
                'body' => mb_substr($request->getContent(), 0, 1000),
            ]);

            return $this->plain('ok');
        }

        if (! $this->hasValidSecret($payload)) {
            Log::warning('VK webhook: неверный secret', ['type' => $payload['type'] ?? null]);

            return $this->plain('forbidden', 403);
        }

        return match ($payload['type'] ?? null) {
            'confirmation' => $this->plain((string) config('vk.confirmation_code')),
            'message_new'  => $this->handleMessage($payload, $handler),
            default        => $this->plain('ok'),
        };
    }

    /**
     * @param  array<string, mixed>  $payload
     */
    private function handleMessage(array $payload, MessageHandler $handler): Response
    {
        $handler->handle($payload);

        // VK требует "ok" даже при внутренней ошибке, иначе он ретраит событие.
        return $this->plain('ok');
    }

    /**
     * @param  array<string, mixed>  $payload
     */
    private function hasValidSecret(array $payload): bool
    {
        $secret = (string) config('vk.secret');

        if ($secret === '') {
            return true;
        }

        return hash_equals($secret, (string) ($payload['secret'] ?? ''));
    }

    private function plain(string $body, int $status = 200): Response
    {
        return response($body, $status)->header('Content-Type', 'text/plain; charset=utf-8');
    }
}