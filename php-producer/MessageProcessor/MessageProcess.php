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
                return; 
            }
            if ($eventId && $this->isDuplicateEvent($eventId)) {
                return;
            }

            if ($this->hasPhoto($attachments)) {
                $user = new UserState($peer_id, $this->userRepository);
                $userData = $user->handle();
                if ($userData['requests']>0 || $userData['status'] === 'prem'){
                    $photo = new PhotoProcess($attachments, $peer_id);
                    $photo->processPhoto();
                    if ($userData['status'] === 'guest'){
                        $user->decrementRequests();
                    }
                    echo('ok');
                    return;
                }
                else{
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

    private function isDuplicateEvent(string $eventId): bool{
        if ($eventId === '') {
            return false;
        }

        $cacheFile = __DIR__ . '/../cache/events.json';
        $events = [];

        if (file_exists($cacheFile)) {
            $events = json_decode(file_get_contents($cacheFile), true) ?: [];
        }

        $now = time();
        $events = array_filter($events, fn($time) => $now - $time < 60);

        if (isset($events[$eventId])) {
            return true;
        }

        $events[$eventId] = $now;
        file_put_contents($cacheFile, json_encode($events));

        return false;
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