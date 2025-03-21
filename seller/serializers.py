from rest_framework import serializers
from django.contrib.auth.models import User
from .models import SellerProfile, SellerNotification, SellerAnalytics
from admin_dashboard.models import Product, RestockRequest

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name')
        read_only_fields = ('id', 'username')

class SellerProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    supplier_name = serializers.CharField(source='supplier.business_name', read_only=True)
    image = serializers.ImageField(required=False, allow_null=True)
    
    class Meta:
        model = Product
        fields = ['id', 'name', 'category', 'category_name', 'supplier_name', 
                 'description', 'price', 'stock', 'image', 'status',
                 'threshold', 'is_featured', 'created_at', 'updated_at']
        read_only_fields = ('supplier', 'status', 'created_at', 'updated_at')

    def create(self, validated_data):
        validated_data['status'] = 'pending'
        return super().create(validated_data)

class SellerProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    supplier_name = serializers.CharField(source='supplier.business_name', read_only=True)
    total_products = serializers.IntegerField(source='supplier.products.count', read_only=True)
    
    class Meta:
        model = SellerProfile
        fields = '__all__'
        read_only_fields = ('user', 'supplier', 'created_at', 'updated_at')

class SellerNotificationSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='related_product.name', read_only=True)
    restock_request_quantity = serializers.IntegerField(source='related_restock_request.quantity', read_only=True)
    
    class Meta:
        model = SellerNotification
        fields = '__all__'
        read_only_fields = ('seller', 'created_at')

class SellerRestockRequestSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    
    class Meta:
        model = RestockRequest
        fields = ['id', 'product', 'product_name', 'quantity', 'notes', 
                 'status', 'requested_at', 'completed_at']
        read_only_fields = ('status', 'completed_at')

class SellerAnalyticsSerializer(serializers.ModelSerializer):
    seller_name = serializers.CharField(source='seller.user.get_full_name', read_only=True)
    
    class Meta:
        model = SellerAnalytics
        fields = '__all__'
        read_only_fields = ('seller', 'date')
