<?php

require_once __DIR__ . '/vendor/autoload.php';

use PhpAmqpLib\Connection\AMQPStreamConnection;
use PhpAmqpLib\Message\AMQPMessage;

$host = getenv('RABBITMQ_HOST');
$port = getenv('RABBITMQ_PORT');
$user = getenv('RABBITMQ_USER');
$pass = getenv('RABBITMQ_PASS');

$connection = new AMQPStreamConnection($host, $port, $user, $pass);
$channel = $connection->channel();

$channel->queue_declare('request_queue', false, true, false, false);
$channel->queue_declare('response_queue', false, true, false, false);

$correlationId = uniqid();
$user_id = "hellonigger";

$filePath = $argv[1] ?? '/app/storage/example.jpg';
$messageBody = json_encode([
    'request_text' => $filePath,
    'correlation_id' => $correlationId,
    'user_id' => $user_id
]);

$msg = new AMQPMessage($messageBody, [
    'correlation_id' => $correlationId,
    'reply_to' => 'response_queue',
    'delivery_mode' => AMQPMessage::DELIVERY_MODE_PERSISTENT
]);

$channel->basic_publish($msg, '', 'request_queue');
echo " [x] Задача отправлена, ждём ответ...\n";

$response = null;
$timeout = 60; // секунд
$start = time();

while (time() - $start < $timeout) {
    $message = $channel->basic_get('response_queue', true); // no_ack = true
    if ($message) {
        if ($message->get('correlation_id') === $correlationId) {
            $response = json_decode($message->body, true);
            break;
        }
    }
    usleep(100000); // 0.1 секунды
}
if ($response && isset($response['result'])) {
    $result = $response['result'];
    

    // Вывод размеров
    if (isset($result['sizes']) && is_array($result['sizes']) && !empty($result['sizes'])) {
        echo "Размеры объектов:\n";
        foreach ($result['sizes'] as $size) {
            echo "$size\n";
        }
    } else {
        echo "\n";
    }

    // Вывод калорийности
    if (isset($result['message']) && !empty($result['message'])) {
        echo $result['message'] . "\n";
    }

} else {
    echo " [x] Ответ не получен или имеет неверный формат.\n";
}


$channel->close();
$connection->close();