#!/usr/bin/env python
import os
import django
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import ssl

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chinilkin.settings')
django.setup()

from django.conf import settings

def test_alternative_smtp():
    print("=== Тест альтернативных SMTP настроек ===")
    
    # Пробуем Mail.ru как альтернативу
    try:
        print("\n1. Тест Mail.ru SMTP...")
        server = smtplib.SMTP('smtp.mail.ru', 25, timeout=10)
        server.set_debuglevel(1)
        
        server.connect('smtp.mail.ru', 25)
        server.starttls()
        server.login('anashechev@mail.ru', 'testpassword123')
        print("✅ Mail.ru SMTP работает!")
        server.quit()
        
    except Exception as e:
        print(f"❌ Mail.ru ошибка: {e}")
    
    # Пробуем Yandex
    try:
        print("\n2. Тест Yandex SMTP...")
        server = smtplib.SMTP('smtp.yandex.ru', 587, timeout=10)
        server.set_debuglevel(1)
        
        server.connect('smtp.yandex.ru', 587)
        server.starttls()
        server.login('anashechev@yandex.ru', 'testpassword123')
        print("✅ Yandex SMTP работает!")
        server.quit()
        
    except Exception as e:
        print(f"❌ Yandex ошибка: {e}")
    
    # Пробуем Gmail с другим подходом
    try:
        print("\n3. Тест Gmail с альтернативными настройками...")
        
        # Создаем SSL контекст
        context = ssl.create_default_context()
        
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=10, context=context)
        server.set_debuglevel(1)
        
        server.connect('smtp.gmail.com', 465)
        server.login('anashechev@gmail.com', 'nhwnygyutqgaitqm')
        print("✅ Gmail SSL работает!")
        server.quit()
        
    except Exception as e:
        print(f"❌ Gmail SSL ошибка: {e}")
    
    # Тест стандартного Gmail
    try:
        print("\n4. Тест стандартного Gmail (текущие настройки)...")
        
        server = smtplib.SMTP('smtp.gmail.com', 587, timeout=10)
        server.set_debuglevel(1)
        
        server.connect('smtp.gmail.com', 587)
        server.starttls()
        server.login('anashechev@gmail.com', 'nhwnygyutqgaitqm')
        print("✅ Стандартный Gmail работает!")
        server.quit()
        
    except Exception as e:
        print(f"❌ Стандартный Gmail ошибка: {e}")

if __name__ == "__main__":
    test_alternative_smtp()
