<?php

class ServiceMessage
{
    public static function photoSending($peer_id = null) {
        return [
            'text' => "📸 Отправьте фото блюда для анализа.",
            'keyboard' => KeyboardBuilder::getBackButtonJson(),
        ];
    }

    public static function startMessage($peer_id = null) {
        return [
            'text' => "🌟 Добро пожаловать в бот здорового питания! 🌟\n\n" .
                      "🍽️ Я помогу вам анализировать рацион с помощью искусственного интеллекта.\n\n" .
                      "📸 Как получить анализ:\n" .
                      "1. Нажмите кнопку «📋Получить анализ»\n" .
                      "2. Отправьте фото блюда\n" .
                      "3. Бот оценит его и даст рекомендации\n\n" .
                      "Приятного аппетита и будьте здоровы!💚",
            'keyboard' => KeyboardBuilder::getMainMenuJson(),
        ];
    }

    public static function optionsButton($peer_id = null) {
        return [
            'text' => '⚙️Настройки аккаунта',
            'keyboard' => KeyboardBuilder::getUserOptionsJson(),
        ];
    }

    public static function backButton($peer_id = null) {
        return [
            'text' => 'Вы вернулись в главное меню.',
            'keyboard' => KeyboardBuilder::getMainMenuJson(),
        ];
    }
    public static function technichalErrorMessage($peer_id = null){
        return [
            'text' =>   "⚠️Произошла непредвиденная ошибка⚠️\n\n".
                        "Уже работаем над этим. Просим прощения за предоствленные неудобства. \n\n".
                        "Напишите администратору для более подробной информации о вашей проблеме. \n\n" .
                        "Это поможет ускорить работу, к тому же вы можете получить бонус за предоставленую информацию!",
            'keyboard' => KeyboardBuilder::getMainMenuJson(),
        ];
    }
        public static function noRequestsErorrMessage($peer_id = null){
        return [
            'text' =>   "⚠️Превышен лимит запросов или истекла подписка⚠️ \n\n".
                        "Купите подписку, или оплатите нужное вам количество запросов\n\n",
            'keyboard' => KeyboardBuilder::getUserOptionsJson(),
        ];
    }


}
?>