<?php
    require_once __DIR__ . '/../Service/TextAnalysis.php';


    class CommandHandler{

        private $commands = [];
        private Logger $logger;
        private UserRepository $userRepository;
        public function __construct(array $commands, UserRepository $userRepository){
            $this->commands = $commands;
            $this->logger = new Logger('CommandHandler_error.log');
            $this->userRepository = $userRepository;  
        }
        
    public function handle($message, $peer_id){
        $this->processTextMessage($message, $peer_id);
    }

    private function processTextMessage($message, $peer_id){
        $lowerMessage = mb_strtolower(trim($message));

        if (isset($this->commands[$lowerMessage])) {
            $this->executeCommand($lowerMessage, $message, $peer_id);
        } else {
            $this->handleUnknownCommand($lowerMessage, $peer_id);
        }
    }
    

   private function executeCommand($commandKey, $message, $peer_id){    
    if (!isset($this->commands[$commandKey])) {
        
        $this->sendResponse(
            $peer_id, 
            "Команда не найдена.", 
            KeyboardBuilder::getMainMenuJson()
        );
        return;
    }
    
    $handler = $this->commands[$commandKey];
    
    try{

        $responseData = $handler($peer_id);
        $text = $responseData['text'] ?? '';
        $keyboard = $responseData['keyboard'] ?? null;
        $this->sendResponse($peer_id, $text, $keyboard);

    } catch (\Throwable $e) {
        $this->log("Ошибка при выполнении команды '$commandKey': " . $e->getMessage());
        $errorMessage  = ServiceMessage::technichalErrorMessage();
        
        $this->sendResponse($peer_id, $errorMessage['text'], $errorMessage['keyboard']);
    }
}

    private function handleUnknownCommand($message, $peer_id){
        // $this->sendResponse($peer_id, "Отвечаем на ваще сообщение...");
        $user = new UserState($peer_id, $this->userRepository);
        $userData = $user->handle();
        if ($userData['requests'] > 0 || $userData['status'] === 'prem'){
            $text_analysis = new TextAnalysis($message, $peer_id);
            $result = $text_analysis->getAnalysis();
            SendResponse::vkSendMessage(
                $peer_id,
                $result['text'],
                KeyboardBuilder::getMainMenuJson()
            );
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

    private function sendResponse($peer_id, $message, $keyboard = null){
        SendResponse::vkSendMessage($peer_id, $message, $keyboard);
    }

    private function log($message) {
        $this->logger->handle($message);
    }

        

}
?>