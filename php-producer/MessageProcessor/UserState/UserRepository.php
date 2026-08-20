<?php

    class UserRepository{
        private mysqli $conn;
        public function __construct(mysqli $conn){
            $this->conn = $conn;
        }
         public function decrementRequests($peer_id){

            $sql = "UPDATE users SET requests = requests - 1 WHERE id = ? AND requests > 0";
            $stmt = $this->conn->prepare($sql);

            if (!$stmt) {
                throw new \RuntimeException("UserRepository::decrementRequests — ошибка prepare: " . $this->conn->error);
            }

            $stmt->bind_param("s", $peer_id);
            $stmt->execute();
            $stmt->close();
        }

        public function getUserData($peer_id){
            $sql = "SELECT status, time_status, requests FROM users WHERE id = ? LIMIT 1";
            $stmt = $this->conn->prepare($sql);
            if (!$stmt) {
                throw new \RuntimeException("UserRepository::getUserData — ошибка prepare: " . $this->conn->error);
            }

            $stmt->bind_param("s", $peer_id);
            $stmt->execute();
            $result = $stmt->get_result();
            $responce = $result->fetch_assoc();
            return $responce;
        }

        public function createUser($peer_id){
            $sql = "INSERT INTO users (id, status, requests) VALUES (?, 'guest', 5)";
            $stmt = $this->conn->prepare($sql);
            if (!$stmt) {
                throw new \RuntimeException("UserRepository::createUser — ошибка prepare: " . $this->conn->error);
            }
            $stmt->bind_param("s", $peer_id);
            if (!$stmt->execute()) {
                throw new \RuntimeException("UserRepository::createUser — ошибка execute: " . $stmt->error);
            }
            $stmt->close();
        }

        public function isUnique($peer_id): bool{
            $sql = "SELECT id FROM users WHERE id = ? LIMIT 1";
            $stmt = $this->conn->prepare($sql);

            if (!$stmt) {
                throw new \RuntimeException("UserRepository::isUnique — ошибка prepare: " . $this->conn->error);
            }

            $stmt->bind_param("s", $peer_id);
            $stmt->execute();
            $result = $stmt->get_result();
            $exists = $result->num_rows > 0;
            $stmt->close();

            return $exists;
        }
    }