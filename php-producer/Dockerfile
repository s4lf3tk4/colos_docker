FROM php:8.4-apache

RUN apt-get update && apt-get install -y --no-install-recommends \
        git \
        curl \
        unzip \
        zip \
        libonig-dev \
        libzip-dev \
        libicu-dev \
    && rm -rf /var/lib/apt/lists/*

# sockets обязателен для php-amqplib
RUN docker-php-ext-install -j"$(nproc)" \
        pdo_mysql \
        mbstring \
        pcntl \
        zip \
        intl \
        sockets \
        bcmath \
        opcache

# DocumentRoot -> /var/www/html/public и разрешаем .htaccess
RUN a2enmod rewrite headers \
    && sed -ri 's!/var/www/html!/var/www/html/public!g' /etc/apache2/sites-available/*.conf \
    && sed -ri 's!AllowOverride None!AllowOverride All!g' /etc/apache2/apache2.conf

COPY --from=composer:2 /usr/bin/composer /usr/bin/composer

# зеркало Composer: repo.packagist.org недоступен
RUN composer config -g repos.packagist composer https://mirrors.cloud.tencent.com/composer/

WORKDIR /var/www/html

# зависимости ставятся при сборке образа
COPY composer.json composer.lock ./

RUN composer install \
        --no-dev \
        --no-scripts \
        --no-autoloader \
        --prefer-dist \
        --no-progress \
        --no-interaction

# только код приложения: vendor/, .env, .git в образ не попадают
COPY artisan ./
COPY app ./app
COPY bootstrap/app.php bootstrap/providers.php ./bootstrap/
COPY config ./config
COPY database ./database
COPY public ./public
COPY resources ./resources
COPY routes ./routes
COPY storage ./storage

RUN mkdir -p storage/logs \
        storage/framework/cache/data \
        storage/framework/sessions \
        storage/framework/views \
        bootstrap/cache \
    && rm -f bootstrap/cache/*.php \
    && composer dump-autoload --optimize --no-dev --no-scripts --no-interaction \
    && php artisan package:discover --ansi \
    && chown -R www-data:www-data storage bootstrap/cache

RUN php -r ' \
    $required = ["mbstring","zip","curl","openssl","dom","fileinfo","pdo_mysql","pcntl","intl","sockets","Zend OPcache"]; \
    $missing = array_values(array_filter($required, fn ($e) => ! extension_loaded($e))); \
    if ($missing) { fwrite(STDERR, "missing extensions: ".implode(", ", $missing).PHP_EOL); exit(1); } \
    fwrite(STDOUT, "extensions OK".PHP_EOL); \
'

EXPOSE 80