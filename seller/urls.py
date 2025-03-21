from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'profile', views.SellerProfileViewSet, basename='seller-profile')
router.register(r'products', views.ProductViewSet, basename='seller-products')
router.register(r'restock-requests', views.RestockRequestViewSet, basename='seller-restock')
router.register(r'notifications', views.NotificationViewSet, basename='seller-notifications')

urlpatterns = [
    path('login/', views.seller_login, name='login'),
    path('logout/', views.seller_logout, name='logout'),
    path('dashboard/', views.seller_dashboard, name='dashboard'),
    path('products/', views.seller_products, name='products'),
    path('restock-requests/', views.seller_restock_requests, name='restock_requests'),
    path('orders/', views.seller_orders, name='orders'),
    path('orders/<int:order_id>/', views.order_detail, name='order_detail'),
    path('orders/<int:order_id>/update-status/', views.update_order_status, name='update_order_status'),
    path('profile/', views.seller_profile, name='profile'),
    path('profile/change-password/', views.change_password, name='change_password'),
    path('delivery-boys/', views.delivery_boys, name='delivery_boys'),
    path('delivery-boys/add/', views.add_delivery_boy, name='add_delivery_boy'),
    path('delivery-boys/edit/<int:id>/', views.edit_delivery_boy, name='edit_delivery_boy'),
    path('delivery-boys/toggle-status/<int:id>/', views.toggle_delivery_boy_status, name='toggle_delivery_boy_status'),
    path('revenue/', views.revenue_page, name='revenue'),
    path('api/', include(router.urls)),
]
