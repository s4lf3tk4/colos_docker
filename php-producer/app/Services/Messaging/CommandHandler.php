<?php

declare(strict_types=1);

namespace App\Services\Messaging;

use App\Services\Analysis\AnalysisService;
use App\Services\Users\UserStateService;
use App\Services\Vk\KeyboardBuilder;
use App\Services\Vk\OutgoingMessage;
use App\Services\Vk\ServiceMessages;
use App\Services\Vk\VkApiClient;
use Illuminate\Support\Facades\Log;
use Throwable;

final class CommandHandler
{
    public function __construct(
        private readonly CommandRegistry $registry,
        private readonly UserStateService $userStates,
        private readonly AnalysisService $analysis,
        private readonly VkApiClient $vk,
    ) {}

    public function handle(IncomingMessage $message): void
    {
        $key = mb_strtolower(trim($message->text));
        $handlers = $this->registry->handlers();

        if (isset($handlers[$key])) {
            $this->execute($key, $handlers[$key], $message);

            return;
        }

        $this->handleFreeText($message);
    }

    /**
     * @param  callable(string): OutgoingMessage  $handler
     */
    private function execute(string $key, callable $handler, IncomingMessage $message): void
    {
        try {
            $this->vk->sendMessage($message->peerId, $handler((string) $message->peerId));
        } catch (Throwable $e) {
            Log::error("CommandHandler: команда '{$key}' завершилась ошибкой", [
                'peer_id' => $message->peerId,
                'error'   => $e->getMessage(),
            ]);

            $this->vk->sendMessage($message->peerId, ServiceMessages::technicalError());
        }
    }

    private function handleFreeText(IncomingMessage $message): void
    {
        $peerId = (string) $message->peerId;
        $state = $this->userStates->resolve($peerId);

        if (! $state->canMakeRequest()) {
            $this->vk->sendMessage($message->peerId, ServiceMessages::noRequests());

            return;
        }

        $result = $this->analysis->analyze($message->text, $peerId);

        $this->vk->sendMessage(
            $message->peerId,
            new OutgoingMessage($result->text, KeyboardBuilder::mainMenu()),
        );

        if ($result->ok && $state->isGuest()) {
            $this->userStates->decrement($peerId);
        }
    }
}