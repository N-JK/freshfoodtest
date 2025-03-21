from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from rest_framework.decorators import action
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.db.models import Count, Sum, F, Q
from django.db.models.functions import TruncMonth
from django.utils import timezone
from .serializers import (
    SellerProfileSerializer, SellerNotificationSerializer,
    SellerAnalyticsSerializer, SellerProductSerializer,
    SellerRestockRequestSerializer
)
from .models import SellerProfile, SellerNotification, SellerAnalytics, DeliveryBoy
from admin_dashboard.models import Product, RestockRequest
from buyer.models import Order, OrderItem
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.conf import settings
import razorpay

class SellerPermission:
    def has_permission(self, request, view):
        return hasattr(request.user, 'sellerprofile')

class SellerProfileViewSet(viewsets.ModelViewSet):
    serializer_class = SellerProfileSerializer
    permission_classes = [IsAuthenticated, SellerPermission]

    def get_queryset(self):
        return SellerProfile.objects.filter(user=self.request.user)

    @action(detail=False, methods=['post'])
    def change_password(self, request):
        user = request.user
        current_password = request.data.get('current_password')
        new_password = request.data.get('new_password')
        confirm_password = request.data.get('confirm_password')
        
        if not user.check_password(current_password):
            return Response({
                'message': 'Current password is incorrect'
            }, status=status.HTTP_400_BAD_REQUEST)
            
        if new_password != confirm_password:
            return Response({
                'message': 'New passwords do not match'
            }, status=status.HTTP_400_BAD_REQUEST)
            
        if len(new_password) < 8:
            return Response({
                'message': 'Password must be at least 8 characters long'
            }, status=status.HTTP_400_BAD_REQUEST)
            
        user.set_password(new_password)
        user.save()
        
        return Response({
            'message': 'Password changed successfully'
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def dashboard_stats(self, request):
        seller = request.user.sellerprofile
        today = timezone.now().date()
        
        # Get analytics for today
        analytics, created = SellerAnalytics.objects.get_or_create(
            seller=seller,
            date=today,
            defaults={
                'total_products': seller.supplier.products.count(),
                'active_products': seller.supplier.products.filter(status='approved').count(),
                'pending_approvals': seller.supplier.products.filter(status='pending').count(),
                'low_stock_items': seller.supplier.products.filter(stock__lte=F('threshold')).count(),
            }
        )
        
        return Response({
            'analytics': SellerAnalyticsSerializer(analytics).data,
            'unread_notifications': seller.notifications.filter(is_read=False).count()
        })

class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = SellerProductSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if not hasattr(self.request.user, 'sellerprofile'):
            raise PermissionDenied("Seller profile not found")
        return Product.objects.filter(supplier=self.request.user.sellerprofile.supplier)

    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return Response({
                'status': 'success',
                'data': {
                    'id': instance.id,
                    'name': instance.name,
                    'category': instance.category.id,
                    'description': instance.description,
                    'price': str(instance.price),
                    'stock': instance.stock,
                    'threshold': instance.threshold,
                    'image': instance.image.url if instance.image else None
                }
            })
        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    def perform_create(self, serializer):
        if not hasattr(self.request.user, 'sellerprofile'):
            raise PermissionDenied("Seller profile not found")
        
        # Ensure supplier is active
        supplier = self.request.user.sellerprofile.supplier
        if not supplier.is_active:
            raise PermissionDenied("Your supplier account is not active")
        
        # Set default values
        serializer.save(
            supplier=supplier,
            status='pending'
        )

    def create(self, request, *args, **kwargs):
        try:
            # Validate the data
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            # Create the product
            self.perform_create(serializer)
            
            # Return success response
            return Response({
                'status': 'success',
                'message': 'Product created successfully and is pending approval',
                'data': serializer.data
            }, status=status.HTTP_201_CREATED)
            
        except PermissionDenied as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_403_FORBIDDEN)
            
        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            
            # Print request data for debugging
            print("Received data:", request.data)
            
            # Convert numeric fields to appropriate types
            data = request.data.copy()
            try:
                if 'price' in data:
                    data['price'] = float(data['price'])
                if 'stock' in data:
                    data['stock'] = int(data['stock'])
                if 'threshold' in data:
                    data['threshold'] = int(data['threshold'])
            except (ValueError, TypeError) as e:
                print("Type conversion error:", str(e))
                return Response({
                    'status': 'error',
                    'message': 'Invalid numeric values provided'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Print data after conversion
            print("Data after conversion:", data)

            serializer = self.get_serializer(instance, data=data, partial=True)
            if not serializer.is_valid():
                print("Validation errors:", serializer.errors)
                return Response({
                    'status': 'error',
                    'message': 'Validation error',
                    'errors': serializer.errors,
                    'received_data': data
                }, status=status.HTTP_400_BAD_REQUEST)

            # Print validated data
            print("Validated data:", serializer.validated_data)

            # Perform the update
            self.perform_update(serializer)

            return Response({
                'status': 'success',
                'message': 'Product updated successfully',
                'data': serializer.data
            })
        except Exception as e:
            print("Error:", str(e))
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    def perform_update(self, serializer):
        try:
            if not self.request.user.is_staff:  # If not admin
                # Instead of modifying validated_data, pass clean data to save
                serializer.save(
                    status=serializer.instance.status,  # Keep existing status
                    supplier=serializer.instance.supplier  # Keep existing supplier
                )
            else:
                serializer.save()
        except Exception as e:
            print("Save error:", str(e))  # Debug print
            raise e

class RestockRequestViewSet(viewsets.ModelViewSet):
    serializer_class = SellerRestockRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if not hasattr(self.request.user, 'sellerprofile'):
            raise PermissionDenied("Seller profile not found")
        return RestockRequest.objects.filter(
            product__supplier=self.request.user.sellerprofile.supplier
        ).order_by('-requested_at')

    def perform_create(self, serializer):
        if not hasattr(self.request.user, 'sellerprofile'):
            raise PermissionDenied("Seller profile not found")
        serializer.save()

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        restock_request = self.get_object()
        if restock_request.status != 'pending':
            return Response(
                {"error": "Can only approve pending restock requests"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            restock_request.status = 'approved'
            restock_request.save()
            return Response({"status": "success"})
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        restock_request = self.get_object()
        if restock_request.status != 'pending':
            return Response(
                {"error": "Can only reject pending restock requests"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            restock_request.status = 'rejected'
            restock_request.save()
            return Response({"status": "success"})
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def complete_restock(self, request, pk=None):
        restock_request = self.get_object()
        if restock_request.status != 'approved':
            return Response(
                {"error": "Can only complete approved restock requests"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            restock_request.complete_restock()
            return Response({"status": "success"})
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = SellerNotificationSerializer
    permission_classes = [IsAuthenticated, SellerPermission]

    def get_queryset(self):
        return SellerNotification.objects.filter(seller=self.request.user.sellerprofile)

    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        return Response({'status': 'notification marked as read'})

    @action(detail=False, methods=['post'])
    def mark_all_as_read(self, request):
        self.get_queryset().update(is_read=True)
        return Response({'status': 'all notifications marked as read'})

def send_welcome_email(user, seller_profile):
    try:
        subject = 'Welcome to Fresh Food - Supplier Account Created'
        message = f'''
        Dear {user.get_full_name()},

        Welcome to Fresh Food! Your supplier account has been created successfully.

        Here are your account details:
        - Email: {user.email}
        - Business Name: {seller_profile.business_name}

        You can now log in to your supplier dashboard to:
        - Add your products
        - Manage inventory
        - Track orders
        - View analytics

        If you have any questions, please don't hesitate to contact our support team.

        Best regards,
        Fresh Food Team
        '''
        
        from django.core.mail import send_mail
        from django.conf import settings
        
        send_mail(
            subject,
            message,
            settings.EMAIL_HOST_USER,
            [user.email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Failed to send welcome email: {str(e)}")
        return False

def seller_login(request):
    """Handle seller login with optimized performance."""
    # Redirect if already logged in
    if request.user.is_authenticated and hasattr(request.user, 'sellerprofile'):
        return redirect('seller:dashboard')
        
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        # Use authenticate directly without try-except for better performance
        authenticated_user = authenticate(request, username=username, password=password)
        
        if authenticated_user is not None and hasattr(authenticated_user, 'supplier'):
            from seller.models import SellerProfile
            # Use get_or_create to avoid race conditions and reduce queries
            seller_profile, created = SellerProfile.objects.get_or_create(
                user=authenticated_user,
                defaults={
                    'supplier': authenticated_user.supplier,
                    'phone_number': authenticated_user.supplier.contact_number,
                    'address': authenticated_user.supplier.address
                }
            )
            login(request, authenticated_user)
            return redirect('seller:dashboard')
        else:
            messages.error(request, 'Invalid username or password.')
    
    # Render login page without any additional context
    return render(request, 'seller/login.html')

@login_required(login_url='seller:login')
def seller_dashboard(request):
    if not hasattr(request.user, 'sellerprofile'):
        raise PermissionDenied
    
    seller = request.user.sellerprofile
    supplier = seller.supplier
    
    # Use annotate to get all counts in a single query
    from django.db.models import Count, Q
    product_stats = supplier.products.aggregate(
        total_products=Count('id'),
        active_products=Count('id', filter=Q(status='approved')),
        pending_approvals=Count('id', filter=Q(status='pending')),
        low_stock_items=Count('id', filter=Q(stock__lte=F('threshold')))
    )
    
    # Prefetch related data for notifications to avoid N+1 queries
    notifications = (SellerNotification.objects
                    .filter(seller=seller)
                    .select_related('seller', 'seller__user')
                    .order_by('-created_at')[:5])
    
    context = {
        'total_products': product_stats['total_products'],
        'active_products': product_stats['active_products'],
        'pending_approvals': product_stats['pending_approvals'],
        'low_stock_items': product_stats['low_stock_items'],
        'notifications': notifications,
        'active_section': 'dashboard'
    }
    
    return render(request, 'seller/dashboard.html', context)

@login_required(login_url='seller:login')
def seller_products(request):
    if not hasattr(request.user, 'sellerprofile'):
        raise PermissionDenied
    
    supplier = request.user.sellerprofile.supplier
    
    # Get all products for this supplier
    products = supplier.products.all().order_by('-created_at')
    
    # Get counts for different product states
    pending_count = products.filter(status='pending').count()
    approved_count = products.filter(status='approved').count()
    low_stock_count = products.filter(
        status='approved',
        stock__lte=F('threshold')
    ).count()
    
    # Get supplier's assigned categories
    categories = supplier.categories.all()
    
    return render(request, 'seller/products.html', {
        'products': products,
        'categories': categories,
        'active_section': 'products',
        'pending_count': pending_count,
        'approved_count': approved_count,
        'low_stock_count': low_stock_count
    })

@login_required(login_url='seller:login')
def seller_restock_requests(request):
    if not hasattr(request.user, 'sellerprofile'):
        raise PermissionDenied
    
    supplier = request.user.sellerprofile.supplier
    restock_requests = RestockRequest.objects.filter(
        product__supplier=supplier
    ).select_related('product').order_by('-requested_at')
    
    return render(request, 'seller/restock_requests.html', {
        'restock_requests': restock_requests,
        'active_section': 'restock_requests'
    })

@login_required(login_url='seller:login')
def seller_orders(request):
    if not hasattr(request.user, 'sellerprofile'):
        raise PermissionDenied
        
    seller = request.user.sellerprofile
    supplier = seller.supplier
    
    # Get all products where this seller is the supplier
    supplier_products = Product.objects.filter(supplier=supplier)
    
    # Get all orders that contain these products
    orders = Order.objects.filter(
        order_items__product__in=supplier_products
    ).distinct().order_by('-created_at')
    
    # Get all active delivery boys
    delivery_boys = DeliveryBoy.objects.filter(seller=seller, is_active=True)
    
    context = {
        'orders': orders,
        'delivery_boys': delivery_boys,
        'active_section': 'orders'
    }
    return render(request, 'seller/orders.html', context)

@login_required(login_url='seller:login')
def order_detail(request, order_id):
    """
    View for displaying detailed information about a specific order
    """
    # Get the seller's profile
    seller = request.user.sellerprofile
    
    # Get the order and verify it belongs to this seller
    order = get_object_or_404(Order, id=order_id, order_items__product__supplier=seller.supplier)
    
    context = {
        'order': order,
        'order_items': order.order_items.filter(product__supplier=seller.supplier),
        'delivery_boys': DeliveryBoy.objects.filter(
            seller=seller,
            is_active=True,
            status='available'
        )
    }
    
    return render(request, 'seller/order_detail.html', context)

@login_required(login_url='seller:login')
def update_order_status(request, order_id):
    if not request.method == 'POST':
        return HttpResponseNotAllowed(['POST'])
        
    if not hasattr(request.user, 'sellerprofile'):
        raise PermissionDenied
        
    order = get_object_or_404(Order, id=order_id)
    seller = request.user.sellerprofile
    
    # Verify that this order contains products from this seller
    seller_products = Product.objects.filter(supplier=seller.supplier)
    if not order.order_items.filter(product__in=seller_products).exists():
        raise PermissionDenied
    
    status = request.POST.get('status')
    if not status:
        messages.error(request, 'Status is required')
        return redirect('seller:orders')
        
    if status == 'confirmed':
        order.order_status = 'confirmed'
        messages.success(request, 'Order has been confirmed')
        
    elif status == 'out_for_delivery':
        delivery_boy_id = request.POST.get('delivery_boy')
        if not delivery_boy_id:
            messages.error(request, 'Please select a delivery boy')
            return redirect('seller:order_detail', order_id=order.id)
            
        try:
            delivery_boy = DeliveryBoy.objects.get(id=delivery_boy_id, seller=seller, is_active=True)
            if delivery_boy.status != 'available':
                messages.error(request, 'Selected delivery boy is not available')
                return redirect('seller:order_detail', order_id=order.id)
                
            order.delivery_boy = delivery_boy
            order.order_status = 'out_for_delivery'
            
            # Update delivery boy status
            delivery_boy.status = 'on_delivery'
            delivery_boy.save()
            
            messages.success(request, f'Order assigned to {delivery_boy.name} and marked as out for delivery')
            
        except DeliveryBoy.DoesNotExist:
            messages.error(request, 'Invalid delivery boy selected')
            return redirect('seller:order_detail', order_id=order.id)
            
    elif status == 'delivered':
        # Make sure order has a delivery boy assigned
        if not order.delivery_boy:
            messages.error(request, 'Cannot mark as delivered: No delivery boy assigned')
            return redirect('seller:order_detail', order_id=order.id)
            
        # Update order status
        order.order_status = 'delivered'
        
        # Update delivery boy status back to available
        delivery_boy = order.delivery_boy
        delivery_boy.status = 'available'
        delivery_boy.save()
        
        messages.success(request, 'Order has been marked as delivered')
    
    order.save()
    return redirect('seller:order_detail', order_id=order.id)

@login_required(login_url='seller:login')
def seller_profile(request):
    if not hasattr(request.user, 'sellerprofile'):
        raise PermissionDenied
    
    seller = request.user.sellerprofile
    
    return render(request, 'seller/profile.html', {
        'seller': seller,
        'active_section': 'profile'
    })

def seller_logout(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('seller:login')

import random
import string
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.models import User, Group

def generate_password():
    """Generate a random password"""
    characters = string.ascii_letters + string.digits + string.punctuation
    return ''.join(random.choice(characters) for i in range(12))

def send_credentials_email(email, username, password):
    """Send login credentials via email"""
    subject = 'Your Home Fresh Delivery Boy Account Credentials'
    message = f'''Hello,

Your delivery boy account has been created for Home Fresh. Here are your login credentials:

Username: {username}
Password: {password}

Please login at: {settings.SITE_URL}/delivery/login/
Please change your password after first login for security.

Best regards,
Home Fresh Team'''
    
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [email],
        fail_silently=False,
    )

@login_required
def delivery_boys(request):
    """View to list and manage delivery boys"""
    seller = request.user.sellerprofile
    delivery_boys = DeliveryBoy.objects.filter(seller=seller)
    
    # Get seller's assigned locations from admin
    available_locations = seller.supplier.locations.filter(is_active=True)
    
    # Get delivery history for each delivery boy
    for boy in delivery_boys:
        boy.total_deliveries = Order.objects.filter(
            delivery_boy=boy, 
            order_status='delivered'
        ).count()
        
        boy.recent_deliveries = Order.objects.filter(
            delivery_boy=boy,
            order_status='delivered'
        ).order_by('-updated_at')[:5]
        
        # For now, we'll consider orders delivered within expected time
        # This is a placeholder since we don't have expected delivery time
        boy.on_time_deliveries = boy.total_deliveries
        boy.on_time_percentage = 100 if boy.total_deliveries > 0 else 0
    
    context = {
        'delivery_boys': delivery_boys,
        'available_locations': available_locations
    }
    return render(request, 'seller/delivery_boys/list.html', context)

@login_required
def add_delivery_boy(request):
    """View to add a new delivery boy"""
    if request.method == 'POST':
        try:
            # Get seller's assigned locations
            seller = request.user.sellerprofile
            available_locations = seller.supplier.locations.filter(is_active=True)
            
            # Validate location
            location_id = request.POST.get('location')
            if not available_locations.filter(id=location_id).exists():
                messages.error(request, 'Invalid location selected')
                return redirect('seller:delivery_boys')
            
            email = request.POST.get('email')
            if not email:
                messages.error(request, 'Email is required for delivery boy account')
                return redirect('seller:delivery_boys')

            # Create user account
            username = f"delivery_{email.split('@')[0]}"
            password = generate_password()
            
            # Check if username exists and modify if needed
            base_username = username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}_{counter}"
                counter += 1
            
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password
            )
            
            # Add user to delivery boy group
            delivery_boy_group, _ = Group.objects.get_or_create(name='Delivery Boys')
            user.groups.add(delivery_boy_group)
            
            # Create delivery boy
            delivery_boy = DeliveryBoy.objects.create(
                seller=seller,
                name=request.POST.get('name'),
                phone=request.POST.get('phone'),
                email=email,
                address=request.POST.get('address'),
                id_proof=request.FILES.get('id_proof'),
                profile_photo=request.FILES.get('profile_photo'),
                vehicle_number=request.POST.get('vehicle_number'),
                vehicle_type=request.POST.get('vehicle_type'),
                assigned_location_id=location_id,
                user=user  # Link to user account
            )
            
            # Send credentials via email
            send_credentials_email(email, username, password)
            
            messages.success(request, f'Delivery boy {delivery_boy.name} added successfully. Login credentials have been sent to their email.')
            return redirect('seller:delivery_boys')
            
        except Exception as e:
            messages.error(request, f'Error adding delivery boy: {str(e)}')
            return redirect('seller:delivery_boys')
            
    # GET request - show form
    seller = request.user.sellerprofile
    available_locations = seller.supplier.locations.filter(is_active=True)
    
    context = {
        'available_locations': available_locations
    }
    return render(request, 'seller/delivery_boys/add.html', context)

@login_required
def edit_delivery_boy(request, id):
    """View to edit an existing delivery boy"""
    seller = request.user.sellerprofile
    delivery_boy = get_object_or_404(DeliveryBoy, id=id, seller=seller)
    
    if request.method == 'POST':
        try:
            # Validate location
            location_id = request.POST.get('location')
            if not seller.supplier.locations.filter(id=location_id, is_active=True).exists():
                messages.error(request, 'Invalid location selected')
                return redirect('seller:delivery_boys')
            
            # Update delivery boy
            delivery_boy.name = request.POST.get('name')
            delivery_boy.phone = request.POST.get('phone')
            delivery_boy.email = request.POST.get('email')
            delivery_boy.address = request.POST.get('address')
            delivery_boy.vehicle_number = request.POST.get('vehicle_number')
            delivery_boy.vehicle_type = request.POST.get('vehicle_type')
            delivery_boy.assigned_location_id = location_id
            delivery_boy.status = request.POST.get('status')
            
            # Update photos if provided
            if 'id_proof' in request.FILES:
                delivery_boy.id_proof = request.FILES['id_proof']
            if 'profile_photo' in request.FILES:
                delivery_boy.profile_photo = request.FILES['profile_photo']
            
            delivery_boy.save()
            messages.success(request, f'Delivery boy {delivery_boy.name} updated successfully')
            return redirect('seller:delivery_boys')
            
        except Exception as e:
            messages.error(request, f'Error updating delivery boy: {str(e)}')
            return redirect('seller:delivery_boys')
    
    # GET request - show form
    available_locations = seller.supplier.locations.filter(is_active=True)
    context = {
        'delivery_boy': delivery_boy,
        'available_locations': available_locations
    }
    return render(request, 'seller/delivery_boys/edit.html', context)

@login_required
def toggle_delivery_boy_status(request, id):
    """Toggle active status of delivery boy"""
    seller = request.user.sellerprofile
    delivery_boy = get_object_or_404(DeliveryBoy, id=id, seller=seller)
    
    delivery_boy.is_active = not delivery_boy.is_active
    delivery_boy.save()
    
    status = 'activated' if delivery_boy.is_active else 'deactivated'
    messages.success(request, f'Delivery boy {delivery_boy.name} {status} successfully')
    return redirect('seller:delivery_boys')

@login_required(login_url='seller:login')
def revenue_page(request):
    if not hasattr(request.user, 'sellerprofile'):
        raise PermissionDenied
        
    seller = request.user.sellerprofile
    supplier = seller.supplier
    
    # Get all products where this seller is the supplier
    supplier_products = Product.objects.filter(supplier=supplier)
    
    # Get all delivered orders with these products
    orders = Order.objects.filter(
        order_items__product__in=supplier_products,
        order_status='delivered'
    ).distinct()
    
    # Calculate total revenue from delivered orders
    total_revenue = OrderItem.objects.filter(
        order__in=orders,
        product__in=supplier_products
    ).aggregate(
        total=Sum(F('quantity') * F('price'))
    )['total'] or 0
    
    # Calculate monthly revenue (last 12 months)
    today = timezone.now()
    last_year = today - timezone.timedelta(days=365)
    
    monthly_revenue = OrderItem.objects.filter(
        order__in=orders,
        product__in=supplier_products,
        order__created_at__gte=last_year
    ).annotate(
        month=TruncMonth('order__created_at')
    ).values('month').annotate(
        revenue=Sum(F('quantity') * F('price'))
    ).order_by('month')
    
    # Calculate revenue by category
    category_revenue = OrderItem.objects.filter(
        order__in=orders,
        product__in=supplier_products
    ).values(
        'product__category__name'
    ).annotate(
        revenue=Sum(F('quantity') * F('price'))
    ).order_by('-revenue')
    
    # Get recent transactions
    recent_orders = orders.order_by('-created_at')[:10]
    
    # Calculate seller's revenue for each recent order
    for order in recent_orders:
        order.seller_revenue = OrderItem.objects.filter(
            order=order,
            product__in=supplier_products
        ).aggregate(
            total=Sum(F('quantity') * F('price'))
        )['total'] or 0
    
    context = {
        'active_section': 'revenue',
        'total_revenue': total_revenue,
        'monthly_revenue': list(monthly_revenue),
        'category_revenue': list(category_revenue),
        'recent_transactions': recent_orders,
    }
    
    return render(request, 'seller/revenue.html', context)

@login_required
def change_password(request):
    try:
        seller = request.user.sellerprofile
    except:
        return redirect('home')
        
    if request.method == 'POST':
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        if not request.user.check_password(current_password):
            messages.error(request, 'Current password is incorrect')
            return redirect('seller:change_password')
            
        if new_password != confirm_password:
            messages.error(request, 'New passwords do not match')
            return redirect('seller:change_password')
            
        if len(new_password) < 8:
            messages.error(request, 'Password must be at least 8 characters long')
            return redirect('seller:change_password')
            
        # Update password
        request.user.set_password(new_password)
        request.user.save()
        
        messages.success(request, 'Password changed successfully. Please login with your new password.')
        return redirect('seller:login')
        
    return render(request, 'seller/change_password.html')
