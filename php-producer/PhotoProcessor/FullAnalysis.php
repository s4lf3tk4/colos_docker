<?php

class FullAnalysis
{
    private string $photoURL;
    private int $peer_id;

    public function __construct(string $photoURL, int $peer_id)
    {
        $this->photoURL = $photoURL;
        $this->peer_id  = $peer_id;
    }

    public function getAnalysis(): array
    {
        $response = (new RabbitRpc())->request($this->photoURL, (string)$this->peer_id);

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

    public function getFullResult(): array
    {
        $result = $this->getAnalysis();

        return [
            'ok'       => $result['ok'] ?? false,
            'text'     => $result['text'] ?? '',
            'keyboard' => KeyboardBuilder::getMainMenuJson(),
        ];
    }
}