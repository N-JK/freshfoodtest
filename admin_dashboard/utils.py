from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
import logging

# Set up logging
logger = logging.getLogger(__name__)

def send_supplier_welcome_email(supplier, username, password):
    """
    Send a welcome email to the newly created supplier with their login credentials
    """
    try:
        # Log the attempt
        logger.info(f"Attempting to send welcome email to {supplier.user.email}")
        
        context = {
            'supplier': supplier,
            'username': username,
            'password': password,
            'login_url': settings.SITE_URL + '/seller/login/'  # Updated URL to match your login path
        }
        
        # Log the context (excluding password)
        log_context = context.copy()
        log_context['password'] = '******'
        logger.info(f"Email context: {log_context}")
        
        # Render the HTML email template
        try:
            html_message = render_to_string('admin_dashboard/emails/supplier_welcome.html', context)
            plain_message = strip_tags(html_message)
            logger.info("Email template rendered successfully")
        except Exception as e:
            logger.error(f"Error rendering email template: {str(e)}")
            raise
        
        # Send the email
        try:
            send_mail(
                subject='Welcome to Home Fresh - Your Supplier Account Details',
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[supplier.user.email],
                html_message=html_message,
                fail_silently=False,
            )
            logger.info(f"Welcome email sent successfully to {supplier.user.email}")
        except Exception as e:
            logger.error(f"Error sending email: {str(e)}")
            raise

    except Exception as e:
        logger.error(f"Failed to send welcome email: {str(e)}")
        raise
