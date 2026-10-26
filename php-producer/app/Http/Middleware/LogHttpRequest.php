<?php

declare(strict_types=1);

namespace App\Http\Middleware;

use Closure;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Log;
use Illuminate\Support\Str;
use Symfony\Component\HttpFoundation\Response;
use Throwable;

final class LogHttpRequest
{
    public function handle(Request $request, Closure $next): Response
    {
        $startedAt = microtime(true);

        Log::withContext([
            'request_id' => (string) Str::uuid(),
            'ip'         => $request->ip(),
            'method'     => $request->method(),
            'path'       => $request->path(),
        ]);

        Log::info('HTTP -> входящий запрос', [
            'content_type' => $request->header('Content-Type'),
            'body'         => $this->redactedBody($request),
        ]);

        try {
            $response = $next($request);
        } catch (Throwable $e) {
            Log::error('HTTP <- исключение', [
                'exception' => $e::class,
                'message'   => $e->getMessage(),
                'at'        => $e->getFile().':'.$e->getLine(),
            ]);

            throw $e;
        }

        Log::info('HTTP <- ответ', [
            'status' => $response->getStatusCode(),
            'ms'     => (int) round((microtime(true) - $startedAt) * 1000),
            'body'   => mb_substr((string) $response->getContent(), 0, 500),
        ]);

        return $response;
    }

    private function redactedBody(Request $request): string
    {
        $raw = $request->getContent();
        $decoded = json_decode($raw, true);

        if (is_array($decoded) && array_key_exists('secret', $decoded)) {
            $decoded['secret'] = '***';
            $raw = (string) json_encode($decoded, JSON_UNESCAPED_UNICODE);
        }

        return mb_substr($raw, 0, 2000);
    }
}