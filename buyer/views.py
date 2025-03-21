from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.db.models import Q
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db import transaction
from .models import (
    BuyerProfile, Address, Wishlist, Cart, Order, 
    OrderItem, Review
)
from admin_dashboard.models import Product, DeliveryLocation, Location
from .forms import (
    BuyerProfileForm, AddressForm, ReviewForm
)
from .auth_forms import BuyerRegistrationForm, BuyerLoginForm
import razorpay
from django.conf import settings
import json
from django.db import models
import logging

logger = logging.getLogger(__name__)

def buyer_register(request):
    if request.user.is_authenticated:
        return redirect('home:home')
        
    if request.method == 'POST':
        form = BuyerRegistrationForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Create user and buyer profile
                    user = form.save()
                    # Set sign_up_method to 'form'
                    
                    messages.success(request, 'Registration successful! Please login to continue.')
                    return redirect('buyer:login')
            except Exception as e:
                messages.error(request, f'Registration failed. Please try again. Error: {str(e)}')
        else:
            # Display form errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = BuyerRegistrationForm()
    
    return render(request, 'buyer/auth/register.html', {'form': form})

def buyer_login(request):
    if request.user.is_authenticated:
        return redirect('home:home')
        
    if request.method == 'POST':
        form = BuyerLoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            remember = form.cleaned_data.get('remember', False)
            
            try:
                # Try to authenticate
                user = authenticate(request, username=username, password=password)
                
                if user is not None:
                    # Check if user has a buyer profile
                    if hasattr(user, 'buyerprofile'):
                        # Set backend for authentication
                        user.backend = 'django.contrib.auth.backends.ModelBackend'
                        login(request, user)
                        
                        # Set session expiry if remember me is not checked
                        if not remember:
                            request.session.set_expiry(0)
                        
                        # Set flag to show location modal
                        request.session['show_location_modal'] = True
                            
                        # messages.success(request, f'Login Sucessfull')
                        return redirect('home:home')
                    else:
                        messages.error(request, 'This account is not registered as a buyer.')
                else:
                    messages.error(request, 'Invalid username/email or password.')
            except Exception as e:
                messages.error(request, f'Login failed. Please try again. Error: {str(e)}')
        else:
            # Display form errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = BuyerLoginForm()
    
    return render(request, 'buyer/auth/login.html', {'form': form})

@login_required
def buyer_logout(request):
    logout(request)
    messages.success(request, 'You have been successfully logged out.')
    return redirect('home:home')

@login_required
def profile(request):
    profile, created = BuyerProfile.objects.get_or_create(user=request.user)
    addresses = Address.objects.filter(user=request.user)
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    
    if request.method == 'POST':
        form = BuyerProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('buyer:profile')
    else:
        form = BuyerProfileForm(instance=profile)
    
    context = {
        'profile': profile,
        'form': form,
        'addresses': addresses,
        'orders': orders
    }
    return render(request, 'buyer/profile.html', context)

@login_required
def manage_addresses(request):
    addresses = Address.objects.filter(user=request.user)
    form = AddressForm()
    
    if request.method == 'POST':
        form = AddressForm(request.POST)
        if form.is_valid():
            address = form.save(commit=False)
            address.user = request.user
            address.save()
            messages.success(request, 'Address added successfully!')
            return redirect('buyer:manage_addresses')
    
    context = {
        'addresses': addresses,
        'form': form
    }
    return render(request, 'buyer/manage_addresses.html', context)

@login_required
def edit_address(request, address_id):
    address = get_object_or_404(Address, id=address_id, user=request.user)
    if request.method == 'POST':
        form = AddressForm(request.POST, instance=address)
        if form.is_valid():
            form.save()
            messages.success(request, 'Address updated successfully!')
            return redirect('buyer:manage_addresses')
    else:
        form = AddressForm(instance=address)
    
    context = {
        'form': form,
        'address': address,
        'addresses': Address.objects.filter(user=request.user)
    }
    return render(request, 'buyer/manage_addresses.html', context)

@login_required
def delete_address(request, address_id):
    if request.method == 'POST':
        address = get_object_or_404(Address, id=address_id, user=request.user)
        address.delete()
        messages.success(request, 'Address deleted successfully!')
    return redirect('buyer:manage_addresses')

@login_required
def wishlist(request):
    wishlist_items = Wishlist.objects.filter(user=request.user).select_related('product')
    context = {
        'wishlist_items': wishlist_items,
    }
    return render(request, 'buyer/wishlist.html', context)



