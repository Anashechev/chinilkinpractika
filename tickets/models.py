from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils import timezone
import uuid
import random
import string
import re

# Role model for user roles
class Role(models.Model):
    CLIENT = 'CLIENT'
    DISPATCHER = 'DISPATCHER'
    WORKER = 'WORKER'
    ADMIN = 'ADMIN'
    
    ROLE_CHOICES = [
        (CLIENT, 'Client'),
        (DISPATCHER, 'Dispatcher'),
        (WORKER, 'Worker'),
        (ADMIN, 'Admin'),
    ]
    
    name = models.CharField(max_length=20, choices=ROLE_CHOICES, unique=True)
    
    def __str__(self):
        return self.get_name_display()

# ServiceType model for types of services
class ServiceType(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Service Type"
        verbose_name_plural = "Service Types"

# TicketStatus model for ticket statuses
class TicketStatus(models.Model):
    NEW = 'NEW'
    ASSIGNED = 'ASSIGNED'
    IN_PROGRESS = 'IN_PROGRESS'
    DONE = 'DONE'
    READY_FOR_PICKUP = 'READY_FOR_PICKUP'
    CANCELED = 'CANCELED'
    
    STATUS_CHOICES = [
        (NEW, 'Новая'),
        (ASSIGNED, 'Назначена'),
        (IN_PROGRESS, 'В работе'),
        (DONE, 'Выполнена'),
        (READY_FOR_PICKUP, 'Готова к выдаче'),
        (CANCELED, 'Отменена'),
    ]
    
    name = models.CharField(max_length=20, choices=STATUS_CHOICES, unique=True)
    
    def __str__(self):
        return self.get_name_display()
    
    class Meta:
        verbose_name = "Ticket Status"
        verbose_name_plural = "Ticket Statuses"

# Custom User Manager
class UserManager(BaseUserManager):
    def create_user(self, username, email, password, full_name, contact, role, **extra_fields):
        if not username:
            raise ValueError('The Username field must be set')
        if not full_name:
            raise ValueError('The Full Name field must be set')
        if not contact:
            raise ValueError('The Contact field must be set')
        if not role:
            raise ValueError('The Role field must be set')
        
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, full_name=full_name, contact=contact, role=role, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, username, email, password, full_name='', contact='', **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        # Create or get ADMIN role
        admin_role, created = Role.objects.get_or_create(name=Role.ADMIN, defaults={'name': Role.ADMIN})
        
        # Set default values for superuser
        if not full_name:
            full_name = 'Administrator'
        if not contact:
            contact = email or 'admin@example.com'
        
        return self.create_user(username, email, password, full_name, contact, admin_role, **extra_fields)

# Custom User model
class User(AbstractUser):
    full_name = models.CharField(max_length=100)
    contact = models.CharField(max_length=100)  # phone or email
    role = models.ForeignKey(Role, on_delete=models.CASCADE, null=True, blank=True)
    is_active = models.BooleanField(default=False)  # False до подтверждения email
    email_verified = models.BooleanField(default=False)  # Подтверждение email
    email_verification_code = models.CharField(max_length=6, blank=True, null=True)  # Код подтверждения
    email_verification_expires = models.DateTimeField(null=True, blank=True)  # Срок действия кода
    
    objects = UserManager()
    
    def __str__(self):
        return f"{self.username} ({self.full_name})"
    
    def save(self, *args, **kwargs):
        # Ensure regular users have a role
        if not self.role and not self.is_superuser:
            # Assign default client role for regular users
            client_role, created = Role.objects.get_or_create(name=Role.CLIENT, defaults={'name': Role.CLIENT})
            self.role = client_role
        elif self.is_superuser and not self.role:
            # Assign admin role for superusers
            admin_role, created = Role.objects.get_or_create(name=Role.ADMIN, defaults={'name': Role.ADMIN})
            self.role = admin_role
        super().save(*args, **kwargs)
    
    def generate_verification_code(self):
        """Генерирует код подтверждения email"""
        import random
        import string
        from django.utils import timezone
        
        code = ''.join(random.choices(string.digits, k=6))
        expires_at = timezone.now() + timezone.timedelta(hours=24)  # Код действителен 24 часа
        
        self.email_verification_code = code
        self.email_verification_expires = expires_at
        self.save()
        
        return code
    
    def is_verification_code_valid(self, code):
        """Проверяет валидность кода подтверждения"""
        if not self.email_verification_code or not self.email_verification_expires:
            return False
        
        from django.utils import timezone
        
        if timezone.now() > self.email_verification_expires:
            return False
            
        return self.email_verification_code == code
    
    def verify_email(self):
        """Подтверждает email"""
        self.email_verified = True
        self.email_verification_code = None
        self.email_verification_expires = None
        self.is_active = True
        self.save()

# Equipment model for client devices
class Equipment(models.Model):
    DEVICE_TYPES = [
        ('laptop', 'Ноутбук'),
        ('desktop', 'Настольный компьютер'),
        ('phone', 'Телефон'),
        ('tablet', 'Планшет'),
        ('printer', 'Принтер'),
        ('other', 'Другое'),
    ]
    
    owner = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role__name': 'CLIENT'}, null=True, blank=True)
    type = models.CharField(max_length=20, choices=DEVICE_TYPES)
    model = models.CharField(max_length=100)
    serial_number = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.get_type_display()} - {self.model} ({self.owner.username})"
    
    class Meta:
        verbose_name = "Equipment"
        verbose_name_plural = "Equipment"

