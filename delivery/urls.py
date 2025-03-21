from django.urls import path
from . import views

app_name = 'delivery'

urlpatterns = [
    path('login/', views.delivery_login, name='login'),
    path('logout/', views.delivery_logout, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('profile/', views.profile, name='profile'),
    path('change-password/', views.change_password, name='change_password'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('orders/', views.orders, name='orders'),
    path('order/<int:order_id>/', views.order_detail, name='order_detail'),
    path('order/<int:order_id>/update-status/', views.update_order_status, name='update_order_status'),
    path('order/<int:order_id>/send-otp/', views.send_otp, name='send_otp'),
    path('order/<int:order_id>/verify-otp/', views.verify_otp, name='verify_otp'),
    path('update-availability/', views.update_availability, name='update_availability'),
]
