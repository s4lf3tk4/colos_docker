<?php

    $dbhost = getenv('DB_HOST');
    $dbuser = getenv('DB_USER');
    $dbpass = getenv('DB_PASS');
    $dbname = getenv('DB_PORT');
    $dbport = getenv('DB_PORT');
    
    $conn = new mysqli($dbhost, $dbuser, $dbpass, $dbname, $dbport);

    if ($conn->connect_error) {
        throw new \Exception("Ошибка подключения к БД: " . $conn->connect_error);
    }

    $sql_users = "CREATE TABLE IF NOT EXISTS `users` (
        `id` VARCHAR(10) NOT NULL,
        `status` VARCHAR(6) NOT NULL,
        `time_status` DATE NOT NULL,
        `requests` INT(100) NOT NULL,
        PRIMARY KEY (`id`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci";

    $conn->query($sql_users);

    return $conn

?>