from django.shortcuts import render, get_object_or_404
from admin_dashboard.models import Product, FoodCategory

def home(request):
    categories = FoodCategory.objects.all()
    featured_products = Product.objects.filter(is_featured=True)[:8]
    context = {
        'categories': categories,
        'featured_products': featured_products,
    }
    return render(request, 'home/index.html', context)

def about(request):
    return render(request, 'home/about.html')

def contact(request):
    return render(request, 'home/contact.html')

def category_products(request, category_id):
    category = get_object_or_404(FoodCategory, id=category_id)
    products = Product.objects.filter(
        category=category
    )
    context = {
        'category': category,
        'products': products,
    }
    return render(request, 'home/category_products.html', context)

def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    related_products = Product.objects.filter(
        category=product.category,
        status='approved'
    ).exclude(id=product.id)[:4]
    context = {
        'product': product,
        'related_products': related_products,
    }
    return render(request, 'home/product_detail.html', context)

def custom_404(request, exception):
    """Custom 404 error page"""
    return render(request, 'home/404.html', status=404)
