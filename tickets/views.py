from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout, login, authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.utils import timezone
from django.http import HttpResponseForbidden, HttpResponse
from django.core.management import execute_from_command_line
from django.conf import settings
from django.urls import reverse
import os
import shutil
from .models import Role, Ticket, Equipment, ServiceType, TicketStatus, TicketStatusHistory, Notification, User, LoginAttempt
from .forms import CustomUserCreationForm, EquipmentForm, AdminEquipmentForm, LinkEquipmentForm, ServiceTypeForm, TicketStatusForm, CustomAuthenticationForm
from .utils import send_ticket_status_notification, send_ticket_assigned_notification

# Helper function to check user role
def check_role(user, role_name):
    return user.role.name == role_name

def login_success_animation(request):
    """Страница с анимацией успешного входа"""
    if not request.user.is_authenticated:
        return redirect('tickets:login')
    
    # Определяем URL для перенаправления в зависимости от роли
    if request.user.is_superuser or (request.user.role and request.user.role.name == Role.ADMIN):
        redirect_url = reverse('tickets:admin_dashboard')
    elif request.user.role and request.user.role.name == Role.DISPATCHER:
        redirect_url = reverse('tickets:dispatcher_dashboard')
    elif request.user.role and request.user.role.name == Role.WORKER:
        redirect_url = reverse('tickets:worker_dashboard')
    else:
        redirect_url = reverse('tickets:client_dashboard')
    
    return render(request, 'auth/success_animation.html', {
        'user': request.user,
        'redirect_url': redirect_url
    })

# Registration view
def register(request):
    # Regular users can only register as clients
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST, is_admin_registration=False)
        if form.is_valid():
            user = form.save(commit=False)
            
            # Устанавливаем email из поля contact если это email
            if '@' in user.contact:
                user.email = user.contact
            
            # Сохраняем пользователя (is_active=False по умолчанию)
            user.save()
            
            # Отправляем email подтверждения
            from .views_email_verification import send_verification_email
            
            if send_verification_email(user):
                messages.success(
                    request, 
                    f'Регистрация прошла успешно! Код подтверждения отправлен на {user.email}. '
                    'Проверьте почту (включая папку Спам) и подтвердите email для входа в систему.'
                )
                return redirect('tickets:verify_email', user_id=user.id)
            else:
                messages.error(
                    request, 
                    'Ошибка при отправке письма с подтверждением. '
                    'Попробуйте войти позже или запросите повторную отправку кода.'
                )
                return redirect('tickets:resend_verification')
    else:
        form = CustomUserCreationForm(is_admin_registration=False)
    
    return render(request, 'registration/register.html', {'form': form})

# Admin registration view
@login_required
def admin_register(request):
    # Only admins can access this view
    if not check_role(request.user, Role.ADMIN):
        return HttpResponseForbidden("Доступ запрещен")
    
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST, is_admin_registration=True)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'Пользователь {user.username} успешно создан!')
            return redirect('tickets:manage_users')
    else:
        form = CustomUserCreationForm(is_admin_registration=True)
    return render(request, 'registration/register.html', {'form': form})

# Login view
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required

@csrf_exempt
def get_user_session(request):
    """Возвращает данные о пользователе из сессии для анимации"""
    if request.method == 'GET':
        username = request.session.get('last_username', request.user.username if request.user.is_authenticated else 'Пользователь')
        
        # Правильно определяем роль
        if request.user.is_authenticated:
            if request.user.is_superuser:
                user_role = 'Суперадминистратор'
                print(f"DEBUG: Superuser detected: {request.user.username}")
            elif request.user.role:
                user_role = request.user.role.get_name_display()
                print(f"DEBUG: User role from model: {request.user.role.name} -> {user_role}")
            else:
                user_role = 'Пользователь'
                print(f"DEBUG: No role for authenticated user: {request.user.username}")
        else:
            user_role = request.session.get('last_user_role', 'Пользователь')
            print(f"DEBUG: Role from session: {user_role}")
        
        print(f"DEBUG: Final role for animation: {user_role}")
        return JsonResponse({
            'username': username,
            'user_role': user_role
        })
    return JsonResponse({'error': 'Method not allowed'}, status=405)

