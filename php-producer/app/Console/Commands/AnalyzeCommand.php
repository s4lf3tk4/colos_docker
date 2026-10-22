<?php

declare(strict_types=1);

namespace App\Console\Commands;

use App\Services\Rabbit\RabbitRpcClient;
use Illuminate\Console\Command;

final class AnalyzeCommand extends Command
{
    protected $signature = 'analysis:send
                            {input : Путь к файлу или текст запроса}
                            {--user=cli-user : Идентификатор пользователя (thread_id в langgraph)}';

    protected $description = 'Отправить запрос в python-consumer через RabbitMQ и напечатать результат';

    public function handle(RabbitRpcClient $rpc): int
    {
        $input = (string) $this->argument('input');
        $userId = (string) $this->option('user');

        $this->components->info('Отправка задачи в request_queue…');

        $response = $rpc->request($input, $userId);

        if (! $response['ok']) {
            $this->components->error('Ответ не получен: '.$response['error']);

            return self::FAILURE;
        }

        $result = $response['result'];

        $sizes = $result['sizes'] ?? null;

        if (is_array($sizes) && $sizes !== []) {
            $this->line('Размеры объектов:');

            foreach ($sizes as $size) {
                $this->line(is_string($size) ? $size : (string) json_encode($size, JSON_UNESCAPED_UNICODE));
            }
        }

        $message = $result['message'] ?? '';

        $this->line(is_string($message) ? $message : (string) json_encode($message, JSON_UNESCAPED_UNICODE));

        return self::SUCCESS;
    }
}