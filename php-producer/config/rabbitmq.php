<?php

return [
    'host'     => env('RABBITMQ_HOST', 'rabbitmq'),
    'port'     => (int) env('RABBITMQ_PORT', 5672),
    'user'     => env('RABBITMQ_USER', 'guest'),
    'password' => env('RABBITMQ_PASS', 'guest'),
    'vhost'    => env('RABBITMQ_VHOST', '/'),

    'request_queue'  => env('RABBITMQ_REQUEST_QUEUE', 'request_queue'),
    'response_queue' => env('RABBITMQ_RESPONSE_QUEUE', 'response_queue'),

    'connection_timeout' => (float) env('RABBITMQ_CONNECTION_TIMEOUT', 3.0),
    'read_write_timeout' => (float) env('RABBITMQ_READ_WRITE_TIMEOUT', 130.0),
    'heartbeat'          => (int) env('RABBITMQ_HEARTBEAT', 30),

    // Сколько ждём ответ в response_queue.
    'response_timeout' => (int) env('RABBITMQ_RESPONSE_TIMEOUT', 60),
];