def user_login(request):
    """Улучшенная функция входа с логированием и проверкой подтверждения email"""
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            
            # Аутентификация
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                # Проверяем подтверждение email
                if not user.email_verified:
                    messages.error(
                        request, 
                        'Ваш email не подтвержден. Пожалуйста, подтвердите email перед входом в систему. '
                        f'Проверьте почту {user.email} или запросите повторную отправку кода.'
                    )
                    return redirect('tickets:resend_verification')
                
                # Проверяем, что аккаунт активен
                if not user.is_active:
                    messages.error(
                        request, 
                        'Ваш аккаунт неактивен. Свяжитесь с администратором.'
                    )
                    return redirect('tickets:login')
                
                # Успешный вход
                login(request, user)
                
                # Сохраняем информацию о пользователе для анимации
                request.session['last_username'] = user.username
                
                # Правильно определяем роль для анимации
                if user.is_superuser:
                    user_role_display = 'Суперадминистратор'
                elif user.role:
                    user_role_display = user.role.get_name_display()
                    print(f"DEBUG: User role found: {user.role.name} -> {user_role_display}")
                else:
                    user_role_display = 'Пользователь'
                    print(f"DEBUG: No role found for user {user.username}")
                
                print(f"DEBUG: Saving role in session: {user_role_display}")
                request.session['last_user_role'] = user_role_display
                
                # Записываем успешную попытку через middleware
                # Middleware автоматически обработает успешный вход
                
                # Добавляем сообщение об успешном входе для анимации
                messages.success(
                    request, 
                    f'Добро пожаловать, {user.username}! Вход выполнен успешно.'
                )
                
                # Перенаправляем на страницу с анимацией
                return redirect('tickets:login_success_animation')
            else:
                messages.error(request, 'Неверное имя пользователя или пароль.')
                
                # Проверяем, не было ли слишком много попыток
                recent_attempts = LoginAttempt.objects.filter(
                    username=username,
                    is_successful=False,
                    timestamp__gte=timezone.now() - timezone.timedelta(minutes=15)
                ).count()
                
                if recent_attempts >= 5:
                    messages.error(request, 'Слишком много попыток входа. Попробуйте позже.')
                    return render(request, 'registration/login.html', {'form': form})
                
                return render(request, 'registration/login.html', {'form': form})
    else:
        form = CustomAuthenticationForm()
    
    return render(request, 'registration/login.html', {'form': form})

def user_logout(request):
    """Выход пользователя"""
    auth_logout(request)
    messages.success(request, 'Вы успешно вышли из системы.')
    return redirect('tickets:login')

# Common views
def home(request):
    if request.user.is_authenticated:
        role = request.user.role.name
        if role == Role.CLIENT:
            return redirect('tickets:client_dashboard')
        elif role == Role.DISPATCHER:
            return redirect('tickets:dispatcher_dashboard')
        elif role == Role.WORKER:
            return redirect('tickets:worker_dashboard')
        elif role == Role.ADMIN:
            return redirect('tickets:admin_dashboard')
    return render(request, 'base/home.html')

def logout_view(request):
    logout(request)
    return redirect('home')

# Client views
@login_required
def client_dashboard(request):
    if not check_role(request.user, Role.CLIENT):
        return HttpResponseForbidden("Доступ запрещен")
    return render(request, 'client/dashboard.html')

@login_required
def client_tickets(request):
    if not check_role(request.user, Role.CLIENT):
        return HttpResponseForbidden("Доступ запрещен")
    tickets = Ticket.objects.filter(client=request.user)
    return render(request, 'client/tickets.html', {'tickets': tickets})

@login_required
def create_ticket(request):
    if not check_role(request.user, Role.CLIENT):
        return HttpResponseForbidden("Доступ запрещен")
    if request.method == 'POST':
        # Handle form submission
        title = request.POST.get('title')
        equipment_id = request.POST.get('equipment')
        service_type_id = request.POST.get('service_type')
        description = request.POST.get('description')
        
        # Get the equipment
        try:
            equipment = Equipment.objects.get(id=equipment_id, owner=request.user)
        except Equipment.DoesNotExist:
            messages.error(request, 'Выбранная техника не найдена.')
            return redirect('tickets:create_ticket')
        
        # Get the service type (optional)
        service_type = None
        if service_type_id:
            try:
                service_type = ServiceType.objects.get(id=service_type_id)
            except ServiceType.DoesNotExist:
                pass
        
        # Get the NEW status
        try:
            new_status = TicketStatus.objects.get(name=TicketStatus.NEW)
        except TicketStatus.DoesNotExist:
            # If NEW status doesn't exist, create it
            new_status = TicketStatus.objects.create(name=TicketStatus.NEW)
        
        # Create the ticket
        ticket = Ticket.objects.create(
            client=request.user,
            equipment=equipment,
            service_type=service_type,
            current_status=new_status,
            title=title,
            description=description
        )
        
        messages.success(request, 'Заявка успешно создана!')
        return redirect('tickets:client_tickets')
    else:
        equipment_list = Equipment.objects.filter(owner=request.user)
        service_types = ServiceType.objects.all()
        return render(request, 'client/create_ticket.html', {
            'equipment_list': equipment_list,
            'service_types': service_types
        })

@login_required
def equipment_list(request):
    if not check_role(request.user, Role.CLIENT):
        return HttpResponseForbidden("Доступ запрещен")
    equipment = Equipment.objects.filter(owner=request.user)
    return render(request, 'client/equipment_list.html', {'equipment': equipment})

@login_required
def link_equipment(request):
    if not check_role(request.user, Role.CLIENT):
        return HttpResponseForbidden("Доступ запрещен")
    
    if request.method == 'POST':
        form = LinkEquipmentForm(request.POST)
        if form.is_valid():
            serial_number = form.cleaned_data['serial_number']
            try:
                equipment = Equipment.objects.get(serial_number=serial_number)
                if equipment.owner is None:
                    equipment.owner = request.user
                    equipment.save()
                    messages.success(request, f'Техника "{equipment.model}" успешно привязана к вашему аккаунту!')
                    return redirect('tickets:equipment_list')
                else:
                    messages.error(request, 'Эта техника уже привязана к другому пользователю.')
            except Equipment.DoesNotExist:
                messages.error(request, 'Техника с таким серийным номером не найдена.')
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме.')
    else:
        form = LinkEquipmentForm()
    
    return render(request, 'client/link_equipment.html', {'form': form})

