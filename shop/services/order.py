# shop/services/order.py
from typing import Dict, Any, Optional
from decimal import Decimal
from django.db import transaction
from django.contrib.auth import get_user_model

from core.logging_utils import get_logger
from shop.models.cart import Cart
from shop.models.order import Order, OrderItem, ShippingInfo
from shop.choices import OrderStatus

logger = get_logger(__name__)
User = get_user_model()


class OrderService:
    """Business logic for order operations"""

    @staticmethod
    @transaction.atomic
    def create_from_cart(
        cart: Cart,
        shipping_info: Dict[str, Any],
        shipping_method_id: str,
        shipping_cost: Decimal,
        user: Optional[User] = None,
        notes: str = ''
    ) -> Order:
        """
        Create order from cart with shipping information

        Args:
            cart: The cart to create order from
            shipping_info: Dictionary with shipping details (address, city, province, etc.)
            shipping_method_id: ID of selected shipping method
            shipping_cost: Calculated shipping cost
            user: User placing order (optional for anonymous orders)
            notes: Optional order notes

        Returns:
            Created Order instance

        Raises:
            ValueError: If cart is empty or validation fails
        """
        # Validate cart not empty
        cart_items = cart.items.select_related('product').all()
        if not cart_items:
            raise ValueError("Cart is empty")

        # Calculate totals
        items_total = cart.total_amount
        total_amount = items_total + shipping_cost

        # Get phone number from shipping info
        phone_number = shipping_info.get("phone_number", "")

        # Create order
        order = Order.objects.create(
            user=user,
            total_amount=total_amount,
            phone_number=phone_number,
            status=OrderStatus.PENDING,
            shipping_method=shipping_method_id,
            shipping_cost=shipping_cost,
            notes=notes,
        )

        # Create shipping info
        ShippingInfo.objects.create(
            order=order,
            address=shipping_info["address"],
            city=shipping_info["city"],
            province=shipping_info["province"],
            postal_code=shipping_info["postal_code"],
            recipient_name=shipping_info["recipient_name"],
            phone_number=phone_number,
        )

        # Create order items using bulk_create
        order_items = [
            OrderItem(
                order=order,
                product=item.product,
                quantity=item.quantity,
                price=item.product.price,
            )
            for item in cart_items
        ]
        OrderItem.objects.bulk_create(order_items)

        # Clear cart after successful order creation
        cart.items.all().delete()

        # Update promo code usage if applicable
        if cart.promo_code:
            cart.promo_code.used_count += 1
            cart.promo_code.save()

            # Store promo info in order (if needed for future reference)
            order.promo_code = cart.promo_code
            order.discount_amount = cart.discount_amount or Decimal('0')
            order.save()

        logger.info(
            "Order created from cart",
            extra={"extra_data": {
                "order_id": str(order.id),
                "cart_id": str(cart.id),
                "user_id": str(user.id) if user else None,
                "total": float(total_amount),
                "items_count": len(cart_items),
            }}
        )

        return order

    @staticmethod
    def calculate_total(order: Order) -> Decimal:
        """
        Recalculate order total from items

        Args:
            order: The order to calculate total for

        Returns:
            Total amount as Decimal
        """
        from django.db.models import Sum, F

        subtotal = order.items.aggregate(
            total=Sum(F('quantity') * F('price'))
        )['total'] or Decimal('0')

        discount = order.discount_amount or Decimal('0')
        shipping = order.shipping_cost or Decimal('0')

        total = subtotal - discount + shipping
        return total

    @staticmethod
    def update_status(order: Order, new_status: str, notes: str = '') -> Order:
        """
        Update order status with validation

        Args:
            order: The order to update
            new_status: New status value
            notes: Optional notes about status change

        Returns:
            Updated Order instance

        Raises:
            ValueError: If status transition is invalid
        """
        old_status = order.status

        # Validate status transition (you can add more complex validation here)
        valid_transitions = {
            OrderStatus.PENDING: [OrderStatus.PROCESSING, OrderStatus.CANCELLED],
            OrderStatus.PROCESSING: [OrderStatus.CONFIRMED, OrderStatus.CANCELLED],
            OrderStatus.CONFIRMED: [OrderStatus.SHIPPED, OrderStatus.CANCELLED],
            OrderStatus.SHIPPED: [OrderStatus.DELIVERED, OrderStatus.RETURNED],
            OrderStatus.DELIVERED: [OrderStatus.RETURNED],
        }

        if old_status in valid_transitions and new_status not in valid_transitions[old_status]:
            raise ValueError(
                f"Invalid status transition from {old_status} to {new_status}"
            )

        # Update status
        order.status = new_status
        if notes:
            order.notes = f"{order.notes}\n{notes}" if order.notes else notes
        order.save()

        logger.info(
            "Order status updated",
            extra={"extra_data": {
                "order_id": str(order.id),
                "old_status": old_status,
                "new_status": new_status,
                "notes": notes,
            }}
        )

        return order
