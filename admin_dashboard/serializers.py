from rest_framework import serializers
from django.contrib.auth.models import User
from .models import FoodCategory, Location, Supplier, Product, RestockRequest
import random
import string

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email')

class FoodCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = FoodCategory
        fields = '__all__'

class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = '__all__'

class SupplierSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    categories = serializers.PrimaryKeyRelatedField(many=True, queryset=FoodCategory.objects.all())
    locations = serializers.PrimaryKeyRelatedField(many=True, queryset=Location.objects.filter(is_active=True))
    temp_password = serializers.CharField(read_only=True)

    class Meta:
        model = Supplier
        fields = ('id', 'business_name', 'user', 'contact_number', 'address', 'locations', 'categories', 'temp_password')

    def validate_user(self, value):
        # Validate email uniqueness only for new users or email changes
        email = value.get('email')
        instance = getattr(self, 'instance', None)
        
        if email:
            # Check if this is an update and the email hasn't changed
            if instance and instance.user.email == email:
                return value
            
            # Check if email exists for other users
            existing_user = User.objects.filter(email=email).exclude(
                id=instance.user.id if instance else None
            ).exists()
            
            if existing_user:
                raise serializers.ValidationError(
                    {"email": "A user with this email already exists."}
                )
        
        return value

    def validate(self, data):
        # Validate required fields
        if not data.get('categories'):
            raise serializers.ValidationError({"categories": "At least one category must be selected."})
        if not data.get('locations'):
            raise serializers.ValidationError({"locations": "At least one location must be selected."})
        return data

    def generate_password(self):
        chars = string.ascii_letters + string.digits + '@#$%^&*'
        return ''.join(random.choice(chars) for _ in range(12))

    def create(self, validated_data):
        try:
            print("Creating supplier with data:", validated_data)
            
            user_data = validated_data.pop('user')
            categories = validated_data.pop('categories')
            locations = validated_data.pop('locations')
            
            # Generate username from email
            email = user_data['email']
            username = email.split('@')[0]
            base_username = username
            counter = 1
            
            # Ensure unique username
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1
            
            # Generate password
            password = self.generate_password()
            print(f"Generated password for {email}: {password}")
            
            # Create user
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=user_data['first_name'],
                last_name=user_data['last_name']
            )
            print(f"Created user: {user}")
            
            try:
                # Create supplier
                supplier = Supplier.objects.create(
                    user=user,
                    business_name=validated_data['business_name'],
                    contact_number=validated_data['contact_number'],
                    address=validated_data['address']
                )
                print(f"Created supplier: {supplier}")
                
                # Add categories and locations
                supplier.categories.set(categories)
                supplier.locations.set(locations)
                print(f"Added categories: {categories}")
                print(f"Added locations: {locations}")
                
                # Store temporary password for email
                supplier.temp_password = password
                
                return supplier
                
            except Exception as e:
                # If supplier creation fails, delete the user
                print(f"Error creating supplier: {e}")
                user.delete()
                raise
                
        except Exception as e:
            print(f"Error in create method: {e}")
            raise serializers.ValidationError(str(e))

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', {})
        categories = validated_data.pop('categories', None)
        locations = validated_data.pop('locations', None)
        
        # Update user details
        if user_data:
            user = instance.user
            for attr, value in user_data.items():
                setattr(user, attr, value)
            user.save()
        
        # Update supplier details
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update categories if provided
        if categories is not None:
            instance.categories.set(categories)
            
        # Update locations if provided
        if locations is not None:
            instance.locations.set(locations)
        
        return instance

class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    supplier_name = serializers.CharField(source='supplier.business_name', read_only=True)
    
    class Meta:
        model = Product
        fields = ['id', 'name', 'category', 'category_name', 'supplier', 'supplier_name', 
                 'description', 'price', 'stock', 'image', 'is_approved', 'threshold', 
                 'is_active', 'created_at']
        read_only_fields = ('is_approved', 'supplier')

    def create(self, validated_data):
        request = self.context.get('request')
        if request and hasattr(request.user, 'sellerprofile'):
            validated_data['supplier'] = request.user.sellerprofile.supplier
            validated_data['is_approved'] = False  # New products need approval
            return super().create(validated_data)
        raise serializers.ValidationError("Invalid supplier")

class RestockRequestSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    supplier_name = serializers.CharField(source='product.supplier.business_name', read_only=True)

    class Meta:
        model = RestockRequest
        fields = '__all__'
        read_only_fields = ('status', 'completed_at')