@login_required
def client_view_ticket(request, ticket_id):
    """View ticket details for client without employee information"""
    ticket = get_object_or_404(Ticket, id=ticket_id, client=request.user)
    
    # Get ticket status history
    status_history = ticket.status_history.all().order_by('-changed_at')
    
    return render(request, 'client/view_ticket.html', {
        'ticket': ticket,
        'status_history': status_history
    })

# Dispatcher views
@login_required
def dispatcher_dashboard(request):
    if not check_role(request.user, Role.DISPATCHER):
        return HttpResponseForbidden("Доступ запрещен")
    
    # Get ticket statistics
    total_tickets = Ticket.objects.count()
    pending_tickets = Ticket.objects.filter(current_status__name=TicketStatus.NEW).count()
    assigned_tickets = Ticket.objects.filter(current_status__name=TicketStatus.ASSIGNED).count()
    in_progress_tickets = Ticket.objects.filter(current_status__name=TicketStatus.IN_PROGRESS).count()
    completed_tickets = Ticket.objects.filter(current_status__name=TicketStatus.DONE).count()
    
    # Get recent tickets
    recent_tickets = Ticket.objects.order_by('-created_at')[:5]
    
    context = {
        'total_tickets': total_tickets,
        'pending_tickets': pending_tickets,
        'assigned_tickets': assigned_tickets,
        'in_progress_tickets': in_progress_tickets,
        'completed_tickets': completed_tickets,
        'recent_tickets': recent_tickets
    }
    
    return render(request, 'dispatcher/dashboard.html', context)

@login_required
def new_tickets(request):
    if not check_role(request.user, Role.DISPATCHER):
        return HttpResponseForbidden("Доступ запрещен")
    new_status = TicketStatus.objects.get(name=TicketStatus.NEW)
    tickets = Ticket.objects.filter(current_status=new_status)
    return render(request, 'dispatcher/new_tickets.html', {'tickets': tickets})

@login_required
def all_tickets(request):
    if not check_role(request.user, Role.DISPATCHER):
        return HttpResponseForbidden("Доступ запрещен")
    tickets = Ticket.objects.all()
    return render(request, 'dispatcher/all_tickets.html', {'tickets': tickets})

@login_required
def assign_ticket(request, ticket_id):
    if not check_role(request.user, Role.DISPATCHER):
        return HttpResponseForbidden("Доступ запрещен")
    
    ticket = get_object_or_404(Ticket, id=ticket_id)
    
    if request.method == 'POST':
        # Handle form submission
        worker_id = request.POST.get('worker')
        if worker_id:
            try:
                worker = User.objects.get(id=worker_id, role__name=Role.WORKER)
                # Update ticket status and assignee
                assigned_status = TicketStatus.objects.get(name=TicketStatus.ASSIGNED)
                ticket.assignee = worker
                ticket.current_status = assigned_status
                ticket.dispatcher = request.user
                ticket.save()
                
                # Create status history record
                TicketStatusHistory.objects.create(
                    ticket=ticket,
                    old_status=None,  # Assuming this is the first status change
                    new_status=assigned_status,
                    changed_by=request.user
                )
                
                # Send notification to worker
                send_ticket_assigned_notification(ticket, worker, request.user)
                
                messages.success(request, f'Заявка назначена работнику {worker.full_name}')
                return redirect('tickets:new_tickets')
            except User.DoesNotExist:
                messages.error(request, 'Выбранный работник не найден')
            except TicketStatus.DoesNotExist:
                messages.error(request, 'Статус "Назначено" не найден')
        else:
            messages.error(request, 'Не выбран работник')
        return render(request, 'dispatcher/assign_ticket.html', {'ticket': ticket})
    else:
        # Get all workers for the dropdown
        workers = User.objects.filter(role__name=Role.WORKER)
        return render(request, 'dispatcher/assign_ticket.html', {'ticket': ticket, 'workers': workers})

@login_required
def reports(request):
    if not check_role(request.user, Role.DISPATCHER):
        return HttpResponseForbidden("Доступ запрещен")
    # Generate reports
    # Get ticket statistics
    total_tickets = Ticket.objects.count()
    pending_tickets = Ticket.objects.filter(current_status__name=TicketStatus.NEW).count()
    in_progress_tickets = Ticket.objects.filter(current_status__name=TicketStatus.IN_PROGRESS).count()
    completed_tickets = Ticket.objects.filter(current_status__name=TicketStatus.DONE).count()
    
    # Get worker statistics (simplified)
    workers = User.objects.filter(role__name=Role.WORKER)
    workers_stats = []
    for worker in workers:
        assigned = Ticket.objects.filter(assignee=worker, current_status__name=TicketStatus.ASSIGNED).count()
        in_progress = Ticket.objects.filter(assignee=worker, current_status__name=TicketStatus.IN_PROGRESS).count()
        completed = Ticket.objects.filter(assignee=worker, current_status__name=TicketStatus.DONE).count()
        total_assigned = assigned + in_progress + completed
        efficiency = round((completed / total_assigned * 100) if total_assigned > 0 else 0, 1)
        
        workers_stats.append({
            'name': worker.full_name,
            'assigned': assigned,
            'in_progress': in_progress,
            'completed': completed,
            'efficiency': efficiency
        })
    
    return render(request, 'dispatcher/reports.html', {
        'total_tickets': total_tickets,
        'pending_tickets': pending_tickets,
        'in_progress_tickets': in_progress_tickets,
        'completed_tickets': completed_tickets,
        'workers_stats': workers_stats
    })