@login_required
def add_to_wishlist(request, product_id):
    if request.method == 'POST':
        try:
            # Get the product
            product = get_object_or_404(Product, id=product_id, status='approved')
            
            # Add to wishlist
            wishlist_item, created = Wishlist.objects.get_or_create(
                user=request.user,
                product=product
            )
            
            if created:
                message = 'Added to wishlist successfully!'
            else:
                # If already in wishlist, remove it (toggle behavior)
                wishlist_item.delete()
                message = 'Removed from wishlist'
            
            return JsonResponse({
                'success': True,
                'message': message,
                'in_wishlist': created
            })
            
        except Product.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Product not found'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)
    
    return JsonResponse({
        'success': False,
        'error': 'Invalid request method'
    }, status=400)


# views.py
@login_required
def remove_from_wishlist(request, product_id):
    if request.method == 'POST':
        try:
            wishlist_item = Wishlist.objects.get(user=request.user, product_id=product_id)
            product_name = wishlist_item.product.name
            wishlist_item.delete()
            return JsonResponse({
                'success': True,
                'message': f'{product_name} has been removed from your wishlist.'
            })
        except Wishlist.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Item not found in your wishlist.'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=400)





@login_required
def cart(request):
    cart_items = Cart.objects.filter(user=request.user).select_related('product')
    total = sum(item.product.price * item.quantity for item in cart_items)
    context = {
        'cart_items': cart_items,
        'total': total,
    }
    return render(request, 'buyer/cart.html', context)

@login_required
def add_to_cart(request, product_id):
    if request.method == 'POST':
        try:
            # Get the product
            product = get_object_or_404(Product, id=product_id, status='approved')
            
            # Get quantity from form
            quantity = int(request.POST.get('quantity', 1))
            
            # Validate quantity
            if quantity <= 0:
                return JsonResponse({
                    'success': False,
                    'error': 'Please enter a valid quantity'
                }, status=400)
            
            # Check stock
            if product.stock < quantity:
                return JsonResponse({
                    'success': False,
                    'error': f'Only {product.stock} items available in stock'
                }, status=400)
            elif product.stock <= 0:
                return JsonResponse({
                    'success': False,
                    'error': 'Product is out of stock'
                }, status=400)
            
            # Add to cart
            cart_item, created = Cart.objects.get_or_create(
                user=request.user,
                product=product,
                defaults={'quantity': quantity}
            )
            
            if not created:
                # If item exists, add the new quantity
                cart_item.quantity += quantity
                # Ensure we don't exceed stock
                if cart_item.quantity > product.stock:
                    return JsonResponse({
                        'success': False,
                        'error': f'Cannot add more items. Only {product.stock} available in stock'
                    }, status=400)
                cart_item.save()
            
            # Get updated cart count
            cart_count = Cart.objects.filter(user=request.user).aggregate(
                total=models.Sum('quantity')
            )['total'] or 0
            
            return JsonResponse({
                'success': True,
                'message': f'Added {quantity} item(s) to cart successfully!',
                'cart_count': cart_count
            })
            
        except ValueError:
            return JsonResponse({
                'success': False,
                'error': 'Please enter a valid quantity'
            }, status=400)
        except Product.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Product not found'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)
    
    return JsonResponse({
        'success': False,
        'error': 'Invalid request method'
    }, status=400)

@login_required
def update_cart(request, cart_item_id):
    if request.method == 'POST':
        cart_item = get_object_or_404(Cart, id=cart_item_id, user=request.user)
        action = request.POST.get('action')
        
        if action == 'remove':
            cart_item.delete()
            messages.success(request, 'Item removed from cart.')
        else:
            quantity = int(request.POST.get('quantity', 1))
            if quantity > cart_item.product.stock:
                messages.error(request, f'Sorry, only {cart_item.product.stock} units available.')
            else:
                cart_item.quantity = quantity
                cart_item.save()
                messages.success(request, 'Cart updated successfully.')
                
    return redirect('buyer:cart')

@login_required
def remove_from_cart(request, cart_item_id):
    if request.method == 'POST':
        cart_item = get_object_or_404(Cart, id=cart_item_id, user=request.user)
        product_name = cart_item.product.name
        cart_item.delete()
        messages.success(request, f'{product_name} has been removed from your cart.')
    return redirect('buyer:cart')

