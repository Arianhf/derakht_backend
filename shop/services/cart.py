# shop/services/cart.py

from typing import Optional

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from ..models import Order, OrderItem, Product

User = get_user_model()


class CartService:
    def __init__(self, user=None):
        self.user = user
        self._cart = None

    @property
    def cart(self) -> Optional[Order]:
        """Get or create cart for user"""
        if self._cart is None and self.user is not None:
            self._cart, _ = Order.objects.get_or_create_cart(self.user)
        return self._cart

    def add_item(self, product: Product, quantity: int = 1) -> OrderItem:
        """Add item to cart"""
        if not self.cart:
            raise ValidationError(_('Cannot add item to cart without user'))

        if not product.is_available:
            raise ValidationError(_('Product is not available'))

        if product.stock < quantity:
            raise ValidationError(_('Not enough stock available'))

        cart_item, created = OrderItem.objects.get_or_create(
            order=self.cart,
            product=product,
            defaults={'quantity': 0, 'price': product.price}
        )

        # Update quantity
        cart_item.quantity = cart_item.quantity + quantity
        if cart_item.quantity > product.stock:
            raise ValidationError(_('Not enough stock available'))

        cart_item.price = product.price  # Update to current price
        cart_item.save()

        return cart_item

    def remove_item(self, product: Product) -> None:
        """Remove item from cart"""
        if not self.cart:
            return

        OrderItem.objects.filter(
            order=self.cart,
            product=product
        ).delete()

    def update_quantity(self, product: Product, quantity: int) -> OrderItem:
        """Update item quantity in cart"""
        if not self.cart:
            raise ValidationError(_('Cannot update cart without user'))

        if quantity < 0:
            raise ValidationError(_('Quantity cannot be negative'))

        if quantity == 0:
            self.remove_item(product)
            return None

        if not product.is_available:
            raise ValidationError(_('Product is not available'))

        if product.stock < quantity:
            raise ValidationError(_('Not enough stock available'))

        cart_item, created = OrderItem.objects.get_or_create(
            order=self.cart,
            product=product,
            defaults={'quantity': quantity, 'price': product.price}
        )

        if not created:
            cart_item.quantity = quantity
            cart_item.price = product.price  # Update to current price
            cart_item.save()

        return cart_item

    def clear(self) -> None:
        """Clear cart"""
        if self.cart:
            self.cart.items.all().delete()
            self.cart.calculate_total()

    def get_cart_details(self) -> dict:
        """Get cart details"""
        if not self.cart:
            return {
                'items_count': 0,
                'total_amount': 0,
                'items': []
            }

        return {
            'items_count': self.cart.items.count(),
            'total_amount': self.cart.total_amount,
            'items': [
                {
                    'product': item.product,
                    'quantity': item.quantity,
                    'price': item.price,
                    'total': item.get_total_price()
                }
                for item in self.cart.items.all()
            ]
        }

    def checkout(self, shipping_address: str, phone_number: str) -> Order:
        """Checkout cart"""
        if not self.cart:
            raise ValidationError(_('Cannot checkout empty cart'))

        if not self.cart.items.exists():
            raise ValidationError(_('Cannot checkout empty cart'))

        # Validate stock availability
        for item in self.cart.items.all():
            if item.product.stock < item.quantity:
                raise ValidationError(
                    _('Not enough stock available for %(product)s') % {
                        'product': item.product.title
                    }
                )

        # Update cart to order
        self.cart.status = OrderStatus.PENDING
        self.cart.shipping_address = shipping_address
        self.cart.phone_number = phone_number
        self.cart.save()

        # Update product stock
        for item in self.cart.items.all():
            item.product.stock -= item.quantity
            item.product.save()

        # Create new cart
        self._cart = None

        return self.cart
