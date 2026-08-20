<?php
class SendResponse{
    public static function vkSendMessage($peer_id, $message, $keyboard = null) {
        try{
            $token = VK_TOKEN;
            $params = [
                'access_token' => $token,
                'v'           => '5.199',
                'peer_id'     => $peer_id,
                'message'     => $message,
                'random_id'   => rand(1, 1000000)
            ];
            if ($keyboard) {
                $params['keyboard'] = is_array($keyboard) ? json_encode($keyboard) : $keyboard;
            }
            $url = "https://api.vk.com/method/messages.send?" . http_build_query($params);
            $ch = curl_init();
            curl_setopt($ch, CURLOPT_URL, $url);
            curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
            $response = curl_exec($ch);
            curl_close($ch);
            return $response;
        }catch (\Throwable $e) {
            file_put_contents(
            __DIR__ . '/../logs/vkSend_errors.log',
            date('Y-m-d H:i:s') . " Ошибка: " . $e->getMessage() . "\n",
            FILE_APPEND
            );
            return null;
        }
    }
}

?>