# Worker views
@login_required
def worker_dashboard(request):
    if not check_role(request.user, Role.WORKER):
        return HttpResponseForbidden("Доступ запрещен")
    
    # Get worker statistics
    assigned_tickets = Ticket.objects.filter(assignee=request.user, current_status__name=TicketStatus.ASSIGNED).count()
    in_progress_tickets = Ticket.objects.filter(assignee=request.user, current_status__name=TicketStatus.IN_PROGRESS).count()
    completed_tickets = Ticket.objects.filter(assignee=request.user, current_status__name=TicketStatus.DONE).count()
    total_tickets = assigned_tickets + in_progress_tickets + completed_tickets
    
    # Calculate completion rate
    completion_rate = round((completed_tickets / total_tickets * 100) if total_tickets > 0 else 0, 1)
    
    # Get recent tickets
    recent_tickets = Ticket.objects.filter(assignee=request.user).order_by('-created_at')[:5]
    
    context = {
        'assigned_tickets': assigned_tickets,
        'in_progress_tickets': in_progress_tickets,
        'completed_tickets': completed_tickets,
        'total_tickets': total_tickets,
        'completion_rate': completion_rate,
        'recent_tickets': recent_tickets
    }
    
    return render(request, 'worker/dashboard.html', context)

@login_required
def assigned_tickets(request):
    if not check_role(request.user, Role.WORKER):
        return HttpResponseForbidden("Доступ запрещен")
    assigned_status = TicketStatus.objects.get(name=TicketStatus.ASSIGNED)
    tickets = Ticket.objects.filter(assignee=request.user, current_status=assigned_status)
    return render(request, 'worker/assigned_tickets.html', {'tickets': tickets})

@login_required
def in_progress_tickets(request):
    if not check_role(request.user, Role.WORKER):
        return HttpResponseForbidden("Доступ запрещен")
    in_progress_status = TicketStatus.objects.get(name=TicketStatus.IN_PROGRESS)
    tickets = Ticket.objects.filter(assignee=request.user, current_status=in_progress_status)
    return render(request, 'worker/in_progress.html', {'tickets': tickets})

@login_required
def completed_tickets(request):
    if not check_role(request.user, Role.WORKER):
        return HttpResponseForbidden("Доступ запрещен")
    # Use DONE status instead of COMPLETED
    done_status = TicketStatus.objects.get(name=TicketStatus.DONE)
    ready_status = TicketStatus.objects.get(name=TicketStatus.READY_FOR_PICKUP)
    tickets = Ticket.objects.filter(
        assignee=request.user
    ).filter(
        current_status__in=[done_status, ready_status]
    )
    return render(request, 'worker/completed_tickets.html', {'tickets': tickets})

@login_required
def start_work(request, ticket_id):
    if not check_role(request.user, Role.WORKER):
        return HttpResponseForbidden("Доступ запрещен")
    
    ticket = get_object_or_404(Ticket, id=ticket_id, assignee=request.user)
    
    if request.method == 'POST':
        # Handle form submission
        # Update ticket status to IN_PROGRESS
        try:
            in_progress_status = TicketStatus.objects.get(name=TicketStatus.IN_PROGRESS)
            old_status = ticket.current_status
            ticket.current_status = in_progress_status
            ticket.save()
            
            # Create status history record
            TicketStatusHistory.objects.create(
                ticket=ticket,
                old_status=old_status,
                new_status=in_progress_status,
                changed_by=request.user
            )
            
            # Send notification to client
            send_ticket_status_notification(ticket, in_progress_status, request.user)
            
            messages.success(request, 'Работа по заявке начата')
            return redirect('tickets:in_progress_tickets')
        except TicketStatus.DoesNotExist:
            messages.error(request, 'Статус "В работе" не найден')
            return render(request, 'worker/start_work.html', {'ticket': ticket})
    else:
        return render(request, 'worker/start_work.html', {'ticket': ticket})

@login_required
def complete_ticket(request, ticket_id):
    if not check_role(request.user, Role.WORKER):
        return HttpResponseForbidden("Доступ запрещен")
    
    ticket = get_object_or_404(Ticket, id=ticket_id, assignee=request.user)
    
    if request.method == 'POST':
        # Handle form submission
        # Update ticket status to DONE
        try:
            done_status = TicketStatus.objects.get(name=TicketStatus.DONE)
            old_status = ticket.current_status
            ticket.current_status = done_status
            ticket.completed_at = timezone.now()
            ticket.save()
            
            # Create status history record
            TicketStatusHistory.objects.create(
                ticket=ticket,
                old_status=old_status,
                new_status=done_status,
                changed_by=request.user
            )
            
            # Send notification to client
            send_ticket_status_notification(ticket, done_status, request.user)
            
            messages.success(request, 'Заявка завершена')
            return redirect('tickets:completed_tickets')
        except TicketStatus.DoesNotExist:
            messages.error(request, 'Статус "Завершено" не найден')
            return render(request, 'worker/complete_ticket.html', {'ticket': ticket})
    else:
        return render(request, 'worker/complete_ticket.html', {'ticket': ticket})

