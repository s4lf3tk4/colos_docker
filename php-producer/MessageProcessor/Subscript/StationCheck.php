<?php
    class StationCheck{
        public static function stationCheck($peer_id){
            $conn = require  __DIR__ . '/../UserState/DB_config.php';
            $repository = new UserRepository($conn);
            $result = $repository->getUserData($peer_id);

            if (!$result) {
                $repository->createUser($peer_id);
                $result = $repository->getUserData($peer_id);
                if (!$result) {
                    return [
                        'text' => 'Ошибка при создании пользователя. Попробуйте позже.',
                        'keyboard' => null
                    ];
                }
            }
            
            $text =     "Состояние вашего аккаунта:\n\n" .
                        "📊 Статус: " . $result['status'];

            if($result['status'] == 'guest'){
                $text .= "\n\n♻ Осталось запросов: ". $result['requests'];
            }
            else{
                $text .=" 👑 \n\n";
                $date = new DateTime($result['time_status']);
                $formattedDate = $date->format('d/m/Y');
                $text .= "⏳Подписка до: " . $formattedDate;
            }
            
            return [
                'text' => $text,
                'keyboard'=> null,
            ];

        }
    }