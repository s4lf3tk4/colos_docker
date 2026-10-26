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

Route::post('/', VkWebhookController::class);