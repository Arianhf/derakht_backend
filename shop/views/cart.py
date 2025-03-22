# shop/views/cart.py
from django.utils import timezone
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from ..models import CartItem, Product, PromoCode, Order, OrderItem, ShippingInfo
from ..serializers.cart import CartDetailsSerializer, CartItemSerializer
from ..serializers.order import OrderSerializer


class CartViewSet(viewsets.ViewSet):
    """
    API endpoint for shopping cart
    """

    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=["get"])
    def details(self, request):
        """
        Get cart details
        """
        cart_items = CartItem.objects.filter(user=request.user).select_related(
            "product"
        )

        items_count = cart_items.count()
        total_amount = sum(item.total_price for item in cart_items)

        data = {
            "items_count": items_count,
            "total_amount": total_amount,
            "items": cart_items,
            "applied_promo": None,  # This would be implemented with session or a cart model
            "shipping_cost": 0,  # This would be calculated based on location, etc.
        }

        serializer = CartDetailsSerializer(data)
        return Response(serializer.data)

    @action(detail=False, methods=["post"])
    def add_item(self, request):
        """
        Add item to cart
        """
        serializer = CartItemSerializer(data=request.data)

        if serializer.is_valid():
            product_id = serializer.validated_data["product_id"]
            quantity = serializer.validated_data.get("quantity", 1)

            product = get_object_or_404(Product, id=product_id)

            # Check if product is available
            if not product.is_available:
                return Response(
                    {"error": "Product is not available"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Check if product is in stock
            if product.stock < quantity:
                return Response(
                    {"error": "Not enough stock available"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Get or create cart item
            cart_item, created = CartItem.objects.get_or_create(
                user=request.user, product=product, defaults={"quantity": quantity}
            )

            # If cart item already exists, update quantity
            if not created:
                cart_item.quantity += quantity
                if cart_item.quantity > product.stock:
                    return Response(
                        {"error": "Not enough stock available"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                cart_item.save()

            # Get updated cart details
            return self.details(request)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["post"])
    def update_quantity(self, request):
        """
        Update item quantity in cart
        """
        product_id = request.data.get("product_id")
        quantity = request.data.get("quantity", 1)

        try:
            quantity = int(quantity)
            if quantity < 0:
                return Response(
                    {"error": "Quantity cannot be negative"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except (ValueError, TypeError):
            return Response(
                {"error": "Invalid quantity"}, status=status.HTTP_400_BAD_REQUEST
            )

        if not product_id:
            return Response(
                {"error": "Product ID is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        product = get_object_or_404(Product, id=product_id)

        # If quantity is 0, remove the item
        if quantity == 0:
            CartItem.objects.filter(user=request.user, product=product).delete()
            return self.details(request)

        # Check if product is available
        if not product.is_available:
            return Response(
                {"error": "Product is not available"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check if product is in stock
        if product.stock < quantity:
            return Response(
                {"error": "Not enough stock available"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Update cart item
        cart_item, created = CartItem.objects.get_or_create(
            user=request.user, product=product, defaults={"quantity": quantity}
        )

        if not created:
            cart_item.quantity = quantity
            cart_item.save()

        # Get updated cart details
        return self.details(request)

    @action(detail=False, methods=["post"])
    def remove_item(self, request):
        """
        Remove item from cart
        """
        product_id = request.data.get("product_id")

        if not product_id:
            return Response(
                {"error": "Product ID is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        product = get_object_or_404(Product, id=product_id)

        # Remove cart item
        CartItem.objects.filter(user=request.user, product=product).delete()

        # Get updated cart details
        return self.details(request)

    @action(detail=False, methods=["post"])
    def clear(self, request):
        """
        Clear cart
        """
        CartItem.objects.filter(user=request.user).delete()

        # Get updated cart details (which will be empty)
        return self.details(request)

    @action(detail=False, methods=["post"])
    def apply_promo(self, request):
        """
        Apply promo code to cart
        """
        code = request.data.get("code")

        if not code:
            return Response(
                {"error": "Promo code is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            promo = PromoCode.objects.get(
                code=code,
                is_active=True,
                valid_from__lte=timezone.now(),
                valid_to__gte=timezone.now(),
            )
        except PromoCode.DoesNotExist:
            return Response(
                {"error": "Invalid or expired promo code"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check if max uses has been reached
        if promo.max_uses and promo.used_count >= promo.max_uses:
            return Response(
                {"error": "This promo code has reached its usage limit"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cart_items = CartItem.objects.filter(user=request.user).select_related(
            "product"
        )
        total_amount = sum(item.total_price for item in cart_items)

        # Check if minimum purchase requirement is met
        if total_amount < promo.min_purchase:
            return Response(
                {
                    "error": f"Minimum purchase of {promo.min_purchase} is required to use this promo code"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Calculate discount
        if promo.discount_type == "fixed":
            discount_amount = promo.discount_value
        else:  # percentage discount
            discount_amount = total_amount * (promo.discount_value / 100)

            # Apply maximum discount if applicable
            if promo.max_discount and discount_amount > promo.max_discount:
                discount_amount = promo.max_discount

        # Store promo code in session (or a Cart model if you have one)
        request.session["applied_promo"] = {
            "code": promo.code,
            "discount_amount": discount_amount,
        }

        # Get updated cart details with promo applied
        cart_items = CartItem.objects.filter(user=request.user).select_related(
            "product"
        )

        items_count = cart_items.count()
        total_amount = sum(item.total_price for item in cart_items)

        data = {
            "items_count": items_count,
            "total_amount": total_amount - discount_amount,
            "items": cart_items,
            "applied_promo": {"code": promo.code, "discount_amount": discount_amount},
            "shipping_cost": 0,  # This would be calculated based on location, etc.
        }

        serializer = CartDetailsSerializer(data)
        return Response(
            {
                "success": True,
                "message": "Promo code applied",
                "discount_amount": discount_amount,
                "cart": serializer.data,
            }
        )

    @action(detail=False, methods=["post"])
    def estimate_shipping(self, request):
        """
        Estimate shipping cost
        """
        postal_code = request.data.get("postal_code")

        if not postal_code:
            return Response(
                {"error": "Postal code is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        # This would normally involve a shipping calculator service
        # For now, return a static shipping cost
        shipping_cost = 30000

        return Response(
            {
                "success": True,
                "shipping_cost": shipping_cost,
                "estimated_delivery": "3-5 روز کاری",
            }
        )

    @action(detail=False, methods=["post"])
    def checkout(self, request):
        """
        Checkout and create order
        """
        shipping_info = request.data.get("shipping_info")

        if not shipping_info:
            return Response(
                {"error": "Shipping info is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get cart items
        cart_items = CartItem.objects.filter(user=request.user).select_related(
            "product"
        )

        if not cart_items.exists():
            return Response(
                {"error": "Your cart is empty"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Calculate total amount
        total_amount = sum(item.total_price for item in cart_items)
        phone_number = shipping_info["phone_number"]
        # Create order
        order = Order.objects.create(
            user=request.user,
            total_amount=total_amount,
            phone_number=phone_number,
        )

        ShippingInfo.objects.create(
            order=order,
            address=shipping_info["address"],
            city=shipping_info["city"],
            province=shipping_info["province"],
            postal_code=shipping_info["postal_code"],
            recipient_name=shipping_info["recipient_name"],
            phone_number=shipping_info["phone_number"],
        )

        # Create order items
        for cart_item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=cart_item.product,
                quantity=cart_item.quantity,
                price=cart_item.product.price,
            )

        # Clear cart after checkout
        cart_items.delete()

        # Return order details
        serializer = OrderSerializer(order)
        return Response(serializer.data)
