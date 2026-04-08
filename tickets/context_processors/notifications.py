from tickets.models import Notification

def unread_notifications_count(request):
    """Add unread notifications count to context for all views"""
    if request.user.is_authenticated:
        unread_count = Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).count()
        return {'unread_count': unread_count}
    return {'unread_count': 0}