<?php

use PhpAmqpLib\Connection\AMQPStreamConnection;
use PhpAmqpLib\Message\AMQPMessage;

class TextAnalysis
{
    private string $rabbitHost;
    private int $rabbitPort;
    private string $rabbitUser;
    private string $rabbitPass;
    private int $timeout = 60;
    private string $text;
    private int $peer_id;

    public function __construct(string $text, int $peer_id)
    {
        $this->rabbitHost = getenv('RABBITMQ_HOST');
        $this->rabbitPort = (int)(getenv('RABBITMQ_PORT'));
        $this->rabbitUser = getenv('RABBITMQ_USER');
        $this->rabbitPass = getenv('RABBITMQ_PASS');
        $this->text = $text;
        $this->peer_id = $peer_id;
    }

    public function getAnalysis(): array
    {
        try {
            $connection = new AMQPStreamConnection(
                $this->rabbitHost,
                $this->rabbitPort,
                $this->rabbitUser,
                $this->rabbitPass
            );
            $channel = $connection->channel();

            $channel->queue_declare('request_queue', false, true, false, false);
            $channel->queue_declare('response_queue', false, true, false, false);

            $correlationId = uniqid();

            $messageBody = json_encode([
                'request_text' => $this->text,
                'correlation_id' => $correlationId,
                'user_id' => (string)$this->peer_id
            ]);

            $msg = new AMQPMessage($messageBody, [
                'correlation_id' => $correlationId,
                'reply_to' => 'response_queue',
                'delivery_mode' => AMQPMessage::DELIVERY_MODE_PERSISTENT
            ]);

            $channel->basic_publish($msg, '', 'request_queue');

            $response = null;
            $start = time();

            while (time() - $start < $this->timeout) {
                $message = $channel->basic_get('response_queue', true);
                if ($message) {
                    if ($message->get('correlation_id') === $correlationId) {
                        $response = json_decode($message->body, true);
                        break;
                    }
                }
                usleep(100000);
            }

            $channel->close();
            $connection->close();

            if ($response && isset($response['result'])) {
                $result = $response['result'];
                $output = "";
                if (isset($result['message']) && !empty($result['message'])) {
                    $output .= "\n" . $result['message'] . "\n";
                }
                return ['text' => $output];
            } else {
                return ['text' => "❌ Ответ не получен или имеет неверный формат."];
            }

        } catch (Exception $e) {
            return [
                'text' => "❌ Ошибка при обращении к сервису анализа: " . $e->getMessage()
            ];
        }
    }
}