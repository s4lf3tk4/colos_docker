<?php

declare(strict_types=1);

namespace App\Services\Photo;

use Illuminate\Support\Facades\Log;

final class PhotoUrlExtractor
{
    /**
     * VK присылает несколько размеров; самый крупный — последний в sizes.
     *
     * @param  array<int, mixed>  $attachments
     */
    public function extract(array $attachments): ?string
    {
        foreach ($attachments as $attachment) {
            if (! is_array($attachment) || ($attachment['type'] ?? null) !== 'photo') {
                continue;
            }

            $sizes = $attachment['photo']['sizes'] ?? null;

            if (! is_array($sizes) || $sizes === []) {
                Log::warning('PhotoUrlExtractor: вложение photo без sizes, пропускаю');

                continue;
            }

            $largest = end($sizes);
            $url = is_array($largest) ? ($largest['url'] ?? null) : null;

            if (is_string($url) && $url !== '') {
                return $url;
            }
        }

        return null;
    }
}