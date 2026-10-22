<?php

declare(strict_types=1);

namespace App\Services\Vk;

final class KeyboardBuilder
{
    public static function mainMenu(): string
    {
        return self::encode([
            'one_time' => false,
            'buttons'  => [
                [self::textButton('📋 Получить анализ', 'primary')],
                [self::textButton('Настройки', 'secondary')],
            ],
        ]);
    }

    public static function userOptions(): string
    {
        return self::encode([
            'one_time' => false,
            'buttons'  => [
                [self::textButton('Узнать статус подписки', 'secondary')],
                [self::textButton('Подключить подписку', 'secondary')],
                [self::textButton('Назад', 'secondary')],
            ],
        ]);
    }

    public static function backButton(): string
    {
        return self::encode([
            'one_time' => false,
            'buttons'  => [
                [self::textButton('Назад', 'primary')],
            ],
        ]);
    }

    /**
     * @return array<string, mixed>
     */
    private static function textButton(string $label, string $color): array
    {
        return [
            'action' => ['type' => 'text', 'label' => $label],
            'color'  => $color,
        ];
    }

    /**
     * @param  array<string, mixed>  $keyboard
     */
    private static function encode(array $keyboard): string
    {
        return (string) json_encode($keyboard, JSON_UNESCAPED_UNICODE);
    }
}