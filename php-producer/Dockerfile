FROM php:8.3-apache

# Системные зависимости (только то, что нужно для компиляции расширений и Composer)
RUN apt-get update && apt-get install -y \
    git unzip zip libzip-dev default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*

# PHP-расширения (обязательные)
RUN docker-php-ext-install sockets zip bcmath mysqli

# Composer (из официального образа)
COPY --from=composer:latest /usr/bin/composer /usr/bin/composer

# Копируем код
COPY . /var/www/html/

RUN rm -rf /var/www/html/vendor
# Устанавливаем зависимости через Composer
RUN composer install --no-dev --no-scripts --no-autoloader -v

# Права для Apache
RUN chown -R www-data:www-data /var/www/html

EXPOSE 80