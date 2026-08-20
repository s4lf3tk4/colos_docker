<?php

class KeyboardBuilder
{
    public static function getMainMenuJson() {
        $keyboard = [
            'one_time' => false,
            'buttons' => [
                [
                    ['action' => ['type' => 'text', 'label' => '📋 Получить анализ'], 'color' => 'primary'],
                ],
                [
                    ['action' => ['type' => 'text', 'label' => 'Настройки'], 'color' => 'secondary']
                ],
            ]
        ];
        return json_encode($keyboard, JSON_UNESCAPED_UNICODE);
    }

    public static function getUserOptionsJson() {
        $keyboard = [
            'one_time' => false,
            'buttons' => [
                [
                    ['action' => ['type' => 'text', 'label' => 'Узнать статус подписки'], 'color' => 'secondary'],
                ],
                [
                    ['action' => ['type' => 'text', 'label' => 'Подключить подписку'], 'color' => 'secondary']
                ],
                [
                    ['action' => ['type' => 'text', 'label' => 'Назад'], 'color' => 'secondary']
                ],
            ]
        ];
        return json_encode($keyboard, JSON_UNESCAPED_UNICODE);
    }

    public static function getBackButtonJson() {
        $keyboard = [
            'one_time' => false,
            'buttons' => [
                [
                    ['action' => ['type' => 'text', 'label' => 'Назад'], 'color' => 'primary']
                ],
            ]
        ];
        return json_encode($keyboard, JSON_UNESCAPED_UNICODE);
    }
}
?>