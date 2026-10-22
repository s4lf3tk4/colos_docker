<?php

use App\Http\Controllers\VkWebhookController;
use Illuminate\Foundation\Application;
use Illuminate\Support\Facades\Route;

Route::get('/', fn () => response()->json([
    'service'   => config('app.name'),
    'framework' => 'Laravel '.Application::VERSION,
    'status'    => 'ok',
]));

Route::get('/health', fn () => response()->json(['status' => 'ok']));

// Старый index.php жил в корне — поэтому POST / сохранён.
// Для настройки Callback API удобнее /vk/callback.
Route::post('/', VkWebhookController::class);
Route::post('/vk/callback', VkWebhookController::class);