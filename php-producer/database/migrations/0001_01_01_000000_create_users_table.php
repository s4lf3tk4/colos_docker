<?php

declare(strict_types=1);

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('users', function (Blueprint $table): void {
            // peer_id приходит числом, но храним строкой — как в legacy-схеме.
            $table->string('id', 20)->primary();
            $table->string('status', 16)->default('guest');
            $table->date('time_status')->nullable();
            $table->unsignedInteger('requests')->default(5);

            $table->index('status');
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('users');
    }
};