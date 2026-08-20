<?php
//require_once __DIR__ . '/../MessageProcessor/UserState/DB_config.php';

try {
    $sql = "CREATE DATABASE IF NOT EXISTS `vk-bot`
            CHARACTER SET utf8mb4
            COLLATE utf8mb4_general_ci";
    
    $pdo->exec($sql);
    echo "✅ База данных 'vk-bot' создана или уже существует\n";

    $pdo->exec("USE `vk-bot`");
    echo "✅ Используется база данных 'vk-bot'\n";

    $sql = "CREATE TABLE IF NOT EXISTS `users` (
                `id` VARCHAR(10) NOT NULL,
                `status` VARCHAR(6) NOT NULL,
                `time_status` DATE NOT NULL,
                `requests` INT(100) NOT NULL,
                PRIMARY KEY (`id`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci";
    
    $pdo->exec($sql);
    echo "✅ Таблица 'users_status' создана или уже существует\n";

    $stmt = $pdo->query("SHOW TABLES");
    $tables = $stmt->fetchAll();
    echo "\n📋 Таблицы в базе данных:\n";
    foreach ($tables as $table) {
        echo "- " . current($table) . "\n";
    }

    $stmt = $pdo->query("DESCRIBE `users_status`");
    $columns = $stmt->fetchAll();
    echo "\n📊 Структура таблицы 'users_status':\n";
    echo "ID | Имя | Тип | Null | Ключ | По умолчанию | Extra\n";
    echo str_repeat("-", 70) . "\n";
    foreach ($columns as $col) {
        echo $col['Field'] . " | " 
             . $col['Type'] . " | " 
             . ($col['Null'] ? 'YES' : 'NO') . " | "
             . $col['Key'] . " | "
             . $col['Default'] . " | "
             . $col['Extra'] . "\n";
    }

} catch (PDOException $e) {
    die("❌ Ошибка: " . $e->getMessage());
}
?>