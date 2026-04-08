from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordResetForm
from django.core.exceptions import ValidationError
from .models import User, Role, Equipment, ServiceType, TicketStatus
import random
import string
import re

def validate_full_name(value):
    """Валидатор для проверки корректности ФИО"""
    if not value or not value.strip():
        raise ValidationError('Поле ФИО обязательно для заполнения.')
    
    # Проверяем, что есть как минимум фамилия и имя
    words = value.strip().split()
    if len(words) < 2:
        raise ValidationError('ФИО должно содержать как минимум фамилию и имя.')
    
    # Проверяем, что все слова начинаются с заглавной буквы и содержат только буквы
    for word in words:
        if not re.match(r'^[А-Яа-яЁёA-Za-z]+$', word):
            raise ValidationError('ФИО должно содержать только буквы кириллицы или латиницы.')
        if not word[0].isupper():
            raise ValidationError('Каждое слово в ФИО должно начинаться с заглавной буквы.')

def validate_contact(value):
    """Валидатор для проверки контактной информации"""
    if not value or not value.strip():
        raise ValidationError('Поле контактной информации обязательно для заполнения.')
    
    return value

def validate_email_unique(value):
    """Валидатор для проверки уникальности email"""
    email = value.lower()
    
    # Проверяем уникальность email в полях contact и email
    if User.objects.filter(contact__iexact=email).exists():
        raise ValidationError('Пользователь с таким email уже существует.')
    
    if User.objects.filter(email__iexact=email).exists():
        raise ValidationError('Пользователь с таким email уже существует.')
    
    return email

def validate_email(value):
    """Валидатор для проверки email"""
    if not value or not value.strip():
        raise ValidationError('Email обязателен для заполнения.')
    
    # Проверяем формат email
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, value):
        raise ValidationError('Введите корректный email адрес.')
    
    return validate_email_unique(value)

def validate_username_unique(value):
    """Валидатор для проверки уникальности имени пользователя"""
    if User.objects.filter(username__iexact=value).exists():
        raise ValidationError('Пользователь с таким именем уже существует.')
    return value

def validate_password_strength(value):
    """Валидатор для проверки надежности пароля"""
    if len(value) < 8:
        raise ValidationError('Пароль должен содержать минимум 8 символов.')
    
    if not re.search(r'[A-Z]', value):
        raise ValidationError('Пароль должен содержать хотя бы одну заглавную букву.')
    
    if not re.search(r'[a-z]', value):
        raise ValidationError('Пароль должен содержать хотя бы одну строчную букву.')
    
    if not re.search(r'\d', value):
        raise ValidationError('Пароль должен содержать хотя бы одну цифру.')
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', value):
        raise ValidationError('Пароль должен содержать хотя бы один специальный символ.')
    
    return value

class CustomAuthenticationForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Введите ваше имя пользователя'
        })
        self.fields['password'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Введите ваш пароль'
        })
        self.fields['username'].label = 'Имя пользователя'
        self.fields['password'].label = 'Пароль'

class CustomPasswordResetForm(PasswordResetForm):
    """Кастомная форма восстановления пароля с проверкой существования email"""
    
    def clean_email(self):
        email = self.cleaned_data['email'].strip()
        
        # Ищем пользователя сначала в поле email (для новых пользователей)
        user = User.objects.filter(email__iexact=email).first()
        
        if not user:
            # Проверяем поле contact (для старых пользователей)
            user = User.objects.filter(contact__iexact=email).first()
        
        if not user:
            raise ValidationError(
                'Пользователь с таким email не найден в системе. '
                'Проверьте правильность введенного email.'
            )
        
        # Если нашли по contact и нет в поле email, копируем email
        if user and not user.email and user.contact and '@' in user.contact:
            user.email = user.contact
            user.save()
        
        return email