@login_required
def checkout(request):
    cart_items = Cart.objects.filter(user=request.user)
    
    # Validate cart is not empty
    if not cart_items.exists():
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'message': 'Your cart is empty!'})
        messages.error(request, 'Your cart is empty!')
        return redirect('buyer:cart')
    
    addresses = Address.objects.filter(user=request.user)
    
    # Validate user has at least one address
    if not addresses.exists():
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'message': 'Please add a delivery address before checkout!'})
        messages.error(request, 'Please add a delivery address before checkout!')
        return redirect('buyer:manage_addresses')
    
    total = sum(item.product.price * item.quantity for item in cart_items)
    
    # Validate minimum order amount
    if total < 100:  # Minimum order amount ₹100
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'message': 'Minimum order amount is ₹100!'})
        messages.error(request, 'Minimum order amount is ₹100!')
        return redirect('buyer:cart')
    
    if request.method == 'POST':
        address_id = request.POST.get('address')
        payment_method = request.POST.get('payment_method')
        
        # Validate required fields
        if not address_id:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'status': 'error', 'message': 'Please select a delivery address!'})
            messages.error(request, 'Please select a delivery address!')
            return redirect('buyer:checkout')
            
        if not payment_method:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'status': 'error', 'message': 'Please select a payment method!'})
            messages.error(request, 'Please select a payment method!')
            return redirect('buyer:checkout')
            
        if payment_method not in ['cod', 'razorpay']:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'status': 'error', 'message': 'Invalid payment method!'})
            messages.error(request, 'Invalid payment method!')
            return redirect('buyer:checkout')
        
        try:
            address = Address.objects.get(id=address_id, user=request.user)
        except Address.DoesNotExist:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'status': 'error', 'message': 'Selected address is invalid!'})
            messages.error(request, 'Selected address is invalid!')
            return redirect('buyer:checkout')
        
        try:
            with transaction.atomic():
                # Validate stock availability
                for cart_item in cart_items:
                    if cart_item.quantity > cart_item.product.stock:
                        error_msg = f'Sorry! Only {cart_item.product.stock} units available for {cart_item.product.name}'
                        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                            return JsonResponse({'status': 'error', 'message': error_msg})
                        messages.error(request, error_msg)
                        return redirect('buyer:cart')
                
                # Create order with appropriate status
                order = Order.objects.create(
                    user=request.user,
                    address=address,
                    total_amount=total,
                    payment_method=payment_method,
                    payment_status='pending',  # Always start as pending
                    order_status='pending'  # Order status starts as pending
                )
                
                # Create order items and update stock
                for cart_item in cart_items:
                    OrderItem.objects.create(
                        order=order,
                        product=cart_item.product,
                        quantity=cart_item.quantity,
                        price=cart_item.product.price
                    )
                    
                    # Update product stock
                    cart_item.product.stock -= cart_item.quantity
                    cart_item.product.save()
                
                # Clear cart
                cart_items.delete()
                
                # Store order ID in session for payment processing
                request.session['order_id'] = order.id
                
                # Return appropriate response based on request type
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    if payment_method == 'razorpay':
                        return JsonResponse({
                            'status': 'success',
                            'order_id': order.id,
                            'redirect_url': reverse('buyer:payment_page', args=[order.id])
                        })
                    else:  # COD
                        return JsonResponse({
                            'status': 'success',
                            'redirect_url': reverse('buyer:order_detail', args=[order.id])
                        })
                
                # Redirect based on payment method
                if payment_method == 'razorpay':
                    messages.info(request, 'Please complete your payment to confirm the order.')
                    return redirect('buyer:payment_page', order_id=order.id)
                else:  # COD
                    messages.success(request, 'Order placed successfully! Payment will be collected upon delivery.')
                    return redirect('buyer:order_detail', order_id=order.id)
                    
        except Exception as e:
            error_msg = f'Failed to place order. Please try again! Error: {str(e)}'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'status': 'error', 'message': error_msg})
            messages.error(request, error_msg)
            return redirect('buyer:checkout')
    
    context = {
        'cart_items': cart_items,
        'addresses': addresses,
        'total': total,
        'RAZORPAY_KEY_ID': settings.RAZORPAY_KEY_ID
    }
    return render(request, 'buyer/checkout.html', context)

