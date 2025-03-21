from django.urls import path
from . import views

app_name = 'home'

urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('category/<int:category_id>/', views.category_products, name='category'),
    path('product/<int:product_id>/', views.product_detail, name='product'),
]
