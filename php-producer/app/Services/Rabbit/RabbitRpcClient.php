<?php

declare(strict_types=1);

namespace App\Services\Rabbit;

use Illuminate\Support\Facades\Log;
use PhpAmqpLib\Channel\AMQPChannel;
use PhpAmqpLib\Connection\AMQPStreamConnection;
use PhpAmqpLib\Exception\AMQPTimeoutException;
use PhpAmqpLib\Message\AMQPMessage;
use RuntimeException;
use Throwable;

/**
 * Единственная точка общения с python-consumer (RPC поверх request_queue/response_queue).
 */
final class RabbitRpcClient
{
    private ?AMQPStreamConnection $connection = null;

    private ?AMQPChannel $channel = null;

    /** @var array<string, mixed>|null */
    private ?array $response = null;

    private string $correlationId = '';

    public function __construct(
        private readonly string $host,
        private readonly int $port,
        private readonly string $user,
        private readonly string $password,
        private readonly string $vhost = '/',
        private readonly string $requestQueue = 'request_queue',
        private readonly string $responseQueue = 'response_queue',
        private readonly float $connectionTimeout = 3.0,
        private readonly float $readWriteTimeout = 130.0,
        private readonly int $heartbeat = 30,
        private readonly int $responseTimeout = 60,
    ) {}

    public static function fromConfig(): self
    {
        return new self(
            host: (string) config('rabbitmq.host', 'rabbitmq'),
            port: (int) config('rabbitmq.port', 5672),
            user: (string) config('rabbitmq.user', 'guest'),
            password: (string) config('rabbitmq.password', 'guest'),
            vhost: (string) config('rabbitmq.vhost', '/'),
            requestQueue: (string) config('rabbitmq.request_queue', 'request_queue'),
            responseQueue: (string) config('rabbitmq.response_queue', 'response_queue'),
            connectionTimeout: (float) config('rabbitmq.connection_timeout', 3.0),
            readWriteTimeout: (float) config('rabbitmq.read_write_timeout', 130.0),
            heartbeat: (int) config('rabbitmq.heartbeat', 30),
            responseTimeout: (int) config('rabbitmq.response_timeout', 60),
        );
    }

    /**
     * @return array{ok: bool, result: array<string, mixed>, error: ?string}
     */
    public function request(string $requestText, string $userId): array
    {
        $this->response = null;

        try {
            $this->connect();

            $this->correlationId = bin2hex(random_bytes(16));

            $this->publish($requestText, $userId);
            $this->waitForResponse();

            if ($this->response === null) {
                return $this->failure('Таймаут анализа');
            }

            $result = $this->response['result'] ?? null;

            if (! is_array($result)) {
                return $this->failure('Ответ без поля result');
            }

            return ['ok' => true, 'result' => $result, 'error' => null];
        } catch (Throwable $e) {
            Log::error('[RabbitRpc] '.$e->getMessage(), ['exception' => $e]);

            return $this->failure($e->getMessage());
        } finally {
            $this->close();
        }
    }

    private function connect(): void
    {
        $this->connection = new AMQPStreamConnection(
            host: $this->host,
            port: $this->port,
            user: $this->user,
            password: $this->password,
            vhost: $this->vhost,
            connection_timeout: $this->connectionTimeout,
            read_write_timeout: $this->readWriteTimeout,
            heartbeat: $this->heartbeat,
        );

        $this->channel = $this->connection->channel();
        $this->channel->basic_qos(0, 1, false);

        // Те же параметры, что объявляет python-consumer.
        $this->channel->queue_declare($this->requestQueue, false, true, false, false);
        $this->channel->queue_declare($this->responseQueue, false, true, false, false);
    }

    private function publish(string $requestText, string $userId): void
    {
        if ($this->channel === null) {
            throw new RuntimeException('Канал RabbitMQ не открыт');
        }

        $body = json_encode([
            'request_text'   => $requestText,
            'correlation_id' => $this->correlationId,
            'user_id'        => $userId,
        ], JSON_UNESCAPED_UNICODE);

        if ($body === false) {
            throw new RuntimeException('Не удалось сериализовать задачу в JSON');
        }

        $this->channel->basic_publish(
            new AMQPMessage($body, [
                'correlation_id' => $this->correlationId,
                'reply_to'       => $this->responseQueue,
                'delivery_mode'  => AMQPMessage::DELIVERY_MODE_PERSISTENT,
            ]),
            '',
            $this->requestQueue,
        );
    }

    private function waitForResponse(): void
    {
        $channel = $this->channel;

        if ($channel === null) {
            return;
        }

        $channel->basic_consume(
            queue: $this->responseQueue,
            consumer_tag: '',
            no_local: false,
            no_ack: false,
            exclusive: false,
            nowait: false,
            callback: function (AMQPMessage $message): void {
                $message->ack();

                // Чужой ответ: подтвердили и идём дальше.
                if ($message->get('correlation_id') !== $this->correlationId) {
                    return;
                }

                $decoded = json_decode($message->body, true);

                if (is_array($decoded)) {
                    $this->response = $decoded;
                }
            },
        );

        $deadline = microtime(true) + $this->responseTimeout;

        while ($this->response === null && microtime(true) < $deadline) {
            try {
                $channel->wait(null, false, 1);
            } catch (AMQPTimeoutException) {
                continue;
            }
        }
    }

    private function close(): void
    {
        try {
            if ($this->channel !== null && $this->channel->is_open()) {
                $this->channel->close();
            }

            if ($this->connection !== null && $this->connection->isConnected()) {
                $this->connection->close();
            }
        } catch (Throwable) {
            // соединение могло быть уже разорвано
        } finally {
            $this->channel = null;
            $this->connection = null;
        }
    }

    /**
     * @return array{ok: false, result: array<never>, error: string}
     */
    private function failure(string $error): array
    {
        return ['ok' => false, 'result' => [], 'error' => $error];
    }
}