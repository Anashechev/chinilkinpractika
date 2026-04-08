from .models import Notification

def send_notification(recipient, notification_type, title, message, ticket=None):
    """
    Send a notification to a user.
    
    Args:
        recipient: User object to receive the notification
        notification_type: Type of notification (ticket_status, ticket_assigned, system)
        title: Title of the notification
        message: Message content
        ticket: Optional ticket object related to the notification
    """
    notification = Notification.objects.create(
        recipient=recipient,
        notification_type=notification_type,
        title=title,
        message=message,
        ticket=ticket
    )
    return notification

def send_ticket_status_notification(ticket, new_status, changed_by):
    """
    Send a notification when a ticket status changes.
    
    Args:
        ticket: Ticket object
        new_status: New status of the ticket
        changed_by: User who changed the status
    """
    title = f"Заявка #{ticket.id} - Статус изменен"
    message = f"Статус вашей заявки '{ticket.title}' был изменен на '{new_status.name}' пользователем {changed_by.full_name}."
    
    return send_notification(
        recipient=ticket.client,
        notification_type='ticket_status',
        title=title,
        message=message,
        ticket=ticket
    )

def send_ticket_assigned_notification(ticket, assignee, assigned_by):
    """
    Send a notification when a ticket is assigned to a worker.
    
    Args:
        ticket: Ticket object
        assignee: User assigned to the ticket
        assigned_by: User who assigned the ticket
    """
    title = f"Заявка #{ticket.id} - Назначена"
    message = f"Вы были назначены на заявку '#{ticket.id}: {ticket.title}' пользователем {assigned_by.full_name}."
    
    return send_notification(
        recipient=assignee,
        notification_type='ticket_assigned',
        title=title,
        message=message,
        ticket=ticket
    )