# Admin views
@login_required
def admin_dashboard(request):
    if not check_role(request.user, Role.ADMIN):
        return HttpResponseForbidden("Доступ запрещен")
    
    # Get system statistics
    total_users = User.objects.count()
    total_tickets = Ticket.objects.count()
    clients = User.objects.filter(role__name=Role.CLIENT).count()
    dispatchers = User.objects.filter(role__name=Role.DISPATCHER).count()
    workers = User.objects.filter(role__name=Role.WORKER).count()
    admins = User.objects.filter(role__name=Role.ADMIN).count()
    
    # Ticket status distribution
    new_tickets = Ticket.objects.filter(current_status__name=TicketStatus.NEW).count()
    assigned_tickets = Ticket.objects.filter(current_status__name=TicketStatus.ASSIGNED).count()
    in_progress_tickets = Ticket.objects.filter(current_status__name=TicketStatus.IN_PROGRESS).count()
    completed_tickets = Ticket.objects.filter(current_status__name=TicketStatus.DONE).count()
    cancelled_tickets = Ticket.objects.filter(current_status__name=TicketStatus.CANCELED).count()
    
    # Recent activity (simplified)
    recent_tickets = Ticket.objects.order_by('-created_at')[:5]
    
    context = {
        'total_users': total_users,
        'total_tickets': total_tickets,
        'clients': clients,
        'dispatchers': dispatchers,
        'workers': workers,
        'admins': admins,
        'new_tickets': new_tickets,
        'assigned_tickets': assigned_tickets,
        'in_progress_tickets': in_progress_tickets,
        'completed_tickets': completed_tickets,
        'cancelled_tickets': cancelled_tickets,
        'recent_tickets': recent_tickets
    }
    
    return render(request, 'admin_role/dashboard.html', context)

@login_required
def manage_users(request):
    if not check_role(request.user, Role.ADMIN):
        return HttpResponseForbidden("Доступ запрещен")
    
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        action = request.POST.get('action')
        
        try:
            user = User.objects.get(id=user_id)
            if action == 'deactivate':
                # Prevent deactivation of admins
                if user.role.name == Role.ADMIN:
                    messages.error(request, f'Невозможно деактивировать администратора {user.username}.')
                # Prevent admin from deactivating themselves
                elif user == request.user:
                    messages.error(request, 'Вы не можете деактивировать самого себя.')
                else:
                    user.is_active = False
                    messages.success(request, f'Пользователь {user.username} деактивирован.')
            elif action == 'activate':
                user.is_active = True
                messages.success(request, f'Пользователь {user.username} активирован.')
            user.save()
        except User.DoesNotExist:
            messages.error(request, 'Пользователь не найден.')
        
        return redirect('tickets:manage_users')
    
    # Получаем всех пользователей
    users = User.objects.all().order_by('-date_joined')
    return render(request, 'admin_role/users.html', {'users': users, 'current_user': request.user})

@login_required
def edit_user(request, user_id):
    if not check_role(request.user, Role.ADMIN):
        return HttpResponseForbidden("Доступ запрещен")
    
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        messages.error(request, 'Пользователь не найден.')
        return redirect('tickets:manage_users')
    
    # Prevent editing of superusers by regular admins
    if user.is_superuser and not request.user.is_superuser:
        messages.error(request, 'У вас нет прав для редактирования суперпользователя.')
        return redirect('tickets:manage_users')
    
    if request.method == 'POST':
        # Get the original password before processing the form
        original_password = user.password
        
        # Update user data from form
        user.username = request.POST.get('username', user.username)
        user.full_name = request.POST.get('full_name', user.full_name)
        user.contact = request.POST.get('contact', user.contact)
        
        # Prevent deactivation of admins
        if user.role.name == Role.ADMIN:
            user.is_active = True  # Always keep admins active
        else:
            user.is_active = request.POST.get('is_active') == 'on'
        
        # Handle role change
        role_id = request.POST.get('role')
        if role_id:
            try:
                role = Role.objects.get(id=role_id)
                # Prevent changing admin role to non-admin
                if user.role.name == Role.ADMIN and role.name != Role.ADMIN:
                    messages.error(request, 'Невозможно изменить роль администратора на другую.')
                    return render(request, 'admin_role/edit_user.html', {'user': user, 'roles': Role.objects.all()})
                user.role = role
            except Role.DoesNotExist:
                messages.error(request, 'Выбранная роль не существует.')
                return render(request, 'admin_role/edit_user.html', {'user': user, 'roles': Role.objects.all()})
        
        # Handle password change (only if provided and not for admins)
        new_password = request.POST.get('password')
        if user.role.name != Role.ADMIN and new_password:
            user.set_password(new_password)
        else:
            # Keep the original password
            user.password = original_password
        
        # Save the user
        user.save()
        
        messages.success(request, f'Пользователь {user.username} успешно обновлен.')
        return redirect('tickets:manage_users')
    
    # GET request - show edit form
    roles = Role.objects.all()
    return render(request, 'admin_role/edit_user.html', {'user': user, 'roles': roles})