class CustomUserCreationForm(UserCreationForm):
    username = forms.CharField(
        max_length=150,
        label='Имя пользователя',
        validators=[validate_username_unique],
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    full_name = forms.CharField(max_length=100, label='ФИО', validators=[validate_full_name])
    contact = forms.EmailField(
        max_length=100, 
        label='Email',
        validators=[validate_email],
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'example@domain.com'})
    )
    role = forms.ModelChoiceField(
        queryset=Role.objects.exclude(name='ADMIN'),
        label='Роль',
        empty_label="Выберите роль",
        required=False
    )

    class Meta:
        model = User
        fields = ('username', 'full_name', 'contact', 'role', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        # Check if this is for admin registration
        self.is_admin_registration = kwargs.pop('is_admin_registration', False)
        super().__init__(*args, **kwargs)
        self.fields['password1'].label = 'Пароль'
        self.fields['password2'].label = 'Подтверждение пароля'
        
        # Add Bootstrap classes to form fields
        self.fields['full_name'].widget.attrs.update({'class': 'form-control'})
        self.fields['contact'].widget.attrs.update({'class': 'form-control'})
        self.fields['password1'].widget.attrs.update({'class': 'form-control'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control'})
        self.fields['role'].widget.attrs.update({'class': 'form-select'})
        
        # If not admin registration, hide role field (auto-assign client role)
        if not self.is_admin_registration:
            del self.fields['role']
        else:
            # For admin registration, include all roles
            admin_role = Role.objects.filter(name=Role.ADMIN).first()
            if admin_role:
                self.fields['role'].queryset = Role.objects.all()
            # Make role required for admin registration
            self.fields['role'].required = True
    
    def clean_password1(self):
        password = self.cleaned_data.get('password1')
        if password:
            validate_password_strength(password)
        return password
    
    def save(self, commit=True):
        user = super().save(commit=False)
        
        # Ensure role is set
        if not user.role:
            if self.is_admin_registration and self.cleaned_data.get('role'):
                user.role = self.cleaned_data['role']
            else:
                # Assign default client role for regular users
                client_role, created = Role.objects.get_or_create(name=Role.CLIENT, defaults={'name': Role.CLIENT})
                user.role = client_role
        
        if commit:
            user.save()
        return user

class EquipmentForm(forms.ModelForm):
    class Meta:
        model = Equipment
        fields = ['type', 'model', 'serial_number', 'notes']
        labels = {
            'type': 'Тип устройства',
            'model': 'Модель',
            'serial_number': 'Серийный номер',
            'notes': 'Примечания',
        }
        widgets = {
            'type': forms.Select(attrs={'class': 'form-select'}),
            'model': forms.TextInput(attrs={'class': 'form-control'}),
            'serial_number': forms.TextInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def save(self, commit=True):
        equipment = super().save(commit=False)
        
        # Generate unique 12-digit serial number if not provided
        if not equipment.serial_number:
            equipment.serial_number = self.generate_unique_serial_number()
        
        if commit:
            equipment.save()
        return equipment
    
    def generate_unique_serial_number(self):
        """Generate a unique 12-digit serial number"""
        while True:
            # Generate 12-digit number
            serial_number = ''.join(random.choices(string.digits, k=12))
            
            # Check if it's unique
            if not Equipment.objects.filter(serial_number=serial_number).exists():
                return serial_number

class AdminEquipmentForm(forms.ModelForm):
    class Meta:
        model = Equipment
        fields = ['type', 'model', 'serial_number', 'notes']
        labels = {
            'type': 'Тип устройства',
            'model': 'Модель',
            'serial_number': 'Серийный номер',
            'notes': 'Примечания',
        }
        widgets = {
            'type': forms.Select(attrs={'class': 'form-select'}),
            'model': forms.TextInput(attrs={'class': 'form-control'}),
            'serial_number': forms.TextInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def save(self, commit=True):
        equipment = super().save(commit=False)
        
        # Generate unique 12-digit serial number if not provided
        if not equipment.serial_number:
            equipment.serial_number = self.generate_unique_serial_number()
        
        # Owner is not set by admin - it will be set by client later
        equipment.owner = None
        
        if commit:
            equipment.save()
        return equipment
    
    def generate_unique_serial_number(self):
        """Generate a unique 12-digit serial number"""
        while True:
            # Generate 12-digit number
            serial_number = ''.join(random.choices(string.digits, k=12))
            
            # Check if it's unique
            if not Equipment.objects.filter(serial_number=serial_number).exists():
                return serial_number

class LinkEquipmentForm(forms.Form):
    serial_number = forms.CharField(
        max_length=12,
        label='Серийный номер',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    def clean_serial_number(self):
        serial_number = self.cleaned_data['serial_number']
        try:
            equipment = Equipment.objects.get(serial_number=serial_number)
            if equipment.owner:
                raise forms.ValidationError('Эта техника уже привязана к другому пользователю.')
        except Equipment.DoesNotExist:
            raise forms.ValidationError('Техника с таким серийным номером не найдена.')
        return serial_number

class ServiceTypeForm(forms.ModelForm):
    class Meta:
        model = ServiceType
        fields = ['name', 'description']
        labels = {
            'name': 'Название',
            'description': 'Описание',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class TicketStatusForm(forms.ModelForm):
    class Meta:
        model = TicketStatus
        fields = ['name']
        labels = {
            'name': 'Название',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
        }

# Форма для ввода кода подтверждения
class PasswordResetCodeForm(forms.Form):
    code = forms.CharField(
        max_length=6,
        min_length=6,
        label='Код подтверждения',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите 6-значный код',
            'pattern': '[0-9]{6}',
            'maxlength': '6'
        })
    )
    
    def clean_code(self):
        code = self.cleaned_data['code']
        
        # Проверяем, что код состоит только из цифр
        if not code.isdigit():
            raise ValidationError('Код должен состоять только из цифр.')
        
        return code

# Форма для установки нового пароля
class SetNewPasswordForm(forms.Form):
    new_password1 = forms.CharField(
        label='Новый пароль',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        help_text='Минимум 8 символов: заглавные, строчные буквы и цифры'
    )
    new_password2 = forms.CharField(
        label='Подтверждение пароля',
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    
    def clean_new_password1(self):
        password1 = self.cleaned_data.get('new_password1')
        if password1:
            validate_password_strength(password1)
        return password1
    
    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('new_password1')
        password2 = cleaned_data.get('new_password2')
        
        if password1 and password2 and password1 != password2:
            raise ValidationError('Пароли не совпадают.')
        
        return cleaned_data