#Arquivo dockerfile para iniciar o apache com os modulos do PHP corretos.
#Podemos adicionar configurações espeficias no servidor atravez de cosutmizações nos arquivos de configuração.

FROM php:7.4.3-apache
RUN docker-php-ext-install mysqli pdo pdo_mysql
#COPY 000-default.conf /etc/apache2/sites-available/000-default.conf