@login_required
def service_types(request):
    if not check_role(request.user, Role.ADMIN):
        return HttpResponseForbidden("Доступ запрещен")
    
    if request.method == 'POST':
        if 'delete_id' in request.POST:
            # Удаление типа услуги
            service_type_id = request.POST.get('delete_id')
            try:
                service_type = ServiceType.objects.get(id=service_type_id)
                service_type.delete()
                messages.success(request, 'Тип услуги успешно удален.')
            except ServiceType.DoesNotExist:
                messages.error(request, 'Тип услуги не найден.')
            return redirect('tickets:service_types')
        else:
            # Создание или редактирование типа услуги
            service_type_id = request.POST.get('service_type_id')
            if service_type_id:
                # Редактирование существующего типа услуги
                try:
                    service_type = ServiceType.objects.get(id=service_type_id)
                    form = ServiceTypeForm(request.POST, instance=service_type)
                except ServiceType.DoesNotExist:
                    messages.error(request, 'Тип услуги не найден.')
                    return redirect('tickets:service_types')
            else:
                # Создание нового типа услуги
                form = ServiceTypeForm(request.POST)
            
            if form.is_valid():
                service_type = form.save()
                if service_type_id:
                    messages.success(request, f'Тип услуги "{service_type.name}" успешно обновлен.')
                else:
                    messages.success(request, f'Тип услуги "{service_type.name}" успешно создан.')
                return redirect('tickets:service_types')
            else:
                messages.error(request, 'Пожалуйста, исправьте ошибки в форме.')
                service_types = ServiceType.objects.all()
                return render(request, 'admin_role/service_types.html', {
                    'service_types': service_types,
                    'form': form,
                    'editing': service_type_id
                })
    
    # GET запрос - отображение списка типов услуг
    service_types = ServiceType.objects.all()
    
    # Check if editing a service type
    edit_id = request.GET.get('edit')
    if edit_id:
        try:
            service_type = ServiceType.objects.get(id=edit_id)
            form = ServiceTypeForm(instance=service_type)
        except ServiceType.DoesNotExist:
            form = ServiceTypeForm()
    else:
        form = ServiceTypeForm()
    
    return render(request, 'admin_role/service_types.html', {
        'service_types': service_types,
        'form': form,
        'editing': edit_id
    })

@login_required
def ticket_statuses(request):
    if not check_role(request.user, Role.ADMIN):
        return HttpResponseForbidden("Доступ запрещен")
    
    # Check if viewing tickets for a specific status
    status_id = request.GET.get('view_tickets')
    if status_id:
        try:
            status = TicketStatus.objects.get(id=status_id)
            tickets = Ticket.objects.filter(current_status=status)
            return render(request, 'admin_role/ticket_status_detail.html', {
                'status': status,
                'tickets': tickets
            })
        except TicketStatus.DoesNotExist:
            messages.error(request, 'Статус заявки не найден.')
            return redirect('tickets:ticket_statuses')
    
    if request.method == 'POST':
        if 'delete_id' in request.POST:
            # Удаление статуса заявки
            status_id = request.POST.get('delete_id')
            try:
                status = TicketStatus.objects.get(id=status_id)
                # Проверяем, что статус не используется в заявках
                if Ticket.objects.filter(current_status=status).exists():
                    messages.error(request, 'Невозможно удалить статус, так как он используется в заявках.')
                else:
                    status.delete()
                    messages.success(request, 'Статус заявки успешно удален.')
            except TicketStatus.DoesNotExist:
                messages.error(request, 'Статус заявки не найден.')
            return redirect('tickets:ticket_statuses')
        else:
            # Создание или редактирование статуса заявки
            status_id = request.POST.get('status_id')
            if status_id:
                # Редактирование существующего статуса заявки
                try:
                    status = TicketStatus.objects.get(id=status_id)
                    form = TicketStatusForm(request.POST, instance=status)
                except TicketStatus.DoesNotExist:
                    messages.error(request, 'Статус заявки не найден.')
                    return redirect('tickets:ticket_statuses')
            else:
                # Создание нового статуса заявки
                form = TicketStatusForm(request.POST)
            
            if form.is_valid():
                status = form.save()
                if status_id:
                    messages.success(request, f'Статус заявки "{status.name}" успешно обновлен.')
                else:
                    messages.success(request, f'Статус заявки "{status.name}" успешно создан.')
                return redirect('tickets:ticket_statuses')
            else:
                messages.error(request, 'Пожалуйста, исправьте ошибки в форме.')
                statuses = TicketStatus.objects.all()
                return render(request, 'admin_role/ticket_statuses.html', {
                    'statuses': statuses,
                    'form': form,
                    'editing': status_id
                })
    
    # GET запрос - отображение списка статусов заявок
    statuses = TicketStatus.objects.all()
    
    # Check if editing a status
    edit_id = request.GET.get('edit')
    if edit_id:
        try:
            status = TicketStatus.objects.get(id=edit_id)
            form = TicketStatusForm(instance=status)
        except TicketStatus.DoesNotExist:
            form = TicketStatusForm()
    else:
        form = TicketStatusForm()
    
    return render(request, 'admin_role/ticket_statuses.html', {
        'statuses': statuses,
        'form': form,
        'editing': edit_id
    })

@login_required
def admin_equipment_list(request):
    if not check_role(request.user, Role.ADMIN):
        return HttpResponseForbidden("Доступ запрещен")
    equipment = Equipment.objects.all()
    return render(request, 'admin_role/equipment_list.html', {'equipment': equipment})

