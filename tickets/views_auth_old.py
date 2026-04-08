from django.shortcuts import render, redirect
from django.contrib.auth.views import PasswordResetView, PasswordResetDoneView, PasswordResetConfirmView, PasswordResetCompleteView
from django.contrib import messages
from .forms import CustomPasswordResetForm

class CustomPasswordResetView(PasswordResetView):
    form_class = CustomPasswordResetForm
    template_name = 'registration/password_reset_form.html'
    email_template_name = 'registration/password_reset_email.html'
    subject_template_name = 'registration/password_reset_subject.txt'
    
    def form_valid(self, form):
        # Добавляем сообщение об успешной отправке
        messages.success(
            self.request, 
            'Инструкции по восстановлению пароля отправлены на ваш email. '
            'Проверьте почту (включая папку Спам).'
        )
        return super().form_valid(form)
    
    def form_invalid(self, form):
        # Добавляем сообщение об ошибке
        messages.error(
            self.request, 
            'Ошибка при отправке письма. Пожалуйста, проверьте правильность email.'
        )
        return super().form_invalid(form)

class CustomPasswordResetDoneView(PasswordResetDoneView):
    template_name = 'registration/password_reset_done.html'

class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'registration/password_reset_confirm.html'
    
    def form_valid(self, form):
        messages.success(
            self.request,
            'Пароль успешно изменен! Теперь вы можете войти с новым паролем.'
        )
        return super().form_valid(form)

class CustomPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = 'registration/password_reset_complete.html'