@login_required
def payment_page(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    # Redirect to order detail if payment is already completed
    if order.payment_status == 'paid':
        return redirect('buyer:order_detail', order_id=order_id)
    
    context = {
        'order': order,
        'RAZORPAY_KEY_ID': settings.RAZORPAY_KEY_ID
    }
    return render(request, 'buyer/payment.html', context)

@login_required
def initiate_payment(request):
    if request.method == 'POST':
        try:
            order_id = request.POST.get('order_id')
            order = get_object_or_404(Order, id=order_id, user=request.user)
            
            if order.payment_status == 'paid':
                return JsonResponse({
                    'status': 'error',
                    'message': 'Payment already completed'
                })
            
            # Initialize Razorpay client
            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            
            # Create Razorpay order
            payment_data = {
                'amount': int(float(order.total_amount) * 100),  # Convert to paise
                'currency': 'INR',
                'receipt': f'order_{order.id}',
                'payment_capture': 1
            }
            
            # Create Razorpay order
            razorpay_order = client.order.create(data=payment_data)
            
            # Save Razorpay order ID to our order
            order.razorpay_order_id = razorpay_order['id']
            order.save()
            
            # Return success response with order details
            return JsonResponse({
                'status': 'success',
                'order_id': razorpay_order['id'],
                'amount': payment_data['amount'],
                'currency': payment_data['currency']
            })
            
        except Exception as e:
            logger.error(f"Payment initialization error: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': 'Failed to initialize payment. Please try again.'
            })
    
    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method'
    })

@csrf_exempt
def payment_callback(request):
    if request.method == 'POST':
        try:
            # Get payment details from POST data
            payment_id = request.POST.get('razorpay_payment_id')
            razorpay_order_id = request.POST.get('razorpay_order_id')
            signature = request.POST.get('razorpay_signature')
            
            # Validate required parameters
            if not all([payment_id, razorpay_order_id, signature]):
                raise ValueError('Missing required payment parameters')
            
            # Initialize Razorpay client
            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            
            # Verify signature
            params_dict = {
                'razorpay_payment_id': payment_id,
                'razorpay_order_id': razorpay_order_id,
                'razorpay_signature': signature
            }
            
            try:
                # Verify the payment signature
                client.utility.verify_payment_signature(params_dict)
                
                # Get and update the order
                order = Order.objects.get(razorpay_order_id=razorpay_order_id)
                order.payment_id = payment_id
                order.payment_status = 'paid'
                order.order_status = 'processing'  # Move to processing after payment
                order.save()
                
                # Clear session data
                request.session.pop('order_id', None)
                
                messages.success(request, 'Payment successful! Your order has been confirmed and is being processed.')
                return redirect('buyer:order_detail', order_id=order.id)
                
            except Exception as e:
                logger.error(f"Payment verification failed: {str(e)}")
                
                # Get and update the order status
                order = Order.objects.get(razorpay_order_id=razorpay_order_id)
                order.payment_status = 'failed'
                order.save()
                
                messages.error(request, 'Payment verification failed. Please try again.')
                return redirect('buyer:payment_failed')
                
        except ValueError as e:
            logger.error(f"Invalid payment parameters: {str(e)}")
            messages.error(request, 'Invalid payment parameters received.')
            return redirect('buyer:payment_failed')
            
        except Order.DoesNotExist:
            logger.error("Order not found for Razorpay order ID: " + razorpay_order_id)
            messages.error(request, 'Order not found. Please contact support.')
            return redirect('buyer:payment_failed')
            
        except Exception as e:
            logger.error(f"Payment callback error: {str(e)}")
            messages.error(request, 'Payment processing failed. Please contact support.')
            return redirect('buyer:payment_failed')
    
    return JsonResponse({
        'error': 'Invalid request method'
    }, status=400)

@login_required
def payment_failed(request):
    messages.error(request, 'Payment failed. Please try again or choose a different payment method.')
    return redirect('buyer:orders')

@login_required
def order_history(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'buyer/order_history.html', {'orders': orders})

@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'buyer/order_detail.html', {'order': order})

