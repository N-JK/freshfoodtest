from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from seller.models import DeliveryBoy
from buyer.models import Order
from django.contrib.auth.forms import AuthenticationForm
from django.http import JsonResponse, HttpResponseNotAllowed
from django.db import transaction
from django.utils import timezone
from .forms import DeliveryBoyProfileForm, CustomPasswordChangeForm
import random
import json
from datetime import datetime, timedelta
from django.db.models import Count, Sum, F, Q
from django.contrib.auth.hashers import check_password

# Create your views here.

def delivery_login(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            try:
                delivery_boy = DeliveryBoy.objects.get(user=user, is_active=True)
                login(request, user)
                messages.success(request, f'Welcome back {delivery_boy.name}!')
                return redirect('delivery:dashboard')
            except DeliveryBoy.DoesNotExist:
                messages.error(request, 'Invalid delivery boy account')
    else:
        form = AuthenticationForm()
    return render(request, 'delivery/login.html', {'form': form})

@login_required(login_url='delivery:login')
def delivery_logout(request):
    logout(request)
    return redirect('delivery:login')

@login_required(login_url='delivery:login')
def dashboard(request):
    if not hasattr(request.user, 'deliveryboy'):
        raise PermissionDenied
        
    delivery_boy = request.user.deliveryboy
    
    # Get today's date range
    today = timezone.now().date()
    today_start = timezone.make_aware(datetime.combine(today, datetime.min.time()))
    today_end = timezone.make_aware(datetime.combine(today, datetime.max.time()))
    
    # Get active orders
    active_orders = Order.objects.filter(
        delivery_boy=delivery_boy,
        order_status__in=['out_for_delivery', 'assigned']
    ).select_related('user').order_by('-created_at')
    
    # Get completed orders for today
    completed_orders = Order.objects.filter(
        delivery_boy=delivery_boy,
        order_status='delivered',
        updated_at__range=(today_start, today_end)
    ).select_related('user').order_by('-updated_at')[:10]
    
    # Calculate today's metrics
    today_stats = Order.objects.filter(
        delivery_boy=delivery_boy,
        updated_at__range=(today_start, today_end),
        order_status='delivered'
    ).aggregate(
        today_deliveries=Count('id'),
        today_earnings=Sum('total_amount')
    )
    
    # Calculate performance metrics
    last_week = today - timedelta(days=7)
    performance_metrics = Order.objects.filter(
        delivery_boy=delivery_boy,
        created_at__gte=last_week
    ).aggregate(
        total_orders=Count('id'),
        on_time_deliveries=Count('id', filter=Q(order_status='delivered')),
        total_ratings=Count('id')
    )
    
    total_orders = performance_metrics['total_orders'] or 0
    on_time_deliveries = performance_metrics['on_time_deliveries'] or 0
    
    on_time_rate = (
        (on_time_deliveries / total_orders * 100)
        if total_orders > 0 else 0
    )
    
    context = {
        'delivery_boy': delivery_boy,
        'active_orders': active_orders,
        'completed_orders': completed_orders,
        'today_deliveries': today_stats['today_deliveries'] or 0,
        'today_earnings': today_stats['today_earnings'] or 0,
        'on_time_rate': round(on_time_rate, 1),
        'avg_rating': 4.8,  # Placeholder since rating system isn't implemented yet
        'acceptance_rate': 92,  # Placeholder - implement based on your business logic
        'active_section': 'dashboard'
    }
    
    return render(request, 'delivery/dashboard.html', context)

@login_required(login_url='delivery:login')
def profile(request):
    if not hasattr(request.user, 'deliveryboy'):
        raise PermissionDenied
        
    delivery_boy = request.user.deliveryboy
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'update_profile':
            profile_form = DeliveryBoyProfileForm(
                request.POST, 
                request.FILES, 
                instance=delivery_boy,
                user=request.user
            )
            password_form = CustomPasswordChangeForm(request.user)
            
            if profile_form.is_valid():
                with transaction.atomic():
                    # Update User model
                    user = request.user
                    user.username = profile_form.cleaned_data['username']
                    user.first_name = profile_form.cleaned_data['first_name']
                    user.last_name = profile_form.cleaned_data['last_name']
                    user.email = profile_form.cleaned_data['email']
                    user.save()
                    
                    # Update DeliveryBoy model
                    profile_form.save()
                    
                messages.success(request, 'Profile updated successfully!')
                return redirect('delivery:profile')
        
        elif action == 'change_password':
            password_form = CustomPasswordChangeForm(request.user, request.POST)
            profile_form = DeliveryBoyProfileForm(instance=delivery_boy, user=request.user)
            
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, 'Password changed successfully!')
                return redirect('delivery:profile')
    else:
        profile_form = DeliveryBoyProfileForm(instance=delivery_boy, user=request.user)
        password_form = CustomPasswordChangeForm(request.user)
    
    context = {
        'delivery_boy': delivery_boy,
        'profile_form': profile_form,
        'password_form': password_form,
        'active_section': 'profile'
    }
    return render(request, 'delivery/profile.html', context)

