<?php

declare(strict_types=1);

namespace App\Services\Analysis;

final class AnalysisResponse
{
    public function __construct(
        public readonly bool $ok,
        public readonly string $text,
    ) {}
}