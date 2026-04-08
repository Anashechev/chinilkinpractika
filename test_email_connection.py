#!/usr/bin/env python
"""Тест подключения к почтовому серверу"""

import os
import sys
import django
from django.core.mail import send_mail
from django.core.mail import EmailMessage
from django.conf import settings

# Добавляем путь к проекту
sys.path.append('c:\\Users\\anash\\OneDrive\\Рабочий стол\\chinilkin')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chinilkin.settings')
django.setup()

def test_email_connection():
    """Тестируем подключение к почтовому серверу"""
    
    print("=== Тест подключения к почтовому серверу ===")
    print(f"EMAIL_HOST: {settings.EMAIL_HOST}")
    print(f"EMAIL_PORT: {settings.EMAIL_PORT}")
    print(f"EMAIL_USE_TLS: {settings.EMAIL_USE_TLS}")
    print(f"EMAIL_USE_SSL: {settings.EMAIL_USE_SSL}")
    print(f"EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}")
    print(f"EMAIL_TIMEOUT: {settings.EMAIL_TIMEOUT}")
    print()
    
    try:
        # Тест 1: Простая проверка подключения
        print("1. Проверка базового подключения...")
        from django.core.mail import get_connection
        connection = get_connection()
        print("✓ Базовое подключение установлено")
        
        # Тест 2: Отправка тестового письма
        print("\n2. Отправка тестового письма...")
        subject = "Тестовое письмо от Django"
        message = "Это тестовое письмо для проверки почтовых настроек."
        from_email = settings.DEFAULT_FROM_EMAIL
        recipient_list = ['anashechev@gmail.com']  # Отправляем на тот же адрес
        
        result = send_mail(
            subject,
            message,
            from_email,
            recipient_list,
            fail_silently=False,
        )
        
        if result:
            print(f"✓ Письмо успешно отправлено! ID: {result}")
        else:
            print("✗ Письмо не отправлено")
            
    except Exception as e:
        print(f"✗ Ошибка: {e}")
        print(f"Тип ошибки: {type(e).__name__}")
        
        # Дополнительная диагностика
        if "SMTPAuthenticationError" in str(e):
            print("\nВозможные причины:")
            print("- Неверный пароль приложения (App Password)")
            print("- Двухфакторная аутентификация отключена")
            print("- Аккаунт Gmail заблокирован")
        elif "SMTPConnectError" in str(e):
            print("\nВозможные причины:")
            print("- Проблемы с интернет-соединением")
            print("- Блокировка порта 587")
            print("- Проблемы с DNS")
        elif "SMTPException" in str(e):
            print("\nВозможные причины:")
            print("- Неправильные настройки TLS/SSL")
            print("- Проблемы с сертификатами")
    
    print("\n=== Тест завершен ===")

if __name__ == "__main__":
    test_email_connection()
