from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse
from django.http import Http404
from django.utils import timezone
from .models import User
from .forms_email_verification import EmailVerificationForm, ResendVerificationForm

def send_verification_email(user):
    """Отправляет email с кодом подтверждения"""
    code = user.generate_verification_code()
    
    subject = 'Подтверждение email - Система обслуживания'
    message = f'''
Здравствуйте, {user.full_name}!

Вы зарегистрировались в системе обслуживания техники.

Для подтверждения вашего email введите следующий код:
{code}

Код действителен в течение 24 часов.

Если вы не регистрировались в нашей системе, проигнорируйте это письмо.

С уважением,
Команда поддержки системы обслуживания
'''
    
    try:
        result = send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        
        print(f"Email verification sent to {user.email}, result: {result}")
        return True
        
    except Exception as e:
        print(f"Error sending verification email: {e}")
        return False

def verify_email(request, user_id):
    """Страница подтверждения email"""
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        raise Http404("Пользователь не найден")
    
    # Если email уже подтвержден
    if user.email_verified:
        messages.info(request, 'Ваш email уже подтвержден. Вы можете войти в систему.')
        return redirect('tickets:login')
    
    if request.method == 'POST':
        form = EmailVerificationForm(user, request.POST)
        if form.is_valid():
            # Подтверждаем email
            user.verify_email()
            
            messages.success(
                request, 
                'Email успешно подтвержден! Теперь вы можете войти в систему.'
            )
            return redirect('tickets:login')
    else:
        form = EmailVerificationForm(user)
    
    return render(request, 'registration/verify_email.html', {
        'form': form,
        'user': user
    })

def resend_verification(request):
    """Повторная отправка кода подтверждения"""
    if request.method == 'POST':
        form = ResendVerificationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            
            # Ищем пользователя
            user = User.objects.filter(email__iexact=email).first()
            if not user:
                user = User.objects.filter(contact__iexact=email).first()
            
            if user and not user.email_verified:
                # Отправляем новый код
                if send_verification_email(user):
                    messages.success(
                        request, 
                        f'Новый код подтверждения отправлен на {email}. '
                        'Проверьте почту (включая папку Спам).'
                    )
                    
                    # Перенаправляем на страницу подтверждения
                    return redirect('tickets:verify_email', user_id=user.id)
                else:
                    messages.error(
                        request, 
                        'Ошибка при отправке письма. Попробуйте позже.'
                    )
            else:
                # Не сообщаем, что email не найден (безопасность)
                messages.success(
                    request, 
                    'Если учетная запись с таким email существует и не подтверждена, '
                    'новый код будет отправлен на почту.'
                )
    else:
        form = ResendVerificationForm()
    
    return render(request, 'registration/resend_verification.html', {'form': form})
