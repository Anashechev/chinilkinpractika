from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.mail import send_mail
from django.utils import timezone
from django.conf import settings
from django.urls import reverse
from .forms import CustomPasswordResetForm, PasswordResetCodeForm, SetNewPasswordForm
from .models import PasswordResetCode, User
from django.core.exceptions import ValidationError
import random
import string

def password_reset_request(request):
    """Страница запроса восстановления пароля"""
    if request.method == 'POST':
        form = CustomPasswordResetForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            
            # Ищем пользователя - сначала в поле email (для новых пользователей), потом в contact
            user = User.objects.filter(email__iexact=email).first()
            
            if not user:
                # Проверяем поле contact (для старых пользователей)
                user = User.objects.filter(contact__iexact=email).first()
            
            print(f"DEBUG: Поиск пользователя для email {email}")
            print(f"DEBUG: Найден пользователь: {user}")
            if user:
                print(f"DEBUG: Пользователь email: {user.email}")
                print(f"DEBUG: Пользователь contact: {user.contact}")
                print(f"DEBUG: Email подтвержден: {user.email_verified}")
                print(f"DEBUG: Аккаунт активен: {user.is_active}")
            
            if user:
                # Удаляем старые коды для этого email
                PasswordResetCode.objects.filter(email=email).delete()
                
                # Генерируем новый код
                code = ''.join(random.choices(string.digits, k=6))
                expires_at = timezone.now() + timezone.timedelta(minutes=15)
                
                # Сохраняем код в базе
                PasswordResetCode.objects.create(
                    email=email,
                    code=code,
                    expires_at=expires_at
                )
                
                # Отправляем письмо
                try:
                    subject = 'Код восстановления пароля - Система обслуживания'
                    message = f'''
Здравствуйте!

Вы запросили восстановление пароля для вашей учетной записи.

Ваш код подтверждения: {code}

Код действителен в течение 15 минут.

Если вы не запрашивали восстановление, проигнорируйте это письмо.

С уважением,
Команда поддержки системы обслуживания
'''
                    
                    # Добавляем детальную отладку
                    print(f"Попытка отправки письма на {email}")
                    print(f"SMTP хост: {settings.EMAIL_HOST}")
                    print(f"SMTP порт: {settings.EMAIL_PORT}")
                    print(f"TLS: {settings.EMAIL_USE_TLS}")
                    print(f"Timeout: {settings.EMAIL_TIMEOUT}")
                    
                    result = send_mail(
                        subject=subject,
                        message=message,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[email],
                        fail_silently=False,
                    )
                    
                    print(f"Результат отправки: {result}")
                    
                    messages.success(
                        request, 
                        f'Код подтверждения отправлен на {email}. '
                        'Проверьте почту (включая папку Спам).'
                    )
                    
                    # Перенаправляем на страницу ввода кода
                    return redirect(reverse('tickets:password_reset_code') + f'?email={email}')
                    
                except Exception as e:
                    print(f"Детальная ошибка SMTP: {type(e).__name__}: {str(e)}")
                    
                    # Показываем пользователю более понятную ошибку
                    error_msg = str(e)
                    if "timed out" in error_msg.lower():
                        user_msg = "Ошибка подключения к почтовому серверу. Проверьте интернет-соединение и попробуйте еще раз."
                    elif "authentication" in error_msg.lower():
                        user_msg = "Ошибка аутентификации почты. Проверьте настройки SMTP."
                    elif "connection" in error_msg.lower():
                        user_msg = "Не удалось подключиться к почтовому серверу. Попробуйте позже."
                    else:
                        user_msg = f"Ошибка при отправке письма: {error_msg}"
                    
                    messages.error(request, user_msg)
                    
                    # Для отладки в режиме разработки
                    if settings.DEBUG:
                        # Показываем код в сообщении для тестирования
                        messages.info(request, f'ВАШ КОД ДЛЯ ТЕСТИРОВАНИЯ: {code}')
                        messages.warning(request, 'Режим отладки: код показан в сообщении выше')
            else:
                # Не сообщаем пользователю, что email не найден (безопасность)
                messages.success(
                    request, 
                    'Если учетная запись с таким email существует, '
                    'инструкции по восстановлению пароля будут отправлены на почту.'
                )
    else:
        form = CustomPasswordResetForm()
    
    return render(request, 'registration/password_reset_form.html', {'form': form})

