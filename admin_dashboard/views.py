from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from django.db.models import F, Count, Q
from django.conf import settings
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
import random
import string
import logging
from django.core.paginator import Paginator
from django.core.exceptions import PermissionDenied
from django.core.mail import send_mail
from django.utils import timezone
from django.db import models

from .models import FoodCategory, Location, Supplier, Product, RestockRequest
from .forms import SupplierAdminForm
from .serializers import (
    FoodCategorySerializer, LocationSerializer, 
    SupplierSerializer, ProductSerializer, 
    RestockRequestSerializer
)
from .utils import send_supplier_welcome_email
from seller.models import SellerNotification

# Set up logging
logger = logging.getLogger(__name__)

def generate_random_password(length=10):
    characters = string.ascii_letters + string.digits + "!@#$%^&*()"
    return ''.join(random.choice(characters) for _ in range(length))

@login_required(login_url='admin_dashboard:admin_login')
@staff_member_required(login_url='admin_dashboard:admin_login')
def add_supplier(request):
    if request.method == 'POST':
        form = SupplierAdminForm(request.POST)
        logger.info("Form data received: %s", request.POST)
        
        if form.is_valid():
            logger.info("Form is valid, creating supplier...")
            try:
                with transaction.atomic():
                    # Generate username from business name
                    username = form.cleaned_data['business_name'].lower().replace(' ', '')
                    base_username = username
                    counter = 1
                    while User.objects.filter(username=username).exists():
                        username = f"{base_username}{counter}"
                        counter += 1
                    
                    # Generate a secure password
                    password = generate_random_password()
                    
                    # Create user account
                    user = User.objects.create_user(
                        username=username,
                        password=password,
                        email=form.cleaned_data['email'],
                        first_name=form.cleaned_data['first_name'],
                        last_name=form.cleaned_data['last_name']
                    )
                    logger.info("Created user: %s", user.username)
                    
                    # Create supplier profile
                    supplier = Supplier.objects.create(
                        user=user,
                        business_name=form.cleaned_data['business_name'],
                        contact_number=form.cleaned_data['contact_number'],
                        address=form.cleaned_data['address']
                    )
                    logger.info("Created supplier: %s", supplier.business_name)
                    
                    # Set locations and categories
                    supplier.locations.set(form.cleaned_data['locations'])
                    supplier.categories.set(form.cleaned_data['categories'])
                    logger.info("Set locations and categories")
                    
                    # Send welcome email
                    try:
                        send_supplier_welcome_email(supplier, username, password)
                        logger.info("Welcome email sent to %s", user.email)
                        messages.success(
                            request,
                            f'Supplier "{supplier.business_name}" has been added successfully. '
                            'A welcome email has been sent with login credentials.'
                        )
                    except Exception as e:
                        logger.error("Failed to send welcome email to %s: %s", user.email, str(e))
                        messages.warning(
                            request,
                            "Supplier account created successfully, but failed to send welcome email. "
                            "Please ensure the supplier has the following credentials:\n"
                            f"Username: {username}\nPassword: {password}"
                        )
                    
                    return redirect('admin_dashboard:suppliers_list')
            
            except Exception as e:
                logger.error("Error creating supplier: %s", str(e))
                messages.error(request, f'Error creating supplier: {str(e)}')
        else:
            logger.error("Form errors: %s", form.errors)
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    
    return render(request, 'admin_dashboard/supplier_form.html', {
        'form': SupplierAdminForm(),
        'title': 'Add New Supplier',
        'section': 'suppliers'
    })

@login_required(login_url='admin_dashboard:admin_login')
@staff_member_required(login_url='admin_dashboard:admin_login')
def edit_supplier(request, supplier_id):
    supplier = get_object_or_404(Supplier, id=supplier_id)
    if request.method == 'POST':
        form = SupplierAdminForm(request.POST, instance=supplier)
        if form.is_valid():
            supplier = form.save()
            messages.success(request, f'Supplier "{supplier.business_name}" has been updated successfully.')
            return redirect('admin_dashboard:suppliers_list')
    else:
        form = SupplierAdminForm(instance=supplier)
    
    return render(request, 'admin_dashboard/supplier_form.html', {
        'form': form,
        'title': 'Edit Supplier',
        'section': 'suppliers'
    })

@login_required(login_url='admin_dashboard:admin_login')
@staff_member_required(login_url='admin_dashboard:admin_login')
def delete_supplier(request, supplier_id):
    supplier = get_object_or_404(Supplier, id=supplier_id)
    if request.method == 'POST':
        supplier.delete()
        messages.success(request, f'Supplier "{supplier.business_name}" has been deleted successfully.')
        return redirect('admin_dashboard:suppliers_list')
    return render(request, 'admin_dashboard/delete_supplier.html', {'supplier': supplier})

