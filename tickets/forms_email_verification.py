from django import forms
from django.core.exceptions import ValidationError
from .models import User
import re

class EmailVerificationForm(forms.Form):
    """Форма для ввода кода подтверждения email"""
    code = forms.CharField(
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '000000',
            'pattern': '[0-9]{6}',
            'inputmode': 'numeric',
            'autocomplete': 'one-time-code'
        }),
        help_text='Введите 6-значный код, отправленный на ваш email'
    )
    
    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
    
    def clean_code(self):
        code = self.cleaned_data.get('code')
        
        if not self.user:
            raise ValidationError('Пользователь не найден')
        
        if not self.user.is_verification_code_valid(code):
            raise ValidationError('Неверный или истекший код подтверждения')
        
        return code

class ResendVerificationForm(forms.Form):
    """Форма для повторной отправки кода подтверждения"""
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите ваш email'
        })
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        
        # Проверяем, существует ли пользователь с таким email
        user = User.objects.filter(email__iexact=email).first()
        if not user:
            user = User.objects.filter(contact__iexact=email).first()
        
        if not user:
            raise ValidationError('Пользователь с таким email не найден')
        
        if user.email_verified:
            raise ValidationError('Этот email уже подтвержден')
        
        return email
