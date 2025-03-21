from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'admin_dashboard'

router = DefaultRouter()
router.register('categories', views.FoodCategoryViewSet, basename='category')
router.register('locations', views.LocationViewSet, basename='location')
router.register('suppliers', views.SupplierViewSet, basename='supplier')
router.register('products', views.ProductViewSet, basename='product')
router.register('restock-requests', views.RestockRequestViewSet, basename='restock-request')

urlpatterns = [
    path('', views.admin_dashboard, name='admin_dashboard'),
    path('login/', views.admin_login, name='admin_login'),
    path('logout/', views.admin_logout, name='admin_logout'),
    
    # Categories Management
    path('categories/', views.categories_list, name='categories_list'),
    path('categories/add/', views.add_category, name='add_category'),
    
    # Locations Management
    path('locations/', views.locations_list, name='locations_list'),
    path('locations/add/', views.add_location, name='add_location'),
    
    # Suppliers Management
    path('suppliers/', views.suppliers_list, name='suppliers_list'),
    path('suppliers/add/', views.add_supplier, name='add_supplier'),
    path('supplier/<int:supplier_id>/edit/', views.edit_supplier, name='edit_supplier'),
    path('supplier/<int:supplier_id>/delete/', views.delete_supplier, name='delete_supplier'),
    
    # Products Management
    path('products/', views.products_list, name='products_list'),
    path('products/<int:product_id>/approve/', views.approve_product, name='approve_product'),
    path('products/<int:product_id>/reject/', views.reject_product, name='reject_product'),
    path('products/<int:product_id>/toggle-featured/', views.toggle_featured, name='toggle_featured'),
    path('products/bulk-feature/', views.bulk_feature_products, name='bulk_feature_products'),
    
    # Restock Management
    path('restock-requests/', views.restock_requests, name='restock_requests'),
    path('restock-requests/create/<int:product_id>/', views.create_restock_request, name='create_restock_request'),
    path('restock-requests/approve/<int:request_id>/', views.approve_restock, name='approve_restock'),
    path('products/<int:product_id>/restock/', views.create_restock_request, name='create_restock_request'),
    
    # API URLs
    path('api/', include(router.urls)),
]
