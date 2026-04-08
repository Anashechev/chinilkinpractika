#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chinilkin.settings')
django.setup()

from tickets.models import User

print("=== Все пользователи в базе данных ===")
users = User.objects.all()

if not users:
    print("Пользователей не найдено!")
else:
    for u in users:
        print(f'ID: {u.id}')
        print(f'Username: "{u.username}"')
        print(f'Email: "{u.email}"')
        print(f'Full name: "{u.full_name}"')
        print(f'Email lower: "{u.email.lower()}"')
        print(f'Email strip: "{u.email.strip()}"')
        print('---')

print("\n=== Поиск по конкретному email ===")
test_emails = ["admin@example.com", "user@example.com", "test@test.com"]
for email in test_emails:
    exists = User.objects.filter(email__iexact=email).exists()
    print(f'Email "{email}": {"Найден" if exists else "Не найден"}')
