<?php
ini_set('display_errors', 0);
ini_set('log_errors', 1);
ini_set('error_log', __DIR__ . '/../Logs/Log_Files/General_errors.log');

define('VK_CONFIRMATION_CODE', getenv('VK_CONFIRMATION_CODE'));
define('VK_TOKEN', getenv('VK_TOKEN'));

define ('RABBITMQ_HOST', getenv('RABBITMQ_HOST'));
define ('RABBITMQ_PORT', getenv('RABBITMQ_PORT'));
define ('RABBITMQ_USER', getenv('RABBITMQ_USER'));
define ('RABBITMQ_PASS', getenv('RABBITMQ_PASS'));


?>