@login_required
def cancel_order(request, order_id):
    try:
        order = get_object_or_404(Order, id=order_id, user=request.user)
        
        if request.method == 'POST':
            try:
                if not order.can_cancel():
                    messages.error(request, 'This order cannot be cancelled. Orders can only be cancelled within 1 hour of placing.')
                    return redirect('buyer:order_detail', order_id=order.id)
                
                order.cancel_order()
                messages.success(request, 'Order cancelled successfully! Your refund will be processed if payment was made.')
                
                # Handle refund for online payments
                if order.payment_method == 'razorpay' and order.payment_id:
                    try:
                        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
                        refund = client.payment.refund(order.payment_id, {
                            'amount': int(order.total_amount * 100),  # Amount in paise
                            'notes': {
                                'order_id': str(order.id),
                                'reason': 'Customer cancelled order'
                            }
                        })
                        messages.success(request, 'Refund initiated successfully!')
                    except Exception as e:
                        messages.warning(request, 'Order cancelled, but refund initiation failed. Our team will process it manually.')
                
            except ValueError as e:
                messages.error(request, str(e))
            except Exception as e:
                messages.error(request, f'Failed to cancel order. Error: {str(e)}')
        
        return redirect('buyer:order_detail', order_id=order.id)
        
    except Order.DoesNotExist:
        messages.error(request, 'Order not found!')
        return redirect('buyer:order_history')

@login_required
def add_review(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.user = request.user
            review.product = product
            review.save()
            messages.success(request, 'Review added successfully!')
            return redirect('product_detail', product_id=product_id)
    else:
        form = ReviewForm()
    
    context = {
        'form': form,
        'product': product
    }
    return render(request, 'buyer/add_review.html', context)

@login_required
@require_http_methods(["POST"])
def verify_location(request):
    try:
        # Get pincode from request
        data = json.loads(request.body)
        pincode = str(data.get('pincode', '')).strip()
        
        # First validate that it's a 6-digit number
        if not pincode:
            return JsonResponse({
                'success': False,
                'message': 'Please enter a pincode'
            })
        
        if not pincode.isdigit() or len(pincode) != 6:
            return JsonResponse({
                'success': False,
                'message': 'Please enter a valid 6-digit pincode'
            })
        
        # Get all active locations from the admin's Location table
        active_locations = Location.objects.filter(is_active=True)
        
        # Check if the entered pincode matches any active location
        try:
            # Try to find the matching location
            location = active_locations.get(pincode=pincode)
            
            # If it matches: Store the location details in the session
            request.session['delivery_pincode'] = location.pincode
            request.session['delivery_location'] = {
                'name': location.name,
                'city': location.city,
                'pincode': location.pincode
            }
            
            # Allow shopping by setting can_shop=True
            request.session['can_shop'] = True
            request.session.pop('show_location_modal', None)
            
            # Show success message with location name and city
            return JsonResponse({
                'success': True,
                'message': f'Login Successfull... Welcome back, {request.user.first_name}! We deliver to {location.name}, {location.city}.',
                'redirect_url': reverse('home:home')
            })
            
        except Location.DoesNotExist:
            # If it doesn't match:
            # Prevent shopping by setting can_shop=False
            request.session['can_shop'] = False
            
            # Get list of all available locations for error message
            available_locations = [
                f"{loc.pincode} ({loc.name})" 
                for loc in active_locations
            ]
            locations_str = ", ".join(available_locations)
            
            # Show error message listing all available locations with their pincodes
            return JsonResponse({
                'success': False,
                'message': f'Sorry, we do not deliver to {pincode}. Available delivery locations: {locations_str}'
            })
            
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid request format'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': 'An error occurred. Please try again.'
        })

@login_required
@ensure_csrf_cookie
def clear_location_modal(request):
    if request.method == 'POST':
        request.session.pop('show_location_modal', None)
        return JsonResponse({'success': True})
    return JsonResponse({'success': False})

def search_products(request):
    query = request.GET.get('q', '')
    category = request.GET.get('category')
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    
    products = Product.objects.filter(status='approved')
    
    if query:
        products = products.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query)
        )
    
    if category:
        products = products.filter(category_id=category)
    
    if min_price:
        products = products.filter(price__gte=min_price)
    
    if max_price:
        products = products.filter(price__lte=max_price)
    
    context = {
        'products': products,
        'query': query
    }
    return render(request, 'buyer/search_results.html', context)

from django.contrib.auth.forms import PasswordResetForm
from django.core.mail import send_mail
from django.contrib import messages
from django.shortcuts import render, redirect
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.shortcuts import get_current_site

