# shop/services/cart.py
from typing import Tuple, Optional
from decimal import Decimal
from uuid import UUID
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Sum, F

from core.logging_utils import get_logger
from shop.models.cart import Cart, CartItem
from shop.models.product import Product
from shop.models.promo import PromoCode

logger = get_logger(__name__)
User = get_user_model()


class CartService:
    """Business logic for cart operations"""

    @staticmethod
    def get_or_create_cart(
        user: Optional[User] = None,
        anonymous_id: Optional[UUID] = None
    ) -> Tuple[Cart, bool]:
        """
        Get or create cart for user or anonymous session

        Args:
            user: Authenticated user (optional)
            anonymous_id: Anonymous cart ID (optional)

        Returns:
            Tuple of (Cart, created_flag)

        Raises:
            ValueError: If neither user nor anonymous_id is provided
        """
        if user and user.is_authenticated:
            cart, created = Cart.objects.get_or_create(
                user=user,
                defaults={"anonymous_id": None}
            )
            logger.info(
                "Cart retrieved for authenticated user",
                extra={"extra_data": {
                    "cart_id": str(cart.id),
                    "user_id": str(user.id),
                    "created": created,
                }}
            )
        elif anonymous_id:
            cart, created = Cart.objects.get_or_create(
                anonymous_id=anonymous_id,
                user=None
            )
            logger.info(
                "Cart retrieved for anonymous user",
                extra={"extra_data": {
                    "cart_id": str(cart.id),
                    "anonymous_id": str(anonymous_id),
                    "created": created,
                }}
            )
        else:
            raise ValueError("Either user or anonymous_id required")

        return cart, created

    @staticmethod
    def add_item(cart: Cart, product: Product, quantity: int) -> CartItem:
        """
        Add or update product in cart

        Args:
            cart: The cart to add item to
            product: The product to add
            quantity: Quantity to add

        Returns:
            CartItem instance

        Raises:
            ValueError: If product unavailable, insufficient stock, or invalid quantity
        """
        if not product.is_available:
            raise ValueError("Product is not available")

        if quantity < 1:
            raise ValueError("Quantity must be positive")

        # Check stock
        if product.stock < quantity:
            raise ValueError(f"Only {product.stock} items available")

        # Get or create cart item
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={'quantity': quantity}
        )

        # If item exists, update quantity
        if not created:
            new_quantity = cart_item.quantity + quantity
            if new_quantity > product.stock:
                raise ValueError(f"Only {product.stock} items available")
            cart_item.quantity = new_quantity
            cart_item.save()

        logger.info(
            "Item added to cart",
            extra={"extra_data": {
                "cart_id": str(cart.id),
                "product_id": str(product.id),
                "product_title": product.title,
                "quantity": quantity,
                "created": created,
            }}
        )

        return cart_item

    @staticmethod
    def update_quantity(cart: Cart, product: Product, quantity: int) -> Optional[CartItem]:
        """
        Update item quantity in cart

        Args:
            cart: The cart containing the item
            product: The product to update
            quantity: New quantity (0 to remove)

        Returns:
            CartItem instance or None if removed

        Raises:
            ValueError: If product unavailable, insufficient stock, or negative quantity
            CartItem.DoesNotExist: If item not in cart
        """
        if quantity < 0:
            raise ValueError("Quantity cannot be negative")

        cart_item = CartItem.objects.get(cart=cart, product=product)

        # Remove item if quantity is 0
        if quantity == 0:
            cart_item.delete()
            logger.info(
                "Item removed from cart",
                extra={"extra_data": {
                    "cart_id": str(cart.id),
                    "product_id": str(product.id),
                }}
            )
            return None

        # Validate product availability
        if not product.is_available:
            raise ValueError("Product is not available")

        # Check stock
        if product.stock < quantity:
            raise ValueError(f"Only {product.stock} items available")

        # Update quantity
        cart_item.quantity = quantity
        cart_item.save()

        logger.info(
            "Cart item quantity updated",
            extra={"extra_data": {
                "cart_id": str(cart.id),
                "product_id": str(product.id),
                "new_quantity": quantity,
            }}
        )

        return cart_item

    @staticmethod
    def apply_promo_code(cart: Cart, code: str) -> Tuple[PromoCode, Decimal]:
        """
        Apply promo code and return discount amount

        Args:
            cart: The cart to apply promo to
            code: Promo code string

        Returns:
            Tuple of (PromoCode, discount_amount)

        Raises:
            ValueError: If promo code invalid, expired, usage limit reached, or minimum purchase not met
        """
        try:
            promo = PromoCode.objects.get(
                code=code,
                is_active=True,
                valid_from__lte=timezone.now(),
                valid_to__gte=timezone.now()
            )
        except PromoCode.DoesNotExist:
            logger.warning(
                f"Invalid promo code attempt: {code}",
                extra={"extra_data": {"code": code, "cart_id": str(cart.id)}}
            )
            raise ValueError("Invalid or expired promo code")

        # Validate usage limits
        if promo.max_uses and promo.used_count >= promo.max_uses:
            logger.warning(
                "Promo code usage limit exceeded",
                extra={"extra_data": {
                    "code": code,
                    "max_uses": promo.max_uses,
                    "used_count": promo.used_count,
                }}
            )
            raise ValueError("This promo code has reached its usage limit")

        # Calculate cart total
        total_amount = CartService.calculate_total(cart)

        # Validate minimum purchase
        if total_amount < promo.min_purchase:
            logger.warning(
                "Promo code minimum purchase not met",
                extra={"extra_data": {
                    "code": code,
                    "min_purchase": float(promo.min_purchase),
                    "current_total": float(total_amount),
                }}
            )
            raise ValueError(
                f"Minimum purchase of {promo.min_purchase} required"
            )

        # Calculate discount
        if promo.discount_type == "percentage":
            discount_amount = total_amount * (Decimal(promo.discount_value) / Decimal(100))
        else:  # fixed
            discount_amount = Decimal(promo.discount_value)

        # Apply to cart
        cart.promo_code = promo
        cart.discount_amount = discount_amount
        cart.save()

        logger.info(
            "Promo code applied",
            extra={"extra_data": {
                "cart_id": str(cart.id),
                "promo_code": code,
                "discount": float(discount_amount),
            }}
        )

        return promo, discount_amount

    @staticmethod
    def calculate_total(cart: Cart) -> Decimal:
        """
        Calculate cart total using database aggregation

        Args:
            cart: The cart to calculate total for

        Returns:
            Total amount as Decimal
        """
        total = cart.items.aggregate(
            total=Sum(F('quantity') * F('product__price'))
        )['total'] or Decimal('0')

        discount = cart.discount_amount or Decimal('0')
        return total - discount

    @staticmethod
    def clear_cart(cart: Cart) -> None:
        """
        Clear all items from cart

        Args:
            cart: The cart to clear
        """
        cart.items.all().delete()
        cart.promo_code = None
        cart.discount_amount = Decimal('0')
        cart.save()

        logger.info(
            "Cart cleared",
            extra={"extra_data": {"cart_id": str(cart.id)}}
        )