@login_required(login_url='delivery:login')
def edit_profile(request):
    delivery_boy = request.user.deliveryboy

    if request.method == 'POST':
        # Handle form submission
        delivery_boy.name = request.POST.get('name')
        delivery_boy.email = request.POST.get('email')
        delivery_boy.phone = request.POST.get('phone')
        delivery_boy.address = request.POST.get('address')
        delivery_boy.vehicle_type = request.POST.get('vehicle_type')
        delivery_boy.vehicle_number = request.POST.get('vehicle_number')

        # Handle profile photo upload
        if 'profile_photo' in request.FILES:
            delivery_boy.profile_photo = request.FILES['profile_photo']

        delivery_boy.save()
        messages.success(request, 'Profile updated successfully!')
        return redirect('delivery:profile')

    return render(request, 'delivery/edit_profile.html', {
        'delivery_boy': delivery_boy
    })

@login_required(login_url='delivery:login')
def orders(request):
    if not hasattr(request.user, 'deliveryboy'):
        raise PermissionDenied
        
    delivery_boy = request.user.deliveryboy
    active_orders = Order.objects.filter(
        delivery_boy=delivery_boy,
        order_status='out_for_delivery'
    ).order_by('-created_at')
    
    completed_orders = Order.objects.filter(
        delivery_boy=delivery_boy,
        order_status='delivered'
    ).order_by('-created_at')
    
    context = {
        'active_orders': active_orders,
        'completed_orders': completed_orders,
        'active_section': 'orders'
    }
    return render(request, 'delivery/orders.html', context)

@login_required(login_url='delivery:login')
def order_detail(request, order_id):
    if not hasattr(request.user, 'deliveryboy'):
        raise PermissionDenied
        
    delivery_boy = request.user.deliveryboy
    order = get_object_or_404(Order, id=order_id, delivery_boy=delivery_boy)
    
    context = {
        'order': order,
        'active_section': 'orders'
    }
    return render(request, 'delivery/order_detail.html', context)

@login_required(login_url='delivery:login')
def update_order_status(request, order_id):
    if not request.method == 'POST':
        return HttpResponseNotAllowed(['POST'])
        
    if not hasattr(request.user, 'deliveryboy'):
        raise PermissionDenied
        
    delivery_boy = request.user.deliveryboy
    order = get_object_or_404(Order, id=order_id, delivery_boy=delivery_boy)
    
    if order.order_status != 'out_for_delivery':
        messages.error(request, 'Can only update orders that are out for delivery')
        return redirect('delivery:orders')
    
    order.order_status = 'delivered'
    order.save()
    
    # Update delivery boy status to available
    delivery_boy.status = 'available'
    delivery_boy.save()
    
    messages.success(request, 'Order marked as delivered')
    return redirect('delivery:orders')

@login_required(login_url='delivery:login')
def update_availability(request):
    if not request.method == 'POST':
        return HttpResponseNotAllowed(['POST'])
        
    if not hasattr(request.user, 'deliveryboy'):
        raise PermissionDenied
        
    delivery_boy = request.user.deliveryboy
    status = request.POST.get('status')
    
    if status in ['available', 'offline']:
        delivery_boy.status = status
        delivery_boy.save()
        messages.success(request, f'Status updated to {status}')
    else:
        messages.error(request, 'Invalid status')
        
    return redirect('delivery:dashboard')

