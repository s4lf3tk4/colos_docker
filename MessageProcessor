<?php

class MessageProcess{

    private CommandHandler $commandHandler;
    private Logger $logger;
    private UserRepository $userRepository;

    public function __construct(CommandHandler $commandHandler, UserRepository $userRepository){
        $this->commandHandler = $commandHandler;
        $this->logger = new Logger('MessageProcess_error.log');
        $this->userRepository = $userRepository;   
    }

    public function handleMessage($data) : void{
        try {
            $eventId = $data['event_id'] ?? '';
            $message = $data['object']['message']['text'] ?? '';
            $peer_id = $data['object']['message']['peer_id'] ?? 0;
            $attachments = $data['object']['message']['attachments'] ?? [];
                
            if (($data['object']['message']['out'] ?? 0) === 1) {
                echo('ok');
                return; 
            }

            if ($eventId && $this->isDuplicateEvent($eventId)) {
                echo('ok');  // подтверждение, даже если событие дублируется
                return;
            }

            if ($this->hasPhoto($attachments)) {
                $user = new UserState($peer_id, $this->userRepository);
                $userData = $user->handle();
                if ($userData['requests'] > 0 || $userData['status'] === 'prem'){
                    $photo = new PhotoProcess($attachments, $peer_id);
                    $photo->processPhoto();
                    if ($userData['status'] === 'guest'){
                        $user->decrementRequests();
                    }
                    echo('ok');
                    return;
                } else {
                    $errorMessage = ServiceMessage::noRequestsErorrMessage();
                    SendResponse::vkSendMessage($peer_id, $errorMessage['text'], $errorMessage['keyboard']);
                    echo('ok');
                    return;
                }
            }

            $this->commandHandler->handle($message, $peer_id);
            echo('ok');
            
        } catch (\Throwable $e) {
            $this->handleError($e, $peer_id ?? 0);
            echo('ok');
        }
    }

    private function isDuplicateEvent(string $eventId): bool
    {
        if ($eventId === '') {
            return false;
        }

        $cacheFile = __DIR__ . '/../cache/events.json';
        try {
            // Проверяем и создаём папку cache, если её нет
            $cacheDir = dirname($cacheFile);
            if (!is_dir($cacheDir)) {
                if (!mkdir($cacheDir, 0755, true) && !is_dir($cacheDir)) {
                    // Не удалось создать папку — пропускаем защиту
                    return false;
                }
            }

            $events = [];
            if (file_exists($cacheFile)) {
                $content = file_get_contents($cacheFile);
                if ($content !== false) {
                    $events = json_decode($content, true) ?: [];
                }
            }

            $now = time();
            // Оставляем только события за последнюю минуту
            $events = array_filter($events, fn($time) => $now - $time < 60);

            if (isset($events[$eventId])) {
                return true;
            }

            $events[$eventId] = $now;
            // Сохраняем с блокировкой, чтобы избежать гонок
            file_put_contents($cacheFile, json_encode($events), LOCK_EX);
            return false;

        } catch (\Throwable $e) {
            // Любая ошибка — пропускаем защиту (не блокируем обработку)
            return false;
        }
    }


    private function hasPhoto($attachments){
        foreach ($attachments as $attach) {
            if ($attach['type'] === 'photo') {
                return true;
            }
        }
        return false;
    }
    
    private function handleError($e, $peer_id = 0){
        $errorMessage = "Ошибка: " . $e->getMessage() . " в строке: " . $e->getLine();
        $this->log($errorMessage);

        if ($peer_id > 0) {
            $errorMessage = ServiceMessage::technichalErrorMessage();
            SendResponse::vkSendMessage($peer_id, $errorMessage['text'], $errorMessage['keyboard']);
        }
    }

    private function log($message) {
        $this->logger->handle($message);
    }
}