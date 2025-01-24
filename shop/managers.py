from django.db import models
from django.db.models import Sum

from .choices import OrderStatus


class OrderManager(models.Manager):
    def get_active_cart(self, user):
        """Get user's active cart or create one"""
        cart, created = self.get_or_create(
            user=user,
            status=OrderStatus.CART,
            defaults={
                'currency': Currency.IRR
            }
        )
        return cart

    def get_user_orders(self, user):
        """Get all completed orders for a user"""
        return self.filter(
            user=user
        ).exclude(
            status=OrderStatus.CART
        ).order_by('-created_at')


class CartManager(models.Manager):
    def get_or_create_cart(self, user=None):
        """Get active cart or create new one"""
        if user and user.is_authenticated:
            cart, created = self.get_or_create(
                user=user,
                status=OrderStatus.CART,
                defaults={'currency': 'IRR'}
            )
        else:
            cart = None
            created = False
        return cart, created

    def get_cart_total_items(self, cart):
        """Get total number of items in cart"""
        return cart.items.aggregate(
            total_items=Sum('quantity')
        )['total_items'] or 0