@login_required
def add_admin_equipment(request):
    if not check_role(request.user, Role.ADMIN):
        return HttpResponseForbidden("Доступ запрещен")
    
    if request.method == 'POST':
        form = AdminEquipmentForm(request.POST)
        if form.is_valid():
            equipment = form.save()
            messages.success(request, 'Оборудование успешно добавлено!')
            return redirect('tickets:admin_equipment_list')
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме.')
    else:
        form = AdminEquipmentForm()
    
    return render(request, 'admin_role/add_equipment.html', {'form': form})

@login_required
def edit_admin_equipment(request, equipment_id):
    if not check_role(request.user, Role.ADMIN):
        return HttpResponseForbidden("Доступ запрещен")
    
    try:
        equipment = Equipment.objects.get(id=equipment_id)
    except Equipment.DoesNotExist:
        messages.error(request, 'Оборудование не найдено.')
        return redirect('tickets:admin_equipment_list')
    
    if request.method == 'POST':
        form = AdminEquipmentForm(request.POST, instance=equipment)
        if form.is_valid():
            equipment = form.save()
            messages.success(request, 'Оборудование успешно обновлено!')
            return redirect('tickets:admin_equipment_list')
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме.')
    else:
        form = AdminEquipmentForm(instance=equipment)
    
    return render(request, 'admin_role/add_equipment.html', {'form': form, 'equipment': equipment})

@login_required
def delete_admin_equipment(request, equipment_id):
    if not check_role(request.user, Role.ADMIN):
        return HttpResponseForbidden("Доступ запрещен")
    
    try:
        equipment = Equipment.objects.get(id=equipment_id)
        equipment.delete()
        messages.success(request, 'Оборудование успешно удалено!')
    except Equipment.DoesNotExist:
        messages.error(request, 'Оборудование не найдено.')
    
    return redirect('tickets:admin_equipment_list')

@login_required
def admin_reports(request):
    if not check_role(request.user, Role.ADMIN):
        return HttpResponseForbidden("Доступ запрещен")
    
    # Generate admin reports
    # Get system statistics
    total_users = User.objects.count()
    total_tickets = Ticket.objects.count()
    clients = User.objects.filter(role__name=Role.CLIENT).count()
    dispatchers = User.objects.filter(role__name=Role.DISPATCHER).count()
    workers = User.objects.filter(role__name=Role.WORKER).count()
    admins = User.objects.filter(role__name=Role.ADMIN).count()
    
    # Ticket status distribution
    new_tickets = Ticket.objects.filter(current_status__name=TicketStatus.NEW).count()
    assigned_tickets = Ticket.objects.filter(current_status__name=TicketStatus.ASSIGNED).count()
    in_progress_tickets = Ticket.objects.filter(current_status__name=TicketStatus.IN_PROGRESS).count()
    completed_tickets = Ticket.objects.filter(current_status__name=TicketStatus.DONE).count()
    cancelled_tickets = Ticket.objects.filter(current_status__name=TicketStatus.CANCELED).count()
    
    # Activity data for the last 12 months
    from django.db.models import Count
    from django.utils import timezone
    import json
    
    # Get current date
    now = timezone.now()
    
    # Prepare data for the chart
    months_labels = []
    new_tickets_data = []
    completed_tickets_data = []
    
    # Get data for the last 12 months
    for i in range(11, -1, -1):
        # Calculate the month
        month_start = now.replace(day=1) - timezone.timedelta(days=30*i)
        month_end = (month_start.replace(day=28) + timezone.timedelta(days=4)).replace(day=1) - timezone.timedelta(days=1)
        
        # Format month name
        months_labels.append(month_start.strftime('%b'))
        
        # Count new tickets for this month
        new_count = Ticket.objects.filter(
            created_at__gte=month_start,
            created_at__lte=month_end
        ).count()
        new_tickets_data.append(new_count)
        
        # Count completed tickets for this month
        completed_count = Ticket.objects.filter(
            completed_at__gte=month_start,
            completed_at__lte=month_end
        ).count()
        completed_tickets_data.append(completed_count)
    
    # Convert data to JSON for JavaScript
    chart_data = {
        'labels': months_labels,
        'new_tickets': new_tickets_data,
        'completed_tickets': completed_tickets_data
    }
    
    return render(request, 'admin_role/reports.html', {
        'total_users': total_users,
        'total_tickets': total_tickets,
        'clients': clients,
        'dispatchers': dispatchers,
        'workers': workers,
        'admins': admins,
        'new_tickets': new_tickets,
        'assigned_tickets': assigned_tickets,
        'in_progress_tickets': in_progress_tickets,
        'completed_tickets': completed_tickets,
        'cancelled_tickets': cancelled_tickets,
        'chart_data': json.dumps(chart_data)
    })

@login_required
def activity(request):
    if not check_role(request.user, Role.ADMIN):
        return HttpResponseForbidden("Доступ запрещен")
    # Show recent activity - simplified for now
    recent_activities = []
    tickets = Ticket.objects.order_by('-created_at')[:10]
    for ticket in tickets:
        recent_activities.append({
            'timestamp': ticket.created_at,
            'user': ticket.client,
            'action': 'Создана заявка',
            'object_repr': f'Заявка #{ticket.id}'
        })
    
    return render(request, 'admin_role/activity.html', {
        'recent_activities': recent_activities
    })

# Notification views
@login_required
def notifications(request):
    """Display user notifications"""
    notifications = Notification.objects.filter(recipient=request.user).order_by('-created_at')
    return render(request, 'base/notifications.html', {'notifications': notifications})

