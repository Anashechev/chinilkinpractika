from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

class Command(BaseCommand):
    help = 'Активирует существующих пользователей и подтверждает их email для обратной совместимости'

    def handle(self, *args, **options):
        # Находим всех неактивных пользователей
        inactive_users = User.objects.filter(is_active=False)
        
        activated_count = 0
        for user in inactive_users:
            user.is_active = True
            user.email_verified = True
            user.email_verification_code = None
            user.email_verification_expires = None
            user.save()
            activated_count += 1
            self.stdout.write(
                self.style.SUCCESS(f'Активирован пользователь: {user.username} ({user.email})')
            )
        
        # Также проверяем пользователей с неподтвержденным email
        unverified_users = User.objects.filter(email_verified=False)
        for user in unverified_users:
            user.email_verified = True
            user.is_active = True
            user.email_verification_code = None
            user.email_verification_expires = None
            user.save()
            activated_count += 1
            self.stdout.write(
                self.style.SUCCESS(f'Подтвержден email пользователя: {user.username} ({user.email})')
            )
        
        total_users = User.objects.count()
        active_users = User.objects.filter(is_active=True).count()
        verified_users = User.objects.filter(email_verified=True).count()
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\nИтог:\n'
                f'Всего пользователей: {total_users}\n'
                f'Активных пользователей: {active_users}\n'
                f'С подтвержденным email: {verified_users}\n'
                f'Активировано в этой команде: {activated_count}'
            )
        )
