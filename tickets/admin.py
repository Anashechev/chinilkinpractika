from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Role, ServiceType, TicketStatus, User, Equipment, Ticket, TicketStatusHistory, Notification

# Register the Role model
@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

# Register the ServiceType model
@admin.register(ServiceType)
class ServiceTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)

# Register the TicketStatus model
@admin.register(TicketStatus)
class TicketStatusAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

# Register the custom User model
@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'full_name', 'role', 'contact', 'is_active')
    list_filter = ('role', 'is_active')
    search_fields = ('username', 'full_name', 'contact')
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('full_name', 'contact', 'role')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'full_name', 'contact', 'role', 'password1', 'password2'),
        }),
    )

# Register the Equipment model
@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = ('owner', 'type', 'model', 'serial_number')
    list_filter = ('type',)
    search_fields = ('owner__username', 'model', 'serial_number')

# Register the Ticket model
@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'client', 'equipment', 'current_status', 'assignee', 'created_at')
    list_filter = ('current_status', 'service_type', 'created_at')
    search_fields = ('title', 'client__username', 'equipment__model')
    date_hierarchy = 'created_at'

# Register the TicketStatusHistory model
@admin.register(TicketStatusHistory)
class TicketStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ('ticket', 'old_status', 'new_status', 'changed_by', 'changed_at')
    list_filter = ('new_status', 'changed_at')
    search_fields = ('ticket__id', 'changed_by__username')
    date_hierarchy = 'changed_at'

# Register the Notification model
@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'title', 'notification_type', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read', 'created_at')
    search_fields = ('recipient__username', 'title')
    date_hierarchy = 'created_at'