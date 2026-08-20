<?php


use PhpAmqpLib\Connection\AMQPStreamConnection;
use PhpAmqpLib\Message\AMQPMessage;

class FullAnalysis extends AbstractPhotoAnalysis
{
    private string $rabbitHost;
    private int $rabbitPort;
    private string $rabbitUser;
    private string $rabbitPass;
    private int $timeout = 60;

    public function __construct(string $photoURL, int $peer_id)
    {
        parent::__construct($photoURL, $peer_id);

        $this->rabbitHost = getenv('RABBITMQ_HOST');
        $this->rabbitPort = (int)(getenv('RABBITMQ_PORT'));
        $this->rabbitUser = getenv('RABBITMQ_USER');
        $this->rabbitPass = getenv('RABBITMQ_PASS');
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

            // Объявляем очереди (durable)
            $channel->queue_declare('request_queue', false, true, false, false);
            $channel->queue_declare('response_queue', false, true, false, false);

            // Генерируем уникальный ID для запроса
            $correlationId = uniqid();

            // Формируем сообщение
            $messageBody = json_encode([
                'request_text' => $this->photoURL,
                'correlation_id' => $correlationId,
                'user_id' => (string)$this->peer_id // передаём ID пользователя
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
                $message = $channel->basic_get('response_queue', true); // no_ack = true
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

                if (isset($result['sizes']) && is_array($result['sizes']) && !empty($result['sizes'])) {
                    $output .= "Размеры объектов:\n";
                    foreach ($result['sizes'] as $size) {
                        $output .= "$size\n";
                    }
                }

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
    public function getRecommendations(): array { return []; }
    public function getHealthRating(): array { return []; }     
}