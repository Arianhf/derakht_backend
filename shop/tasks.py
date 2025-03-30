# shop/tasks.py

from django.utils import timezone
from datetime import timedelta
from django.db import transaction

from .models.cart import Cart


def cleanup_expired_carts():
    """
    Clean up anonymous carts that have been inactive for more than 30 days
    """
    expiry_date = timezone.now() - timedelta(days=30)

    with transaction.atomic():
        # Delete anonymous carts that haven't been used for 30 days
        Cart.objects.filter(user__isnull=True, last_activity__lt=expiry_date).delete()
