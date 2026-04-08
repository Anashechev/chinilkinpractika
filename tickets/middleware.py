import logging
from django.utils import timezone
from .models import LoginAttempt

logger = logging.getLogger(__name__)

class LoginAttemptMiddleware:
    """
    Middleware для отслеживания попыток входа и блокировки подозрительной активности
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        username = ''
        # Проверяем только POST запросы к странице входа
        if request.method == 'POST' and request.path == '/login/':
            username = request.POST.get('username', '')
            password = request.POST.get('password', '')
            
            # Логируем попытку входа
            self._log_login_attempt(request, username, success=False)
        
        response = self.get_response(request)
        
        # Проверяем, была ли попытка успешной после логирования
        if hasattr(response, 'status_code') and response.status_code == 302 and username:
            # Если вход успешный, обновляем последнюю попытку
            self._log_login_attempt(request, username, success=True)
        
        return response
    
    def _log_login_attempt(self, request, username, success=False, reason=''):
        """
        Логирование попытки входа
        """
        try:
            ip_address = self._get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            
            if success:
                logger.info(f"Successful login: {username} from {ip_address}")
                # Удаляем старые неудачные попытки для этого пользователя
                LoginAttempt.objects.filter(
                    username=username,
                    ip_address=ip_address,
                    is_successful=False
                ).delete()
            else:
                logger.warning(f"Failed login attempt: {username} from {ip_address} - {reason}")
                
                # Проверяем, не было ли слишком много неудачных попыток
                recent_attempts = LoginAttempt.objects.filter(
                    username=username,
                    ip_address=ip_address,
                    is_successful=False,
                    timestamp__gte=timezone.now() - timezone.timedelta(minutes=15)
                ).count()
                
                if recent_attempts >= 5:
                    logger.warning(f"Too many failed attempts for {username} from {ip_address}")
                    # Можно добавить блокировку или дополнительные меры безопасности
                    
        except Exception as e:
            logger.error(f"Error logging login attempt: {e}")
    
    def _get_client_ip(self, request):
        """
        Получение IP адреса клиента
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        
        return ip or '0.0.0.0'