def password_reset_code(request):
    """Страница ввода кода подтверждения"""
    email = request.GET.get('email', '')
    
    print(f"DEBUG password_reset_code - GET email: {email}")
    print(f"DEBUG password_reset_code - session before: {dict(request.session)}")
    
    if request.method == 'POST':
        form = PasswordResetCodeForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['code']
            email = request.POST.get('email', '')
            
            print(f"DEBUG password_reset_code - POST email: {email}")
            print(f"DEBUG password_reset_code - POST code: {code}")
            print(f"DEBUG password_reset_code - form data: {request.POST}")
            
            # Проверяем код
            try:
                reset_code = PasswordResetCode.objects.get(
                    email=email,
                    code=code,
                    is_used=False
                )
                
                print(f"DEBUG password_reset_code - found reset_code: {reset_code}")
                print(f"DEBUG password_reset_code - expires_at: {reset_code.expires_at}")
                print(f"DEBUG password_reset_code - is_expired: {reset_code.is_expired()}")
                
                if reset_code.is_expired():
                    messages.error(request, 'Срок действия кода истек. Запросите новый код.')
                    return redirect('tickets:password_reset')
                
                # Помечаем код как использованный
                reset_code.is_used = True
                reset_code.save()
                
                messages.success(request, 'Код подтвержден! Теперь установите новый пароль.')
                
                # Передаем email через URL параметр вместо сессии
                redirect_url = reverse('tickets:password_reset_confirm') + f'?email={email}'
                print(f"DEBUG password_reset_code - redirecting to: {redirect_url}")
                
                return redirect(redirect_url)
                
            except PasswordResetCode.DoesNotExist:
                print(f"DEBUG password_reset_code - code not found for email: {email}, code: {code}")
                messages.error(request, 'Неверный код подтверждения.')
    else:
        form = PasswordResetCodeForm()
    
    return render(request, 'registration/password_reset_code.html', {
        'form': form,
        'email': email
    })

def password_reset_confirm(request):
    """Страница установки нового пароля"""
    email = request.GET.get('email', '')
    
    print(f"DEBUG password_reset_confirm - email from URL: {email}")
    
    if not email:
        print("DEBUG password_reset_confirm - NO EMAIL IN URL!")
        messages.error(request, 'Недействительная ссылка. Начните процесс восстановления заново.')
        return redirect('tickets:password_reset')
    
    # Ищем пользователя - сначала в email, потом в contact
    user = User.objects.filter(email__iexact=email).first()
    if not user:
        user = User.objects.filter(contact__iexact=email).first()
    
    print(f"DEBUG password_reset_confirm - found user: {user}")
    
    if not user:
        print("DEBUG password_reset_confirm - USER NOT FOUND!")
        messages.error(request, 'Пользователь не найден. Начните процесс восстановления заново.')
        return redirect('tickets:password_reset')
    
    if request.method == 'POST':
        form = SetNewPasswordForm(request.POST)
        if form.is_valid():
            new_password = form.cleaned_data['new_password1']
            
            print(f"DEBUG password_reset_confirm - setting new password for user: {user.username}")
            
            # Устанавливаем новый пароль
            user.set_password(new_password)
            user.save()
            
            print(f"DEBUG password_reset_confirm - password saved successfully")
            
            messages.success(
                request,
                'Пароль успешно изменен! Теперь вы можете войти с новым паролем.'
            )
            return redirect('tickets:password_reset_complete')
    else:
        form = SetNewPasswordForm()
    
    return render(request, 'registration/password_reset_confirm.html', {
        'form': form,
        'email': email
    })

def password_reset_complete(request):
    """Страница завершения восстановления пароля"""
    return render(request, 'registration/password_reset_complete.html')
