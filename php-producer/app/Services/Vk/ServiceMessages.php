<?php

declare(strict_types=1);

namespace App\Services\Vk;

final class ServiceMessages
{
    public static function start(): OutgoingMessage
    {
        return new OutgoingMessage(
            "🌟 Добро пожаловать в бот здорового питания! 🌟\n\n"
            ."🍽️ Я помогу вам анализировать рацион с помощью искусственного интеллекта.\n\n"
            ."📸 Как получить анализ:\n"
            ."1. Нажмите кнопку «📋Получить анализ»\n"
            ."2. Отправьте фото блюда\n"
            ."3. Бот оценит его и даст рекомендации\n\n"
            .'Приятного аппетита и будьте здоровы!💚',
            KeyboardBuilder::mainMenu(),
        );
    }

    public static function photoSending(): OutgoingMessage
    {
        return new OutgoingMessage(
            '📸 Отправьте фото блюда для анализа.',
            KeyboardBuilder::backButton(),
        );
    }

    public static function options(): OutgoingMessage
    {
        return new OutgoingMessage(
            '⚙️Настройки аккаунта',
            KeyboardBuilder::userOptions(),
        );
    }

    public static function back(): OutgoingMessage
    {
        return new OutgoingMessage(
            'Вы вернулись в главное меню.',
            KeyboardBuilder::mainMenu(),
        );
    }

    public static function technicalError(): OutgoingMessage
    {
        return new OutgoingMessage(
            "⚠️Произошла непредвиденная ошибка⚠️\n\n"
            ."Уже работаем над этим. Просим прощения за предоствленные неудобства. \n\n"
            ."Напишите администратору для более подробной информации о вашей проблеме. \n\n"
            .'Это поможет ускорить работу, к тому же вы можете получить бонус за предоставленую информацию!',
            KeyboardBuilder::mainMenu(),
        );
    }

    public static function noRequests(): OutgoingMessage
    {
        return new OutgoingMessage(
            "⚠️Превышен лимит запросов или истекла подписка⚠️ \n\n"
            ."Купите подписку, или оплатите нужное вам количество запросов\n\n",
            KeyboardBuilder::userOptions(),
        );
    }
}