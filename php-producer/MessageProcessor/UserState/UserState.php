<?php

    class UserState{
        private $peer_id;
        private UserRepository $userRepository;
        private Logger $logger;

        public function __construct($peer_id, UserRepository $userRepository){
            $this->peer_id = $peer_id;
            $this->userRepository = $userRepository;
            $this->logger = new Logger('UserState_error.log');
        }
         public function handle(){
            try{ 
            
                if(!$this->userRepository->isUnique($this->peer_id)){
                    $this->userRepository->createUser($this->peer_id);
                    return ['status' => 'guest', 'requests' => 5];    
                }
                $userData = $this->userRepository->getUserData($this->peer_id);

                if ($userData['status'] === 'prem' && strtotime($userData['time_status']) > time()){
                    return ['status' => 'prem', 'requests' => null];
                }
                return ['status' => 'guest', 'requests' => $userData['requests']];
                
              
            }catch (\Throwable $e) {
                $this->logger->handle("Ошибка в UserState". $e->getMessage());
                return ['status' => 'error', 'requests' => null];
            }
        }
        public function decrementRequests(): void{
            $this->userRepository->decrementRequests($this->peer_id);
        }

    }