<?php

declare(strict_types=1);

namespace App\Providers;

use App\Services\Messaging\EventDeduplicator;
use App\Services\Rabbit\RabbitRpcClient;
use App\Services\Vk\VkApiClient;
use Illuminate\Support\ServiceProvider;

final class AppServiceProvider extends ServiceProvider
{
    public function register(): void
    {
        $this->app->singleton(
            VkApiClient::class,
            static fn (): VkApiClient => VkApiClient::fromConfig(),
        );

        // Клиент RPC хранит состояние канала и correlation_id — только bind.
        $this->app->bind(
            RabbitRpcClient::class,
            static fn (): RabbitRpcClient => RabbitRpcClient::fromConfig(),
        );

        $this->app->singleton(
            EventDeduplicator::class,
            static fn (): EventDeduplicator => new EventDeduplicator(
                ttlSeconds: (int) config('vk.event_dedupe_seconds', 86400),
            ),
        );
    }

    public function boot(): void
    {
        //
    }
}   