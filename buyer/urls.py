from django.urls import path, reverse_lazy
from . import views
from django.contrib.auth import views as auth_views

app_name = 'buyer'

urlpatterns = [
    # Authentication URLs
    path('register/', views.buyer_register, name='register'),
    path('login/', views.buyer_login, name='login'),
    path('logout/', views.buyer_logout, name='logout'),
    # Password reset URLs
    path('password-reset/', views.custom_password_reset, name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='buyer/auth/password_reset_done.html'
    ), name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='buyer/auth/password_reset_confirm.html'
    ), name='password_reset_confirm'),
    path('password-reset-complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='buyer/auth/password_reset_complete.html'
    ), name='password_reset_complete'),
    
    # Profile Management
    path('profile/', views.profile, name='profile'),
    path('addresses/', views.manage_addresses, name='manage_addresses'),
    path('address/edit/<int:address_id>/', views.edit_address, name='edit_address'),
    path('address/delete/<int:address_id>/', views.delete_address, name='delete_address'),
    
    # Wishlist
    path('wishlist/', views.wishlist, name='wishlist'),
    path('wishlist/add/<int:product_id>/', views.add_to_wishlist, name='add_to_wishlist'),
    path('wishlist/remove/<int:product_id>/', views.remove_from_wishlist, name='remove_from_wishlist'),
    
    # Cart
    path('cart/', views.cart, name='cart'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/update/<int:cart_item_id>/', views.update_cart, name='update_cart'),
    path('cart/remove/<int:cart_item_id>/', views.remove_from_cart, name='remove_from_cart'),
    
    # Orders
    path('checkout/', views.checkout, name='checkout'),
    path('orders/', views.order_history, name='order_history'),
    path('order/<int:order_id>/', views.order_detail, name='order_detail'),
    path('order/<int:order_id>/cancel/', views.cancel_order, name='cancel_order'),
    
    # Payment
    path('payment/<int:order_id>/', views.payment_page, name='payment_page'),
    path('payment/initiate/', views.initiate_payment, name='initiate_payment'),
    path('payment/callback/', views.payment_callback, name='payment_callback'),
    path('payment/failed/', views.payment_failed, name='payment_failed'),
    
    # Reviews
    path('review/add/<int:product_id>/', views.add_review, name='add_review'),
    
    # Search
    path('search/', views.search_products, name='search_products'),
    
    # Location Verification
    path('verify-location/', views.verify_location, name='verify_location'),
    path('clear-location-modal/', views.clear_location_modal, name='clear_location_modal'),
    path('delete-account/', views.delete_account, name='delete_account'),
    path('confirm-delete/<uidb64>/<token>/', views.confirm_delete, name='confirm_delete'),
]
