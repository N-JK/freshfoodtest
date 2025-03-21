// Initialize AOS
AOS.init({
    duration: 800,
    easing: 'ease-out-cubic',
    once: true,
    offset: 50
});

// Product Functions
function viewProductDetails(productId) {
    window.location.href = `/product/${productId}/`;
}

function addToCart(productId, button) {
    // Check if user is authenticated
    if (!isUserAuthenticated()) {
        window.location.href = '/buyer/login/';
        return;
    }

    // Disable button and show loading
    button.disabled = true;
    const originalContent = button.innerHTML;
    button.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
    
    fetch(`/buyer/cart/add/${productId}/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'Content-Type': 'application/json'
        },
        credentials: 'same-origin'  // Add this to ensure cookies are sent
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
    .then(data => {
        if(data.success) {
            Swal.fire({
                title: 'Success!',
                text: 'Product added to cart',
                icon: 'success',
                timer: 2000,
                showConfirmButton: false
            });
            // Update cart count if available
            const cartCount = document.getElementById('cart-count');
            if (cartCount && data.cart_count !== undefined) {
                cartCount.textContent = data.cart_count;
            }
        } else {
            throw new Error(data.error || 'Failed to add to cart');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        Swal.fire({
            title: 'Error',
            text: error.message || 'Failed to add to cart',
            icon: 'error',
            timer: 2000,
            showConfirmButton: false
        });
    })
    .finally(() => {
        // Reset button
        button.disabled = false;
        button.innerHTML = originalContent;
    });
}

function addToWishlist(productId, button) {
    // Check if user is authenticated
    if (!isUserAuthenticated()) {
        window.location.href = '/buyer/login/';
        return;
    }

    // Disable button and show loading
    button.disabled = true;
    const originalContent = button.innerHTML;
    button.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';

    fetch(`/buyer/wishlist/add/${productId}/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'Content-Type': 'application/json'
        },
        credentials: 'same-origin'  // Add this to ensure cookies are sent
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
    .then(data => {
        if(data.success) {
            button.classList.toggle('active');
            const icon = button.querySelector('i');
            if (data.in_wishlist) {
                icon.classList.add('fas', 'text-danger');
                icon.classList.remove('far');
            } else {
                icon.classList.add('far');
                icon.classList.remove('fas', 'text-danger');
            }
            Swal.fire({
                title: 'Success!',
                text: data.message,
                icon: 'success',
                timer: 2000,
                showConfirmButton: false
            });
        } else {
            throw new Error(data.error || 'Failed to update wishlist');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        Swal.fire({
            title: 'Error',
            text: error.message || 'Failed to update wishlist',
            icon: 'error',
            timer: 2000,
            showConfirmButton: false
        });
    })
    .finally(() => {
        // Reset button
        button.disabled = false;
        button.innerHTML = originalContent;
    });
}

// Helper function to check if user is authenticated
function isUserAuthenticated() {
    return document.body.classList.contains('user-authenticated');
}

// Helper Functions
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Scroll Animations
document.addEventListener('DOMContentLoaded', function() {
    // Reveal animations for featured products
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
            }
        });
    }, {
        threshold: 0.1
    });

    document.querySelectorAll('.featured-product-card').forEach(card => {
        observer.observe(card);
    });

    // Smooth scroll for navigation links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
});
