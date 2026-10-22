<?php

declare(strict_types=1);

namespace App\Services\Analysis;

use App\Services\Rabbit\RabbitRpcClient;

/**
 * Фото и текст идут одним путём: значение (URL картинки либо текст)
 * уходит в request_queue как request_text, ответ берётся из result.message.
 */
final class AnalysisService
{
    public function __construct(
        private readonly RabbitRpcClient $rpc,
    ) {}

    public function analyze(string $input, string $userId): AnalysisResponse
    {
        $response = $this->rpc->request($input, $userId);

        if (! $response['ok']) {
            return new AnalysisResponse(
                false,
                '❌ Ошибка при обращении к сервису анализа: '.$response['error'],
            );
        }

        $message = $response['result']['message'] ?? '';

        $text = is_string($message)
            ? $message
            : (string) json_encode($message, JSON_UNESCAPED_UNICODE);

        return new AnalysisResponse(true, $text);
    }
}