@login_required(login_url='admin_dashboard:admin_login')
@staff_member_required(login_url='admin_dashboard:admin_login')
def suppliers_list(request):
    suppliers = Supplier.objects.all()
    return render(request, 'admin_dashboard/suppliers_list.html', {
        'suppliers': suppliers,
        'section': 'suppliers'
    })

def admin_login(request):
    # If user is already logged in and is staff, redirect to admin dashboard
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('admin_dashboard:admin_dashboard')
        
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None and user.is_staff:
            login(request, user)
            messages.success(request, f'Welcome back, {user.get_full_name() or user.username}!')
            return redirect('admin_dashboard:admin_dashboard')
        else:
            messages.error(request, 'Invalid credentials or insufficient permissions')
    
    return render(request, 'admin_dashboard/login.html')

def admin_logout(request):
    if request.user.is_authenticated:
        messages.success(request, 'You have been successfully logged out.')
        logout(request)
    return redirect('admin_dashboard:admin_login')

@login_required(login_url='admin_dashboard:admin_login')
@staff_member_required(login_url='admin_dashboard:admin_login')
def admin_dashboard(request):
    try:
        # Get counts
        total_categories = FoodCategory.objects.count()
        total_locations = Location.objects.count()
        total_suppliers = Supplier.objects.count()
        total_products = Product.objects.count()
        
        # Get recent products
        recent_products = Product.objects.select_related('supplier', 'category').order_by('-created_at')[:5]
        
        # Get top categories by product count
        top_categories = FoodCategory.objects.annotate(
            product_count=Count('products')  # Using correct related_name from model
        ).order_by('-product_count')[:5]
        
        # Get top suppliers by product count
        top_suppliers = Supplier.objects.annotate(
            product_count=Count('products')  # Using correct related_name from model
        ).order_by('-product_count')[:5]
        
        # Get products needing restock
        low_stock_products = Product.objects.filter(
            stock__lte=F('threshold'),  # Using correct field names from model
            is_active=True
        ).select_related('supplier')[:5]
        
        context = {
            'total_categories': total_categories,
            'total_locations': total_locations,
            'total_suppliers': total_suppliers,
            'total_products': total_products,
            'recent_products': recent_products,
            'top_categories': top_categories,
            'top_suppliers': top_suppliers,
            'low_stock_products': low_stock_products,
            'section': 'dashboard'
        }
        
        return render(request, 'admin_dashboard/dashboard.html', context)
    except Exception as e:
        print(f"Error in admin_dashboard: {str(e)}")
        messages.error(request, "An error occurred while loading the dashboard.")
        return render(request, 'admin_dashboard/dashboard.html', {
            'section': 'dashboard'
        })

@login_required(login_url='admin_dashboard:admin_login')
@staff_member_required(login_url='admin_dashboard:admin_login')
def categories_list(request):
    categories = FoodCategory.objects.annotate(
        products_count=Count('product'),
        suppliers_count=Count('suppliers')
    )
    return render(request, 'admin_dashboard/categories.html', {
        'categories': categories,
        'active_section': 'categories'
    })

