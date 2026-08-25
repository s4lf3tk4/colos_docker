FROM php:8.3-apache

# Системные зависимости
RUN apt-get update && apt-get install -y \
    git unzip zip libzip-dev default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*

# PHP-расширения
RUN docker-php-ext-install sockets zip bcmath mysqli

# Composer
COPY --from=composer:latest /usr/bin/composer /usr/bin/composer

# Устанавливаем рабочую директорию
WORKDIR /var/www/html

# Копируем только composer.json и composer.lock (для кеширования)
COPY composer.json ./

# Устанавливаем зависимости (генерируем autoloader)
RUN composer install --no-dev --no-scripts --optimize-autoloader

# Копируем остальной код
COPY . .

# Права для Apache
RUN chown -R www-data:www-data /var/www/html \
    && chmod -R 755 /var/www/html

# Включаем mod_rewrite (если нужно)
RUN a2enmod rewrite

EXPOSE 80