@login_required
def mark_notification_read(request, notification_id):
    """Mark a notification as read"""
    notification = get_object_or_404(Notification, id=notification_id, recipient=request.user)
    notification.is_read = True
    notification.save()
    return redirect('tickets:notifications')

@login_required
def mark_all_notifications_read(request):
    """Mark all notifications as read"""
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    messages.success(request, 'Все уведомления отмечены как прочитанные.')
    return redirect('tickets:notifications')

@login_required
def view_ticket(request, ticket_id):
    """View ticket details for any user who has access to it"""
    ticket = get_object_or_404(Ticket, id=ticket_id)
    
    # Check if user has permission to view this ticket
    if not (request.user == ticket.client or 
            request.user == ticket.assignee or 
            request.user == ticket.dispatcher or
            request.user.role.name == Role.ADMIN):
        return HttpResponseForbidden("Доступ запрещен")
    
    # Get ticket status history
    status_history = ticket.status_history.all().order_by('-changed_at')
    
    return render(request, 'tickets/view_ticket.html', {
        'ticket': ticket,
        'status_history': status_history
    })

@login_required
def add_comment(request, ticket_id):
    """Add comment to ticket"""
    ticket = get_object_or_404(Ticket, id=ticket_id)
    
    # Check if user has permission to comment on this ticket
    if not (request.user == ticket.client or 
            request.user == ticket.assignee or 
            request.user == ticket.dispatcher or
            request.user.role.name == Role.ADMIN):
        return HttpResponseForbidden("Доступ запрещен")
    
    if request.method == 'POST':
        comment_text = request.POST.get('comment')
        if comment_text:
            # Create status history record with comment
            TicketStatusHistory.objects.create(
                ticket=ticket,
                old_status=ticket.current_status,
                new_status=ticket.current_status,  # Same status, just adding comment
                changed_by=request.user,
                comment=comment_text
            )
            
            messages.success(request, 'Комментарий добавлен')
        else:
            messages.error(request, 'Комментарий не может быть пустым')
        
        # Redirect back to appropriate page based on user role
        if request.user.role.name == Role.CLIENT:
            return redirect('tickets:client_tickets')
        elif request.user.role.name == Role.DISPATCHER:
            return redirect('tickets:all_tickets')
        elif request.user.role.name == Role.WORKER:
            # Check ticket status to determine where to redirect
            if ticket.current_status.name == TicketStatus.ASSIGNED:
                return redirect('tickets:assigned_tickets')
            elif ticket.current_status.name == TicketStatus.IN_PROGRESS:
                return redirect('tickets:in_progress_tickets')
            else:
                return redirect('tickets:completed_tickets')
        else:  # ADMIN
            return redirect('tickets:admin_dashboard')
    
    # For GET request, show comment form
    return render(request, 'tickets/add_comment.html', {'ticket': ticket})


@login_required
def backup_database(request):
    """Create a backup of the database and download it to user's device"""
    if not request.user.role.name == Role.ADMIN:
        return HttpResponseForbidden("Доступ запрещен")
    
    if request.method == 'POST':
        try:
            # Get the database path
            db_path = settings.DATABASES['default']['NAME']
            
            # Create backup filename with timestamp
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"db_backup_{timestamp}.sqlite3"
            
            # Read the database file
            with open(db_path, 'rb') as db_file:
                response = HttpResponse(db_file.read(), content_type='application/octet-stream')
                response['Content-Disposition'] = f'attachment; filename={backup_filename}'
                return response
        except Exception as e:
            messages.error(request, f'Ошибка при создании резервной копии: {str(e)}')
            return redirect('tickets:backup_database')
    
    # For GET request, show backup page
    return render(request, 'admin_role/backup_restore.html')


@login_required
def restore_database(request):
    """Restore database from backup"""
    if not request.user.role.name == Role.ADMIN:
        return HttpResponseForbidden("Доступ запрещен")
    
    if request.method == 'POST' and request.FILES.get('backup_file'):
        try:
            # Get the uploaded file
            uploaded_file = request.FILES['backup_file']
            
            # Get the database path
            db_path = settings.DATABASES['default']['NAME']
            
            # Create backup of current database before restoring
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            current_backup_filename = f"olddb_{timestamp}.sqlite3"
            
            # Read current database for download
            with open(db_path, 'rb') as db_file:
                response = HttpResponse(db_file.read(), content_type='application/octet-stream')
                response['Content-Disposition'] = f'attachment; filename={current_backup_filename}'
                
                # Save uploaded file temporarily
                temp_path = os.path.join(os.path.dirname(db_path), 'temp_restore.sqlite3')
                with open(temp_path, 'wb+') as destination:
                    for chunk in uploaded_file.chunks():
                        destination.write(chunk)
                
                # Replace database with uploaded backup
                shutil.copy2(temp_path, db_path)
                
                # Clean up temporary file
                os.remove(temp_path)
                
                messages.success(request, 'База данных успешно восстановлена из резервной копии. Старая база данных была скачана как файл перед восстановлением.')
                
                return response
        except Exception as e:
            messages.error(request, f'Ошибка при восстановлении базы данных: {str(e)}')
            return redirect('tickets:backup_database')
    
    # For GET request, show restore page
    return render(request, 'admin_role/backup_restore.html')