@login_required(login_url='admin_dashboard:admin_login')
@staff_member_required(login_url='admin_dashboard:admin_login')
def add_category(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        image = request.FILES.get('image')
        
        category = FoodCategory.objects.create(
            name=name,
            description=description,
            image=image
        )
        
        messages.success(request, 'Category added successfully!')
        return redirect('admin_dashboard:categories_list')
    return render(request, 'admin_dashboard/add_category.html')

@login_required(login_url='admin_dashboard:admin_login')
@staff_member_required(login_url='admin_dashboard:admin_login')
def locations_list(request):
    locations = Location.objects.annotate(customers_count=Count('customers'))
    return render(request, 'admin_dashboard/locations.html', {
        'locations': locations,
        'active_section': 'locations'
    })

@login_required(login_url='admin_dashboard:admin_login')
@staff_member_required(login_url='admin_dashboard:admin_login')
def add_location(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        city = request.POST.get('city')
        state = request.POST.get('state')
        Location.objects.create(name=name, city=city, state=state)
        messages.success(request, 'Location added successfully!')
        return redirect('admin_dashboard:locations_list')
    return render(request, 'admin_dashboard/add_location.html')

@login_required(login_url='admin_dashboard:admin_login')
@staff_member_required(login_url='admin_dashboard:admin_login')
def products_list(request):
    # Get all products with related fields
    products = Product.objects.select_related('supplier', 'category')
    
    # Get counts
    approved_count = products.filter(status='approved').count()
    featured_count = products.filter(is_featured=True).count()
    pending_count = products.filter(status='pending').count()
    
    # Handle pagination
    paginator = Paginator(products, 12)  # Show 12 products per page
    page = request.GET.get('page')
    products = paginator.get_page(page)
    
    context = {
        'products': products,
        'approved_count': approved_count,
        'featured_count': featured_count,
        'pending_count': pending_count,
        'section': 'products'
    }
    
    return render(request, 'admin_dashboard/products.html', context)

@login_required(login_url='admin_dashboard:admin_login')
@staff_member_required(login_url='admin_dashboard:admin_login')
def approve_product(request, product_id):
    if request.method == 'POST':
        try:
            product = get_object_or_404(Product, id=product_id)
            product.status = 'approved'
            product.save()
            
            # Create notification for supplier
            SellerNotification.objects.create(
                seller=product.supplier.sellerprofile,  # Changed from supplier to seller
                type='product_approval',  # Changed from notification_type to type
                title='Product Approved',
                message=f'Your product "{product.name}" has been approved by the admin.',
                related_product=product  # Added related_product
            )
            
            return JsonResponse({
                'status': 'success',
                'message': 'Product approved successfully'
            })
        except Exception as e:
            logger.error(f"Error approving product {product_id}: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)
            
    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method'
    }, status=405)

@login_required(login_url='admin_dashboard:admin_login')
@staff_member_required(login_url='admin_dashboard:admin_login')
def reject_product(request, product_id):
    if request.method == 'POST':
        try:
            product = get_object_or_404(Product, id=product_id)
            product.status = 'rejected'
            product.save()
            
            # Create notification for supplier
            SellerNotification.objects.create(
                seller=product.supplier.sellerprofile,  # Changed from supplier to seller
                type='product_approval',  # Changed from notification_type to type
                title='Product Rejected',
                message=f'Your product "{product.name}" has been rejected by the admin.',
                related_product=product  # Added related_product
            )
            
            return JsonResponse({
                'status': 'success',
                'message': 'Product rejected successfully'
            })
        except Exception as e:
            logger.error(f"Error rejecting product {product_id}: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)
            
    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method'
    }, status=405)

@login_required(login_url='admin_dashboard:admin_login')
@staff_member_required(login_url='admin_dashboard:admin_login')
def toggle_product_status(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    
    if request.method == 'POST':
        is_active = request.POST.get('is_active') == 'true'
        product.is_active = is_active
        product.save()
        
        status_text = "activated" if is_active else "deactivated"
        messages.success(request, f'Product "{product.name}" has been {status_text}.')
        
    return redirect('admin_dashboard:products_list')


@login_required(login_url='admin_dashboard:admin_login')
@staff_member_required(login_url='admin_dashboard:admin_login')
def toggle_featured(request, product_id):
    if request.method == 'POST':
        try:
            product = get_object_or_404(Product, id=product_id)
            product.is_featured = not product.is_featured
            product.save()
            
            status = 'featured' if product.is_featured else 'unfeatured'
            message = f'Product has been {status} successfully'
            
            return JsonResponse({
                'status': 'success',
                'message': message,
                'is_featured': product.is_featured
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=400)
    
    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method'
    }, status=405)

