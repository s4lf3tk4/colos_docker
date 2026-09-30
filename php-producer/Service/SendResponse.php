<?php

class SendResponse
{
    private const API_URL = 'https://api.vk.com/method/messages.send';
    private const API_VERSION = '5.199';

    public static function vkSendMessage($peer_id, $message, $keyboard = null)
    {
        try {
            if ($message === null || $message === '') {
                return null;   // нечего отправлять
            }

            $params = [
                'access_token' => VK_TOKEN,
                'v'            => self::API_VERSION,
                'peer_id'      => $peer_id,
                'message'      => (string)$message,
                'random_id'    => random_int(1, PHP_INT_MAX),
            ];

            if (!empty($keyboard)) {
                $params['keyboard'] = is_array($keyboard)
                    ? json_encode($keyboard, JSON_UNESCAPED_UNICODE)
                    : $keyboard;
            }

            $ch = curl_init(self::API_URL);
            curl_setopt_array($ch, [
                CURLOPT_POST           => true,
                CURLOPT_POSTFIELDS     => http_build_query($params),
                CURLOPT_RETURNTRANSFER => true,
                CURLOPT_TIMEOUT        => 15,
                CURLOPT_CONNECTTIMEOUT => 5,
            ]);

            $response = curl_exec($ch);
            $error = curl_error($ch);
            curl_close($ch);

            if ($response === false) {
                error_log('[SendResponse] curl: ' . $error);
                return null;
            }

            $decoded = json_decode($response, true);
            if (isset($decoded['error'])) {
                error_log('[SendResponse] VK error: ' . json_encode($decoded['error'], JSON_UNESCAPED_UNICODE));
            }

            return $response;
        } catch (\Throwable $e) {
            error_log('[SendResponse] ' . $e->getMessage());
            return null;
        }
    }
}