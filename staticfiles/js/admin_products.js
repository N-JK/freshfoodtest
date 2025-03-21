// Wait for DOM to be ready
$(document).ready(function() {
    // Initialize tooltips
    const tooltips = $('[data-bs-toggle="tooltip"]');
    if (tooltips.length) {
        tooltips.tooltip();
    }

    // Handle product filtering
    function filterProducts(filter) {
        const products = $('.product-card');
        
        products.each(function() {
            const card = $(this);
            const isFeatured = card.data('featured');
            const status = card.data('status');
            
            switch(filter) {
                case 'featured':
                    card.toggle(isFeatured);
                    break;
                case 'pending':
                    card.toggle(status === 'pending');
                    break;
                default:
                    card.show();
            }
        });
    }

    // Handle filter button clicks
    $('.filter-btn').click(function() {
        const filter = $(this).data('filter');
        $('.filter-btn').removeClass('active');
        $(this).addClass('active');
        filterProducts(filter);
    });

    // Handle stat card clicks
    $('.stat-card.clickable').click(function() {
        const filter = $(this).data('filter');
        $('.filter-btn').removeClass('active');
        $(`.filter-btn[data-filter="${filter}"]`).addClass('active');
        filterProducts(filter);
    });

    // Handle edit product
    $('.edit-product').click(function() {
        const productId = $(this).data('product-id');
        loadProductForEdit(productId);
    });

    // Toggle featured status
    $('.toggle-featured').click(function() {
        const button = $(this);
        const productId = button.data('product-id');
        const isFeatured = button.hasClass('btn-warning');
        
        Swal.fire({
            title: `${isFeatured ? 'Unfeature' : 'Feature'} Product?`,
            text: `Are you sure you want to ${isFeatured ? 'remove this product from' : 'add this product to'} featured products?`,
            icon: 'question',
            showCancelButton: true,
            confirmButtonText: 'Yes',
            cancelButtonText: 'No'
        }).then((result) => {
            if (result.isConfirmed) {
                $.ajax({
                    url: `/admin/products/${productId}/toggle-featured/`,
                    type: 'POST',
                    headers: {
                        'X-CSRFToken': getCsrfToken()
                    },
                    success: function(response) {
                        if (response.success) {
                            // Toggle button appearance
                            if (response.is_featured) {
                                button.removeClass('btn-outline-warning').addClass('btn-warning');
                            } else {
                                button.removeClass('btn-warning').addClass('btn-outline-warning');
                            }
                            // Show success message
                            showNotification('success', response.message);
                            // Update featured badge
                            const card = button.closest('.product-card');
                            if (response.is_featured) {
                                card.attr('data-featured', 'true');
                                if (!card.find('.product-badge.featured').length) {
                                    card.find('.product-image').append('<div class="product-badge featured">Featured</div>');
                                }
                            } else {
                                card.attr('data-featured', 'false');
                                card.find('.product-badge.featured').remove();
                            }
                        }
                    },
                    error: function(xhr) {
                        showNotification('error', 'Failed to update featured status');
                    }
                });
            }
        });
    });

    // Handle product approval
    $('.approve-product').click(function() {
        const button = $(this);
        const productId = button.data('product-id');
        
        Swal.fire({
            title: 'Approve Product?',
            text: 'Are you sure you want to approve this product?',
            icon: 'question',
            showCancelButton: true,
            confirmButtonText: 'Yes',
            cancelButtonText: 'No'
        }).then((result) => {
            if (result.isConfirmed) {
                $.ajax({
                    url: `/admin/products/${productId}/approve/`,
                    type: 'POST',
                    headers: {
                        'X-CSRFToken': getCsrfToken()
                    },
                    success: function(response) {
                        if (response.success) {
                            showNotification('success', 'Product approved successfully');
                            const card = button.closest('.product-card');
                            card.attr('data-status', 'approved');
                            card.find('.product-badge.pending').remove();
                            card.find('.approve-product, .reject-product').remove();
                        }
                    },
                    error: function(xhr) {
                        showNotification('error', 'Failed to approve product');
                    }
                });
            }
        });
    });

    // Handle product rejection
    $('.reject-product').click(function() {
        const button = $(this);
        const productId = button.data('product-id');
        
        Swal.fire({
            title: 'Reject Product?',
            text: 'Are you sure you want to reject this product?',
            icon: 'warning',
            showCancelButton: true,
            confirmButtonText: 'Yes',
            cancelButtonText: 'No',
            confirmButtonColor: '#dc3545'
        }).then((result) => {
            if (result.isConfirmed) {
                $.ajax({
                    url: `/admin/products/${productId}/reject/`,
                    type: 'POST',
                    headers: {
                        'X-CSRFToken': getCsrfToken()
                    },
                    success: function(response) {
                        if (response.success) {
                            showNotification('success', 'Product rejected successfully');
                            const card = button.closest('.product-card');
                            card.fadeOut(() => card.remove());
                        }
                    },
                    error: function(xhr) {
                        showNotification('error', 'Failed to reject product');
                    }
                });
            }
        });
    });

    // Create restock request
    $('.create-restock').click(function() {
        const button = $(this);
        const productId = button.data('product-id');
        
        Swal.fire({
            title: 'Create Restock Request?',
            text: 'Are you sure you want to create a restock request for this product?',
            icon: 'question',
            showCancelButton: true,
            confirmButtonText: 'Yes',
            cancelButtonText: 'No'
        }).then((result) => {
            if (result.isConfirmed) {
                // Disable button to prevent double submission
                button.prop('disabled', true);
                
                $.ajax({
                    url: `/admin/products/${productId}/restock/`,
                    type: 'POST',
                    headers: {
                        'X-CSRFToken': getCsrfToken()
                    },
                    success: function(response) {
                        if (response.success) {
                            showNotification('success', 'Restock request created successfully');
                            // Optionally hide the restock button
                            button.fadeOut();
                        }
                    },
                    error: function(xhr) {
                        showNotification('error', 'Failed to create restock request');
                        button.prop('disabled', false);
                    }
                });
            }
        });
    });

    // Load product data for editing
    function loadProductForEdit(productId) {
        $.ajax({
            url: `/admin/products/${productId}/`,
            type: 'GET',
            success: function(response) {
                // Populate edit modal with product data
                $('#editProductModal').find('#edit-product-id').val(productId);
                $('#editProductModal').find('#edit-product-name').val(response.name);
                $('#editProductModal').find('#edit-product-price').val(response.price);
                $('#editProductModal').find('#edit-product-stock').val(response.stock);
                $('#editProductModal').find('#edit-product-threshold').val(response.threshold);
                $('#editProductModal').find('#edit-product-category').val(response.category_id);
                $('#editProductModal').find('#edit-product-description').val(response.description);
                
                // Show current image if exists
                const imagePreview = $('#editProductModal').find('#edit-image-preview');
                if (response.image) {
                    imagePreview.attr('src', response.image).show();
                } else {
                    imagePreview.hide();
                }
                
                // Show the modal
                $('#editProductModal').modal('show');
            },
            error: function(xhr) {
                showNotification('error', 'Failed to load product data');
            }
        });
    }

    // Handle image preview
    $('#edit-product-image').change(function() {
        const file = this.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = function(e) {
                $('#edit-image-preview').attr('src', e.target.result).show();
            };
            reader.readAsDataURL(file);
        }
    });

    // Handle product update form submission
    $('#edit-product-form').submit(function(e) {
        e.preventDefault();
        const form = $(this);
        const productId = form.find('#edit-product-id').val();
        
        const formData = new FormData(this);
        
        // Show loading state
        Swal.fire({
            title: 'Updating Product',
            text: 'Please wait...',
            allowOutsideClick: false,
            showConfirmButton: false,
            willOpen: () => {
                Swal.showLoading();
            }
        });
        
        $.ajax({
            url: `/admin/products/${productId}/update/`,
            type: 'POST',
            data: formData,
            processData: false,
            contentType: false,
            headers: {
                'X-CSRFToken': getCsrfToken()
            },
            success: function(response) {
                if (response.success) {
                    showNotification('success', 'Product updated successfully');
                    $('#editProductModal').modal('hide');
                    // Reload page to show updated data
                    location.reload();
                }
            },
            error: function(xhr) {
                Swal.close();
                showNotification('error', 'Failed to update product');
            }
        });
    });

    // Utility function to get CSRF token
    function getCsrfToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]').value;
    }

    // Show notification using SweetAlert2
    function showNotification(type, message) {
        const Toast = Swal.mixin({
            toast: true,
            position: 'top-end',
            showConfirmButton: false,
            timer: 3000,
            timerProgressBar: true,
            didOpen: (toast) => {
                toast.addEventListener('mouseenter', Swal.stopTimer);
                toast.addEventListener('mouseleave', Swal.resumeTimer);
            }
        });

        Toast.fire({
            icon: type,
            title: message
        });
    }
});
