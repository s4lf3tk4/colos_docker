<?php

declare(strict_types=1);

namespace App\Services\Messaging;

final class IncomingMessage
{
    /**
     * @param  array<int, mixed>  $attachments
     */
    public function __construct(
        public readonly string $eventId,
        public readonly int $peerId,
        public readonly string $text,
        public readonly array $attachments,
        public readonly bool $isOutgoing,
    ) {}

    /**
     * @param  array<string, mixed>  $payload
     */
    public static function fromVkPayload(array $payload): self
    {
        $message = $payload['object']['message'] ?? [];
        $message = is_array($message) ? $message : [];

        $attachments = $message['attachments'] ?? [];

        return new self(
            eventId: (string) ($payload['event_id'] ?? ''),
            peerId: (int) ($message['peer_id'] ?? 0),
            text: (string) ($message['text'] ?? ''),
            attachments: is_array($attachments) ? $attachments : [],
            isOutgoing: ((int) ($message['out'] ?? 0)) === 1,
        );
    }

    public function hasPhoto(): bool
    {
        foreach ($this->attachments as $attachment) {
            if (is_array($attachment) && ($attachment['type'] ?? null) === 'photo') {
                return true;
            }
        }

        return false;
    }
}