def custom_password_reset(request):
    if request.method == 'POST':
        form = PasswordResetForm(request.POST)
        print("Form submitted with email:", request.POST.get('email'))  # Debug print
        
        if form.is_valid():
            email = form.cleaned_data['email']
            print("Form is valid, email:", email)  # Debug print
            
            try:
                # Get associated users
                associated_users = user.objects.filter(email=email)
                print("Found users:", associated_users.count())  # Debug print
                
                if associated_users.exists():
                    for user in associated_users:
                        print(f"Processing reset for user: {user.username}")  # Debug print
                        
                        # Generate token
                        token = default_token_generator.make_token(user)
                        uid = urlsafe_base64_encode(force_bytes(user.pk))
                        
                        # Build reset URL
                        current_site = get_current_site(request)
                        reset_url = f"{request.scheme}://{current_site.domain}/buyer/password-reset-confirm/{uid}/{token}/"
                        print("Reset URL:", reset_url)  # Debug print
                        
                        # Prepare email content
                        context = {
                            'user': user,
                            'reset_url': reset_url,
                            'site_name': 'Home Fresh',
                            'protocol': request.scheme,
                            'domain': current_site.domain,
                            'uid': uid,
                            'token': token,
                        }
                        
                        email_subject = "Password Reset Request"
                        email_body = render_to_string('buyer/auth/password_reset_email.html', context)
                        print("Email body:", email_body)  # Debug print
                        
                        try:
                            # Send email
                            send_mail(
                                email_subject,
                                email_body,
                                'Home Fresh <mekhasabu2001@gmail.com>',
                                [user.email],
                                fail_silently=False,
                            )
                            print("Email sent successfully")  # Debug print
                            messages.success(request, 'Password reset email has been sent. Please check your inbox.')
                            return redirect('buyer:password_reset_done')
                        except Exception as mail_error:
                            print(f"Email sending error: {str(mail_error)}")  # Debug print
                            raise mail_error
                else:
                    print("No user found with email:", email)  # Debug print
                    messages.error(request, 'No user found with this email address.')
            except Exception as e:
                print(f"Error in password reset: {str(e)}")  # Debug print
                messages.error(request, 'There was an error sending the password reset email. Please try again.')
        else:
            print("Form errors:", form.errors)  # Debug print
    else:
        form = PasswordResetForm()
    
    return render(request, 'buyer/auth/password_reset.html', {'form': form})


from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.core.mail import send_mail
from django.urls import reverse
from django.shortcuts import render, redirect
from .forms import DeleteAccountForm

from django.contrib import messages

@login_required
def delete_account(request):
    user = request.user
    try:
        profile = user.buyerprofile
    except BuyerProfile.DoesNotExist:
        messages.error(request, 'Profile not found.', extra_tags='delete_account')
        return redirect('buyer:profile')

    sign_up_method = profile.sign_up_method

    if request.method == 'POST':
        form = DeleteAccountForm(request.POST, user=user)
        if form.is_valid():
            if sign_up_method == 'form':
                user.delete()
                messages.success(request, 'Your account has been successfully deleted.', extra_tags='delete_account')
                return redirect('home:home')
            else:
                token = default_token_generator.make_token(user)
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                delete_url = reverse('buyer:confirm_delete', kwargs={'uidb64': uid, 'token': token})
                delete_url = request.build_absolute_uri(delete_url)
                send_mail(
                    'Confirm Account Deletion',
                    f'Click the link to confirm account deletion: {delete_url}',
                    'noreply@example.com',
                    [user.email],
                    fail_silently=False,
                )
                messages.info(request, 'A confirmation email has been sent to your email address.', extra_tags='delete_account')
                return redirect('buyer:profile')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{error}', extra_tags='delete_account')
    else:
        form = DeleteAccountForm(user=user)

    return render(request, 'buyer/delete_account.html', {
        'form': form,
        'sign_up_method': sign_up_method
    })



from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.contrib.auth.models import User

def confirm_delete(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        user.delete()
        messages.success(request, 'Your account has been successfully deleted.')
        return redirect('home:home')
    else:
        messages.error(request, 'Invalid or expired confirmation link.')
        return redirect('home:home')






# @login_required
# def add_to_wishlist(request, product_id):
#     if request.method == 'POST':
#         try:
#             product = Product.objects.get(id=product_id, status='approved')
#             wishlist_item, created = Wishlist.objects.get_or_create(
#                 user=request.user,
#                 product=product
#             )
#             if created:
#                 messages.success(request, f'{product.name} has been added to your wishlist.')
#             else:
#                 messages.info(request, f'{product.name} is already in your wishlist.')
#         except Product.DoesNotExist:
#             messages.error(request, 'Product not found')
#     return redirect('home:product', product_id=product_id)