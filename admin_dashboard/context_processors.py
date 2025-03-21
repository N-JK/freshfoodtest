from .models import Product, RestockRequest

def admin_notifications(request):
    """Add notification counts to all admin templates"""
    if not request.user.is_authenticated or not request.user.is_staff:
        return {}
        
    return {
        'low_stock_count': Product.objects.filter(stock__lte=10).count(),
        'pending_restock_count': RestockRequest.objects.filter(status='pending').count()
    }
