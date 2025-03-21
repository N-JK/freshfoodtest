# Buyer Module

The Buyer Module is a comprehensive e-commerce solution that allows users to browse products, manage their wishlist, and complete purchases securely.

## Features

### User Authentication
- Secure sign-up and login functionality
- Password reset and account recovery options
- Profile management with personal details and profile picture

### Product Browsing & Search
- Advanced product search with filters
- Category-based browsing
- Sort products by various criteria (price, name, etc.)
- Detailed product pages with descriptions and reviews

### Wishlist Management
- Add/remove products to wishlist
- Move items from wishlist to cart
- Stock status notifications

### Shopping Cart
- Add products to cart
- Update quantities
- Remove items
- Real-time total calculation

### Checkout Process
- Multiple payment options
  - Cash on Delivery
  - Credit/Debit Card
  - UPI Payment
  - Net Banking
- Address management
- Order summary
- Apply discount coupons

### Order Management
- Order history
- Order tracking
- Order status updates
- Download invoices
- Cancel orders (if eligible)

### Product Reviews
- Rate and review purchased products
- View other buyers' reviews
- Help other buyers make informed decisions

## Setup

1. Install required packages:
```bash
pip install -r requirements.txt
```

2. Add 'buyer' to INSTALLED_APPS in settings.py:
```python
INSTALLED_APPS = [
    ...
    'buyer',
    ...
]
```

3. Run migrations:
```bash
python manage.py makemigrations buyer
python manage.py migrate
```

4. Include buyer URLs in your project's urls.py:
```python
urlpatterns = [
    ...
    path('buyer/', include('buyer.urls')),
    ...
]
```

## Models

### BuyerProfile
- Extended user profile with additional details
- Phone number and address information
- Profile picture support

### Address
- Multiple addresses per user
- Default address selection
- Comprehensive address fields

### Wishlist
- Many-to-many relationship between users and products
- Timestamp tracking
- Unique constraint per user-product pair

### Cart
- Shopping cart implementation
- Quantity management
- Total price calculation

### Order
- Order status tracking
- Payment method selection
- Delivery address association

### OrderItem
- Individual items in an order
- Quantity and price tracking
- Total calculation per item

### Review
- Product ratings and comments
- One review per product per user
- Timestamp tracking

## Views

### Profile Management
- Profile view and update
- Address management
- Order history

### Shopping
- Cart management
- Wishlist operations
- Checkout process
- Order placement

### Product Interaction
- Product search
- Product filtering
- Review submission

## Templates

### Base Template
- Consistent layout
- Navigation menu
- User information

### Shopping Templates
- Cart view
- Wishlist view
- Checkout page
- Order details

### Profile Templates
- Profile management
- Address book
- Order history

## JavaScript Features

- Real-time cart updates
- Dynamic filtering
- Form validation
- Address selection
- Payment method handling

## CSS Styling

The module uses Bootstrap 5 for responsive design and includes custom styles for:
- Product cards
- Cart items
- Order timeline
- Form elements
- Responsive layouts

## Security Features

- CSRF protection
- User authentication required for sensitive operations
- Secure payment handling
- Data validation and sanitization

## Future Enhancements

1. Social media login integration
2. Real-time order tracking
3. Advanced payment gateway integration
4. Wishlist sharing
5. Enhanced product recommendations
6. Email notifications for order updates
7. Return and refund management
8. Customer support integration