@login_required(login_url='admin_dashboard:admin_login')
@staff_member_required(login_url='admin_dashboard:admin_login')
def bulk_feature_products(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'})
    
    try:
        data = json.loads(request.body)
        product_ids = data.get('product_ids', [])
        featured = data.get('featured', False)
        
        # Update products
        Product.objects.filter(id__in=product_ids).update(is_featured=featured)
        
        return JsonResponse({
            'status': 'success',
            'message': f'Successfully {"marked" if featured else "removed"} {len(product_ids)} products {"as featured" if featured else "from featured"}'
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

@login_required(login_url='admin_dashboard:admin_login')
@staff_member_required(login_url='admin_dashboard:admin_login')
def restock_requests(request):
    """View to manage restock requests and show low stock products"""
    if not request.user.is_superuser:
        raise PermissionDenied
    
    # Get filters
    status = request.GET.get('status')
    supplier_id = request.GET.get('supplier')
    
    # Get low stock products (where stock is less than threshold)
    low_stock_products = Product.objects.filter(
        stock__lt=F('threshold')
    ).select_related('supplier').order_by('stock')
    
    # Base queryset with related fields
    restock_requests = RestockRequest.objects.select_related(
        'product', 
        'product__supplier'
    ).order_by('-requested_at')
    
    # Apply filters
    if status:
        restock_requests = restock_requests.filter(status=status)
    if supplier_id:
        restock_requests = restock_requests.filter(product__supplier_id=supplier_id)
    
    # Get all suppliers for filter dropdown
    suppliers = Supplier.objects.filter(is_active=True).order_by('business_name')
    
    # Get count of pending requests
    pending_count = RestockRequest.objects.filter(status='pending').count()
    
    # Get existing restock request product IDs to avoid duplicates
    existing_request_products = RestockRequest.objects.filter(
        status__in=['pending', 'approved']
    ).values_list('product_id', flat=True)
    
    # Filter out products that already have pending or approved requests
    low_stock_products = low_stock_products.exclude(id__in=existing_request_products)
    
    # Paginate results
    paginator = Paginator(restock_requests, 10)
    page = request.GET.get('page')
    restock_requests = paginator.get_page(page)
    
    context = {
        'restock_requests': restock_requests,
        'low_stock_products': low_stock_products,
        'suppliers': suppliers,
        'pending_count': pending_count,
        'active_section': 'restock_requests'
    }
    return render(request, 'admin_dashboard/restock_requests.html', context)

@login_required(login_url='admin_dashboard:admin_login')
@staff_member_required(login_url='admin_dashboard:admin_login')
def create_restock_request(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.method == 'POST':
        quantity = int(request.POST.get('quantity', 0))
        restock_request = RestockRequest.objects.create(
            product=product,
            quantity=quantity,
            status='pending'
        )
        
        # Notify supplier
        send_mail(
            'Restock Request',
            f'Please restock {product.name}. Quantity needed: {quantity}',
            'from@example.com',
            [product.supplier.user.email],
            fail_silently=True,
        )
        
        messages.success(request, 'Restock request sent successfully!')
        return redirect('admin_dashboard:products_list')
    return render(request, 'admin_dashboard/create_restock_request.html', {'product': product})

@login_required(login_url='admin_dashboard:admin_login')
@staff_member_required(login_url='admin_dashboard:admin_login')
def approve_restock(request, request_id):
    restock_request = get_object_or_404(RestockRequest, id=request_id)
    if request.method == 'POST':
        restock_request.status = 'approved'
        restock_request.save()
        
        # Update product stock
        product = restock_request.product
        product.stock += restock_request.quantity
        product.save()
        
        messages.success(request, 'Restock request approved successfully!')
        return redirect('admin_dashboard:restock_requests_list')
    return render(request, 'admin_dashboard/approve_restock.html', {'restock_request': restock_request})

# ViewSets for API
class FoodCategoryViewSet(viewsets.ModelViewSet):
    queryset = FoodCategory.objects.all()
    serializer_class = FoodCategorySerializer
    permission_classes = [IsAdminUser]

class LocationViewSet(viewsets.ModelViewSet):
    queryset = Location.objects.all()
    serializer_class = LocationSerializer
    permission_classes = [IsAdminUser]

class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    permission_classes = [IsAdminUser]

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsAdminUser]

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        product = self.get_object()
        product.is_approved = True
        product.save()
        return Response({'status': 'product approved'})

    @action(detail=True, methods=['post'])
    def toggle_status(self, request, pk=None):
        product = self.get_object()
        product.is_active = not product.is_active
        product.save()
        return Response({'status': 'product status updated'})

class RestockRequestViewSet(viewsets.ModelViewSet):
    queryset = RestockRequest.objects.all()
    serializer_class = RestockRequestSerializer
    permission_classes = [IsAdminUser]

    @action(detail=False, methods=['post'], url_path='create/(?P<product_id>[^/.]+)')
    def create_request(self, request, product_id=None):
        try:
            product = Product.objects.get(id=product_id)
            quantity = request.data.get('quantity')
            
            if not quantity or int(quantity) <= 0:
                return Response(
                    {'error': 'Invalid quantity'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            restock_request = RestockRequest.objects.create(
                product=product,
                quantity=quantity,
                status='pending'
            )

            # Create notification for supplier
            SellerNotification.objects.create(
                seller=product.supplier,
                title='New Restock Request',
                message=f'A restock request has been created for {product.name}. Quantity needed: {quantity}',
                notification_type='restock_request',
                reference_id=restock_request.id
            )

            # Send email to supplier
            try:
                send_mail(
                    'New Restock Request',
                    f'A restock request has been created for {product.name}.\n\n'
                    f'Details:\n'
                    f'- Product: {product.name}\n'
                    f'- Current Stock: {product.stock}\n'
                    f'- Requested Quantity: {quantity}\n\n'
                    f'Please log in to your seller dashboard to approve or reject this request.',
                    settings.DEFAULT_FROM_EMAIL,
                    [product.supplier.user.email],
                    fail_silently=True,
                )
            except Exception as e:
                logger.error(f"Failed to send email to supplier: {str(e)}")

            serializer = self.get_serializer(restock_request)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except Product.DoesNotExist:
            return Response(
                {'error': 'Product not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        restock_request = self.get_object()
        restock_request.status = 'approved'
        restock_request.save()
        return Response({'status': 'approved'})

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        restock_request = self.get_object()
        restock_request.status = 'completed'
        restock_request.save()
        
        # Update product stock
        product = restock_request.product
        product.stock += restock_request.quantity
        product.save()
        
        return Response({'status': 'completed'})
