<?php

class TextAnalysis
{
    private string $text;
    private int $peer_id;

    public function __construct(string $text, int $peer_id)
    {
        $this->text = $text;
        $this->peer_id = $peer_id;
    }

    public function getAnalysis(): array
    {
        $response = (new RabbitRpc())->request($this->text, (string)$this->peer_id);

        if (!$response['ok']) {
            return [
                'ok'   => false,
                'text' => '❌ Ошибка при обращении к сервису анализа: ' . $response['error'],
            ];
        }

        $message = $response['result']['message'] ?? '';

        return [
            'ok'   => true,
            'text' => is_string($message) ? $message : json_encode($message, JSON_UNESCAPED_UNICODE),
        ];
    }
}