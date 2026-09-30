<?php

use PhpAmqpLib\Connection\AMQPStreamConnection;
use PhpAmqpLib\Channel\AMQPChannel;
use PhpAmqpLib\Exception\AMQPTimeoutException;
use PhpAmqpLib\Message\AMQPMessage;

/**
 * Единственная точка общения с python-consumer по схеме RPC.
 */
final class RabbitRpc
{
    private const REQUEST_QUEUE  = 'request_queue';
    private const RESPONSE_QUEUE = 'response_queue';
    private const WAIT_TIMEOUT   = 60;

    private ?AMQPStreamConnection $connection = null;
    private ?AMQPChannel $channel = null;
    private ?array $response = null;

    private string $host;
    private int $port;
    private string $user;
    private string $pass;

    public function __construct()
    {
        $this->host = (string)getenv('RABBITMQ_HOST');
        $this->port = (int)getenv('RABBITMQ_PORT');
        $this->user = (string)getenv('RABBITMQ_USER');
        $this->pass = (string)getenv('RABBITMQ_PASS');
    }

    /** @return array{ok:bool, result?:array, error?:string} */
    public function request(string $requestText, string $userId): array
    {
        $this->response = null;

        try {
            $this->connection = new AMQPStreamConnection(
                host: $this->host,
                port: $this->port,
                user: $this->user,
                password: $this->pass,
                connection_timeout: 3.0,
                read_write_timeout: 130.0,
                heartbeat: 30
            );
            $this->channel = $this->connection->channel();
            $this->channel->basic_qos(0, 1, false);

            $correlationId = bin2hex(random_bytes(16));

            $this->channel->basic_publish(new AMQPMessage(
                json_encode([
                    'request_text'   => $requestText,
                    'correlation_id' => $correlationId,
                    'user_id'        => $userId,
                ], JSON_UNESCAPED_UNICODE),
                [
                    'correlation_id' => $correlationId,
                    'reply_to'       => self::RESPONSE_QUEUE,
                    'delivery_mode'  => AMQPMessage::DELIVERY_MODE_PERSISTENT,
                ]
            ), '', self::REQUEST_QUEUE);

            $this->waitForResponse($correlationId);

            if ($this->response === null) {
                return ['ok' => false, 'error' => 'Таймаут анализа'];
            }
            if (!isset($this->response['result'])) {
                return ['ok' => false, 'error' => 'Ответ без поля result'];
            }

            return ['ok' => true, 'result' => $this->response['result']];

        } catch (\Throwable $e) {
            error_log('[RabbitRpc] ' . $e->getMessage());
            return ['ok' => false, 'error' => $e->getMessage()];
        } finally {
            $this->closeConnection();
        }
    }

    private function waitForResponse(string $correlationId): void
    {
        $this->channel->basic_consume(
            queue: self::RESPONSE_QUEUE,
            consumer_tag: '',
            no_local: false,
            no_ack: false,
            exclusive: false,
            nowait: false,
            callback: function (AMQPMessage $message) use ($correlationId) {
                if ($message->get('correlation_id') !== $correlationId) {
                    $message->ack();   // чужой ответ: не теряем канал, но и не циклим

                    return;
                }

                if (is_array($decoded = json_decode($message->body, true))) {
                    $this->response = $decoded;
                }
                $message->ack();
            }
        );

        $deadline = microtime(true) + self::WAIT_TIMEOUT;

        while ($this->response === null && microtime(true) < $deadline) {
            try {
                $this->channel->wait(null, false, 1);
            } catch (AMQPTimeoutException $e) {
                continue;
            }
        }
    }

    private function closeConnection(): void
    {
        try {
            $this->channel?->close();
            $this->connection?->close();
        } catch (\Throwable $e) {
            // соединение могло уже быть разорвано
        }
    }
}