@login_required
def update_delivery_status(request, order_id):
    if not request.user.is_staff:  # Only allow staff/delivery personnel
        messages.error(request, 'You do not have permission to perform this action.')
        return redirect('home:home')
        
    order = get_object_or_404(Order, id=order_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        try:
            with transaction.atomic():
                if action == 'mark_delivered':
                    # Update order status to delivered
                    order.order_status = 'delivered'
                    
                    # For COD orders, also mark payment as completed
                    if order.payment_method == 'cod':
                        order.payment_status = 'paid'
                        messages.success(request, 'Order marked as delivered and payment collected.')
                    else:
                        messages.success(request, 'Order marked as delivered.')
                        
                    order.save()
                    
                elif action == 'mark_shipped':
                    order.order_status = 'shipped'
                    order.save()
                    messages.success(request, 'Order marked as shipped.')
                    
                else:
                    messages.error(request, 'Invalid action specified.')
                    
        except Exception as e:
            messages.error(request, f'Failed to update order status. Error: {str(e)}')
            
    return redirect('delivery:order_detail', order_id=order.id)

@login_required(login_url='delivery:login')
def send_otp(request, order_id):
    if not request.method == 'POST':
        return HttpResponseNotAllowed(['POST'])
        
    if not hasattr(request.user, 'deliveryboy'):
        raise PermissionDenied
        
    try:
        data = json.loads(request.body)
        phone_number = data.get('phone_number')
        
        if not phone_number or not phone_number.isdigit() or len(phone_number) != 10:
            return JsonResponse({
                'success': False,
                'message': 'Invalid phone number format'
            })
            
        delivery_boy = request.user.deliveryboy
        order = get_object_or_404(Order, id=order_id, delivery_boy=delivery_boy)
        
        if order.order_status != 'out_for_delivery':
            return JsonResponse({
                'success': False,
                'message': 'Can only verify orders that are out for delivery'
            })
        
        # Generate 6-digit OTP
        otp = str(random.randint(100000, 999999))
        
        # Store OTP and phone number in session
        request.session[f'delivery_otp_{order_id}'] = {
            'otp': otp,
            'phone_number': phone_number,
            'timestamp': timezone.now().timestamp(),
            'attempts': 0
        }
        
        # TODO: Integrate with actual SMS service
        # For now, we'll just print the OTP to console for testing
        print(f"OTP for order {order_id} sent to {phone_number}: {otp}")
        
        return JsonResponse({
            'success': True,
            'message': 'OTP sent successfully'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid request format'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        })

@login_required(login_url='delivery:login')
def verify_otp(request, order_id):
    if not request.method == 'POST':
        return HttpResponseNotAllowed(['POST'])
        
    if not hasattr(request.user, 'deliveryboy'):
        raise PermissionDenied
        
    delivery_boy = request.user.deliveryboy
    order = get_object_or_404(Order, id=order_id, delivery_boy=delivery_boy)
    
    # Get OTP details from session
    otp_details = request.session.get(f'delivery_otp_{order_id}')
    if not otp_details:
        messages.error(request, 'OTP has expired. Please send a new OTP.')
        return redirect('delivery:order_detail', order_id=order_id)
    
    # Check if OTP is expired (5 minutes validity)
    if timezone.now().timestamp() - otp_details['timestamp'] > 300:
        del request.session[f'delivery_otp_{order_id}']
        messages.error(request, 'OTP has expired. Please send a new OTP.')
        return redirect('delivery:order_detail', order_id=order_id)
    
    # Check if too many attempts
    if otp_details['attempts'] >= 3:
        del request.session[f'delivery_otp_{order_id}']
        messages.error(request, 'Too many incorrect attempts. Please send a new OTP.')
        return redirect('delivery:order_detail', order_id=order_id)
    
    # Verify OTP
    submitted_otp = request.POST.get('otp')
    if submitted_otp != otp_details['otp']:
        otp_details['attempts'] += 1
        request.session[f'delivery_otp_{order_id}'] = otp_details
        messages.error(request, 'Incorrect OTP. Please try again.')
        return redirect('delivery:order_detail', order_id=order_id)
    
    # OTP verified, mark order as delivered
    try:
        with transaction.atomic():
            order.order_status = 'delivered'
            if order.payment_method == 'cod':
                order.payment_status = 'paid'
            order.save()
            
            # Update delivery boy status to available
            delivery_boy.status = 'available'
            delivery_boy.save()
            
            # Clear OTP from session
            del request.session[f'delivery_otp_{order_id}']
            
            messages.success(request, 'Order marked as delivered successfully!')
    except Exception as e:
        messages.error(request, f'Failed to update order status. Error: {str(e)}')
    
    return redirect('delivery:orders')

@login_required(login_url='delivery:login')
def change_password(request):
    if request.method == 'POST':
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        user = request.user
        
        if not check_password(current_password, user.password):
            messages.error(request, 'Current password is incorrect')
            return redirect('delivery:profile')
            
        if new_password != confirm_password:
            messages.error(request, 'New passwords do not match')
            return redirect('delivery:profile')
            
        if len(new_password) < 8:
            messages.error(request, 'Password must be at least 8 characters long')
            return redirect('delivery:profile')
            
        user.set_password(new_password)
        user.save()
        messages.success(request, 'Password changed successfully. Please login again.')
        return redirect('delivery:login')
        
    return redirect('delivery:profile')
