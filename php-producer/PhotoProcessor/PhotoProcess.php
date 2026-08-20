<?php

class PhotoProcess{

    private $attachment;
    private $peer_id;      
    private Logger $logger;
    public function __construct($attachment, $peer_id) {   

        require_once __DIR__ . '/FactoryPhotoAnalysis/PhotoAnalysisInterf.php';
        require_once __DIR__ . '/FactoryPhotoAnalysis/AbstractPhotoAnalysis.php';
        require_once __DIR__ . '/FactoryPhotoAnalysis/FullAnalysis.php';

        $this->attachment = $attachment;
        $this->peer_id = $peer_id;       
        $this->logger = new Logger('PhotoProcess_error.log');               
    }
    private function extractPhotoUrl($attachments){
        foreach ($attachments as $attach) {
            if ($attach['type'] === 'photo') {
                $sizes = $attach['photo']['sizes'];
                return end($sizes)['url'];
            }
        }
        return null;
    }

    private function processPhotoMessage($photoURL){
        try {
            $analyzer = new FullAnalysis($photoURL, $this->peer_id);
            $result = $analyzer->getFullResult();
            SendResponse::vkSendMessage(
                $this->peer_id,
                $result['text'],
                $result['keyboard']
            );
        } catch (\Throwable $e) {
            $this->log("Ошибка при обработке фото в processPhotoMessage: " . $e->getMessage());

        }
    }

    public function processPhoto(){
        $photoURL = $this->extractPhotoUrl($this->attachment);
        if ($photoURL === null) {
            $this->log("Ошибка: URL фото не найден");
            return;
        }
        $this->processPhotoMessage($photoURL);
    }
        
    private function log($message){
        $this->logger->handle($message);
    }
    
}

?>