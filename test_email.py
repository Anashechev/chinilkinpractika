#!/usr/bin/env python
import os
import django
import smtplib
from email.mime.text import MIMEText

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chinilkin.settings')
django.setup()

from django.conf import settings

def test_smtp_connection():
    print("=== Тест SMTP подключения ===")
    print(f"Хост: {settings.EMAIL_HOST}")
    print(f"Порт: {settings.EMAIL_PORT}")
    print(f"TLS: {settings.EMAIL_USE_TLS}")
    print(f"SSL: {settings.EMAIL_USE_SSL}")
    print(f"Timeout: {settings.EMAIL_TIMEOUT}")
    print(f"Пользователь: {settings.EMAIL_HOST_USER}")
    
    try:
        # Создаем подключение
        server = smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT, timeout=settings.EMAIL_TIMEOUT)
        server.set_debuglevel(1)  # Включаем детальную отладку
        
        print("\n1. Подключаемся к серверу...")
        server.connect(settings.EMAIL_HOST, settings.EMAIL_PORT)
        
        if settings.EMAIL_USE_TLS:
            print("2. Включаем TLS...")
            server.starttls()
        
        print("3. Авторизуемся...")
        server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
        
        print("✅ SMTP подключение успешно!")
        
        # Тестовая отправка
        print("\n4. Отправляем тестовое письмо...")
        msg = MIMEText("Тестовое сообщение")
        msg['Subject'] = 'Тест SMTP'
        msg['From'] = settings.DEFAULT_FROM_EMAIL
        msg['To'] = settings.EMAIL_HOST_USER
        
        server.send_message(msg)
        print("✅ Письмо отправлено успешно!")
        
        server.quit()
        
    except Exception as e:
        print(f"❌ Ошибка: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_smtp_connection()
