<?php
return [
    'начать' => [ServiceMessage::class, 'startMessage'],
    '📋 получить анализ' => [ServiceMessage::class, 'photoSending'],
    'настройки' => [ServiceMessage::class, 'optionsButton'],
    'назад' => [ServiceMessage::class, 'backButton'],
    'узнать статус подписки' => [StationCheck::class, 'stationCheck']
];
?>