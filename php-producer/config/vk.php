<?php

return [
    'confirmation_code' => env('VK_CONFIRMATION_CODE', ''),
    'token'             => env('VK_TOKEN', ''),
    'api_version'       => env('VK_API_VERSION', '5.199'),
    'api_url'           => env('VK_MESSAGES_URL', 'https://api.vk.com/method/messages.send'),

    // Если задан — проверяем поле secret во входящем событии.
    'secret' => env('VK_SECRET'),

        // Окно защиты от повторной доставки события: сутки.
    'event_dedupe_seconds' => (int) env('VK_EVENT_DEDUPE_SECONDS', 86400),
];