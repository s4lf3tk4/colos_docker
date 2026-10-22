<?php

declare(strict_types=1);

namespace App\Services\Messaging;

use App\Services\Analysis\AnalysisService;
use App\Services\Photo\PhotoUrlExtractor;
use App\Services\Users\UserStateService;
use App\Services\Vk\KeyboardBuilder;
use App\Services\Vk\OutgoingMessage;
use App\Services\Vk\ServiceMessages;
use App\Services\Vk\VkApiClient;
use Illuminate\Support\Facades\Log;
use Throwable;

final class MessageHandler
{
    public function __construct(
        private readonly EventDeduplicator $deduplicator,
        private readonly UserStateService $userStates,
        private readonly PhotoUrlExtractor $photoUrls,
        private readonly AnalysisService $analysis,
        private readonly CommandHandler $commands,
        private readonly VkApiClient $vk,
    ) {}

    /**
     * @param  array<string, mixed>  $payload
     */
    public function handle(array $payload): void
    {
        $message = IncomingMessage::fromVkPayload($payload);

        try {
            if ($message->isOutgoing) {
                return;
            }

            if ($this->deduplicator->isDuplicate($message->eventId)) {
                return;
            }

            if ($message->hasPhoto()) {
                $this->handlePhoto($message);

                return;
            }

            $this->commands->handle($message);
        } catch (Throwable $e) {
            Log::error('MessageHandler: необработанная ошибка', [
                'peer_id' => $message->peerId,
                'error'   => $e->getMessage(),
                'line'    => $e->getLine(),
                'file'    => $e->getFile(),
            ]);

            if ($message->peerId > 0) {
                $this->vk->sendMessage($message->peerId, ServiceMessages::technicalError());
            }
        }
    }

    private function handlePhoto(IncomingMessage $message): void
    {
        $peerId = (string) $message->peerId;
        $state = $this->userStates->resolve($peerId);

        if (! $state->canMakeRequest()) {
            $this->vk->sendMessage($message->peerId, ServiceMessages::noRequests());

            return;
        }

        $photoUrl = $this->photoUrls->extract($message->attachments);

        if ($photoUrl === null) {
            Log::warning('MessageHandler: не удалось извлечь URL фото', ['peer_id' => $message->peerId]);

            return;
        }

        $result = $this->analysis->analyze($photoUrl, $peerId);

        $this->vk->sendMessage(
            $message->peerId,
            new OutgoingMessage($result->text, KeyboardBuilder::mainMenu()),
        );

        if ($result->ok && $state->isGuest()) {
            $this->userStates->decrement($peerId);
        }
    }
}