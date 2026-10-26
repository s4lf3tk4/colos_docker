<?php

declare(strict_types=1);

namespace App\Services\Vk;

use Illuminate\Http\Client\ConnectionException;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;

final class VkApiClient
{
    public function __construct(
        private readonly string $token,
        private readonly string $apiVersion,
        private readonly string $apiUrl,
    ) {}

    public static function fromConfig(): self
    {
        return new self(
            token: (string) config('vk.token', ''),
            apiVersion: (string) config('vk.api_version', '5.199'),
            apiUrl: (string) config('vk.api_url', 'https://api.vk.com/method/messages.send'),
        );
    }

    public function sendMessage(int|string $peerId, OutgoingMessage $message): bool
    {
        if (trim($message->text) === '') {
            return false;
        }

        if ($this->token === '') {
            Log::error('VK: не задан VK_TOKEN, сообщение не отправлено', ['peer_id' => $peerId]);

            return false;
        }

        $payload = [
            'access_token' => $this->token,
            'v'            => $this->apiVersion,
            'peer_id'      => $peerId,
            'message'      => $message->text,
            'random_id'    => random_int(1, 2147483647),
        ];

        if ($message->keyboard !== null && $message->keyboard !== '') {
            $payload['keyboard'] = $message->keyboard;
        }

        try {
            $response = Http::asForm()
                ->connectTimeout(5)
                ->timeout(15)
                ->post($this->apiUrl, $payload);
        } catch (ConnectionException $e) {
            Log::error('VK: сетевая ошибка messages.send', ['error' => $e->getMessage()]);

            return false;
        }

        if ($response->failed()) {
            Log::error('VK: HTTP '.$response->status().' от messages.send', [
                'body' => mb_substr($response->body(), 0, 1000),
            ]);

            return false;
        }

        $decoded = $response->json();

        if (is_array($decoded) && isset($decoded['error'])) {
            Log::error('VK: ошибка messages.send', ['error' => $decoded['error']]);

            return false;
        }
        Log::info('VK: messages.send выполнен', ['peer_id' => $peerId]);
        return true;
    }
}