# Ticket model for service requests
class Ticket(models.Model):
    client = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role__name': 'CLIENT'}, related_name='client_tickets')
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE)
    service_type = models.ForeignKey(ServiceType, on_delete=models.SET_NULL, null=True, blank=True)
    current_status = models.ForeignKey(TicketStatus, on_delete=models.CASCADE)
    dispatcher = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, limit_choices_to={'role__name': 'DISPATCHER'}, related_name='dispatcher_tickets')
    assignee = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, limit_choices_to={'role__name': 'WORKER'}, related_name='assignee_tickets')
    title = models.CharField(max_length=200)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Ticket #{self.id}: {self.title} ({self.client.username})"
    
    class Meta:
        verbose_name = "Ticket"
        verbose_name_plural = "Tickets"

# TicketStatusHistory model for logging status changes
class TicketStatusHistory(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='status_history')
    old_status = models.ForeignKey(TicketStatus, on_delete=models.CASCADE, null=True, blank=True, related_name='old_status_histories')
    new_status = models.ForeignKey(TicketStatus, on_delete=models.CASCADE, related_name='new_status_histories')
    changed_by = models.ForeignKey(User, on_delete=models.CASCADE)
    changed_at = models.DateTimeField(auto_now_add=True)
    comment = models.TextField(blank=True)
    
    def __str__(self):
        return f"Status change for Ticket #{self.ticket.id}: {self.old_status} -> {self.new_status}"
    
    class Meta:
        verbose_name = "Ticket Status History"
        verbose_name_plural = "Ticket Status Histories"

# Notification model for user notifications
class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('ticket_status', 'Ticket Status Change'),
        ('ticket_assigned', 'Ticket Assigned'),
        ('system', 'System Notification'),
    ]
    
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, null=True, blank=True)
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return f"Notification for {self.recipient.username}: {self.title}"
    
    class Meta:
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        ordering = ['-created_at']

# LoginAttempt model for tracking login attempts
class LoginAttempt(models.Model):
    username = models.CharField(max_length=150)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    is_successful = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)
    reason = models.CharField(max_length=255, blank=True)
    
    class Meta:
        verbose_name = "Login Attempt"
        verbose_name_plural = "Login Attempts"
        ordering = ['-timestamp']
    
    def __str__(self):
        status = "Success" if self.is_successful else "Failed"
        return f"{status} login attempt for {self.username} at {self.timestamp}"

# PasswordResetCode model for password reset functionality
class PasswordResetCode(models.Model):
    email = models.EmailField()
    code = models.CharField(max_length=6)  # 6-значный код
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    
    def __str__(self):
        return f"Password reset code for {self.email}: {self.code}"
    
    def is_expired(self):
        return timezone.now() > self.expires_at
    
    @staticmethod
    def generate_code():
        return ''.join(random.choices(string.digits, k=6))
    
    class Meta:
        verbose_name = "Password Reset Code"
        verbose_name_plural = "Password Reset Codes"
        ordering = ['-created_at']