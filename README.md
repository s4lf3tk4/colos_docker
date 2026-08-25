<font size="3"><b>

<div align = 'center'>

# Colos


### Описание работы


Colos_docker - Это микросервисная система для анализа фотографий еды: определяет размер объектов (в см³) на основе калибровочных объектов и рассчитывает калорийность


| Компонент | Роль |
|---|---|
| PHP-producer | Принимает запросы (из CLI или VK webhook), отправляет путь к фото в очередь RabbitMQ |
| RabbitMQ | Брокер сообщений, связывает продюсера и консумера |
| Python-consumer | Получает задачу, загружает фото, запускает YOLO для детекции, вычисляет масштаб по вилке, рассчитывает объём, через LLM получает калорийность, отправляет ответ |
| MySQL | Хранит состояние пользователей (статус подписки, количество запросов) |

#### =ПОТОК ДАННЫХ=

<div align = 'left'>

- Пользователь отправляет фото (через бота ВК или CLI).

- PHP формирует задачу с путём к файлу и correlation_id, публикует в очередь request_queue.

- Python забирает задачу, анализирует изображение, формирует результат.

- Результат отправляется в очередь response_queue с тем же correlation_id.

- PHP забирает ответ и возвращает его пользователю.

</div>

#### =ТЕХНОЛОГИИ=

<div align = 'left'>

- PHP 8.3 + php-amqplib – для работы с RabbitMQ

- Python 3.12 + Ultralytics YOLO – детекция объектов

- LangChain + Ollama – расчёт калорийности

- RabbitMQ – обмен сообщениями

- MySQL – хранение данных пользователей

- Docker – контейнеризация всех сервисов

</div>

___

### Быстрый старт
<div align = 'left'>

1) Клонирвоать репозиторий git clone https://github.com/s4lf3tk4/colos_docker

2) Настроить окружение .env: 
   - .env.python в python-consumer; 
   - .env.php в php-producer;
   - .env.mysql в php_docker; 
   - .env.rabbitmq в php_docker; 
   
3) Добавть в файл models веса .pt: 

   - ` model_food.pt ` для анализа самих блюд, 

   - ` model_calibrations.pt`  для калибровки

4) Подготовка папки для теста: 

- `cd php_docker`

- `mkdir storage` для создания папки, где будут тестовые фотки: после поднятия докера создасться сама, но чтобы докер видел сразу `РЕКОМЕНДУЕТСЯ создать ее вручную`, доабвьте в нее картинку (например test.png)

5) Запуск контейнеров

- `docker-compose build` 
- `docker-compose up -d`
- проверить запуск: `docker-compose ps`:
  
   - 4 контейнера должны быть up: mysql, php-producer, python-consumer, rabbitmq 

6) ТЕСТ: `docker-compose exec php-producer php /var/www/html/main.php /app/storage/test.png` - поднимает временный контейнер для main.php

Пример вывода:
```
 [x] Задача отправлена, ждём ответ...
Размеры объектов:
• banana: 10.4 см^3
Расчёт калорийности:
banana: 96 ккал/100г
```


</div>

</div>

</b>
