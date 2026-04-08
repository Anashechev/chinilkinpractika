from django.urls import path
from . import views
from . import views_auth
from . import views_email_verification

app_name = 'tickets'

urlpatterns = [
    # Home and auth
    path('', views.home, name='home'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register, name='register'),
    path('login-success/', views.login_success_animation, name='login_success_animation'),
    path('get_user_session/', views.get_user_session, name='get_user_session'),
    
    # Password reset with code system
    path('password_reset/', views_auth.password_reset_request, name='password_reset'),
    path('password_reset/code/', views_auth.password_reset_code, name='password_reset_code'),
    path('password_reset/confirm/', views_auth.password_reset_confirm, name='password_reset_confirm'),
    path('password_reset/complete/', views_auth.password_reset_complete, name='password_reset_complete'),
    
    # Email verification system
    path('verify-email/<int:user_id>/', views_email_verification.verify_email, name='verify_email'),
    path('resend-verification/', views_email_verification.resend_verification, name='resend_verification'),
    
    # Admin registration
    path('admin-register/', views.admin_register, name='admin_register'),
    
    # Client dashboard
    path('client/dashboard/', views.client_dashboard, name='client_dashboard'),
    path('client/tickets/', views.client_tickets, name='client_tickets'),
    path('client/create-ticket/', views.create_ticket, name='create_ticket'),
    path('client/ticket/<int:ticket_id>/', views.client_view_ticket, name='client_view_ticket'),
    path('client/equipment/', views.equipment_list, name='equipment_list'),
    path('client/link-equipment/', views.link_equipment, name='link_equipment'),
    
    # Dispatcher dashboard
    path('dispatcher/dashboard/', views.dispatcher_dashboard, name='dispatcher_dashboard'),
    path('dispatcher/new-tickets/', views.new_tickets, name='new_tickets'),
    path('dispatcher/all-tickets/', views.all_tickets, name='all_tickets'),
    path('dispatcher/assign-ticket/<int:ticket_id>/', views.assign_ticket, name='assign_ticket'),
    path('dispatcher/reports/', views.reports, name='reports'),
    
    # Worker dashboard
    path('worker/dashboard/', views.worker_dashboard, name='worker_dashboard'),
    path('worker/assigned-tickets/', views.assigned_tickets, name='assigned_tickets'),
    path('worker/in-progress/', views.in_progress_tickets, name='in_progress_tickets'),
    path('worker/completed-tickets/', views.completed_tickets, name='completed_tickets'),
    path('worker/start-work/<int:ticket_id>/', views.start_work, name='start_work'),
    path('worker/complete-ticket/<int:ticket_id>/', views.complete_ticket, name='complete_ticket'),
    
    # Notifications
    path('notifications/', views.notifications, name='notifications'),
    path('notifications/<int:notification_id>/read/', views.mark_notification_read, name='mark_notification_read'),
    path('notifications/mark-all-read/', views.mark_all_notifications_read, name='mark_all_notifications_read'),
    
    # Universal ticket view
    path('ticket/<int:ticket_id>/', views.view_ticket, name='view_ticket'),
    
    # Admin dashboard
    path('admin-role/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-role/users/', views.manage_users, name='manage_users'),
    path('admin-role/users/edit/<int:user_id>/', views.edit_user, name='edit_user'),
    path('admin-role/service-types/', views.service_types, name='service_types'),
    path('admin-role/ticket-statuses/', views.ticket_statuses, name='ticket_statuses'),
    path('admin-role/equipment/', views.admin_equipment_list, name='admin_equipment_list'),
    path('admin-role/equipment/add/', views.add_admin_equipment, name='add_admin_equipment'),
    path('admin-role/equipment/edit/<int:equipment_id>/', views.edit_admin_equipment, name='edit_admin_equipment'),
    path('admin-role/equipment/delete/<int:equipment_id>/', views.delete_admin_equipment, name='delete_admin_equipment'),
    path('admin-role/reports/', views.admin_reports, name='admin_reports'),
    path('admin-role/activity/', views.activity, name='activity'),
    path('admin-role/backup/', views.backup_database, name='backup_database'),
    path('admin-role/restore/', views.restore_database, name='restore_database'),
]