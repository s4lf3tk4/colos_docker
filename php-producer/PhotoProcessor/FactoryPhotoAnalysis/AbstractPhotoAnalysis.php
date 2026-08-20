<?php

use PhpAmqpLib\Connection\AMQPStreamConnection;
use PhpAmqpLib\Message\AMQPMessage;

   abstract class AbstractPhotoAnalysis implements PhotoAnalysisInterf{
        protected $photoURL;
        protected $peer_id;
        public function __construct(string $photoURL, int $peer_id){
            $this->photoURL = $photoURL;
            $this->peer_id  = $peer_id;
        }
        public function getFullResult(): array{
            $results = [
                $this->getAnalysis()
            ];
            $texts = [];

            foreach ($results as $result) {
                if ($result && !empty($result['text'])) {
                    $texts[] = $result['text'];
                }
            }
            return [
                'text' => implode("\n", $texts),
                'keyboard' => KeyboardBuilder::getMainMenuJson(),
            ];
            
        }
    }

?>