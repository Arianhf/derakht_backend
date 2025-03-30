# shop/views/cart.py

from django.utils import timezone
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
import uuid

from ..choices import OrderStatus
from ..models.cart import Cart, CartItem
from ..models.product import Product
from ..models.promo import PromoCode
from ..models.order import Order, OrderItem, ShippingInfo
from ..serializers.cart import CartDetailsSerializer, CartItemSerializer
from ..serializers.order import OrderSerializer


class CartViewSet(viewsets.ViewSet):
    """
    API endpoint for shopping cart with support for both authenticated and anonymous users
    """

    permission_classes = (permissions.AllowAny,)

    def get_cart(self, request, anonymous_cart_id=None):
        """
        Helper method to get the appropriate cart
        """
        # For authenticated users, get or create their cart
        if request.user.is_authenticated:
            cart, created = Cart.objects.get_or_create(
                user=request.user, defaults={"anonymous_id": None}
            )
            return cart, created

        # For anonymous users, try to find an existing cart or create a new one
        if not anonymous_cart_id:
            # Check header first
            header_cart_id = request.META.get("HTTP_X_ANONYMOUS_CART_ID")
            if header_cart_id:
                try:
                    anonymous_cart_id = uuid.UUID(header_cart_id)
                except (ValueError, TypeError):
                    pass

        if anonymous_cart_id:
            cart, created = Cart.objects.get_or_create(
                anonymous_id=anonymous_cart_id, user=None
            )
        else:
            # Generate a new anonymous ID
            new_anonymous_id = uuid.uuid4()
            cart = Cart.objects.create(anonymous_id=new_anonymous_id, user=None)
            created = True

        return cart, created

    @action(detail=False, methods=["get"])
    def details(self, request):
        """
        Get cart details
        """
        # Get cart_id from query parameters
        cart_id = request.query_params.get("cart_id")
        anonymous_id = None

        if cart_id:
            try:
                anonymous_id = uuid.UUID(cart_id)
            except (ValueError, TypeError):
                return Response(
                    {"error": "Invalid cart ID format"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        cart, created = self.get_cart(request, anonymous_id)

        data = {
            "cart_id": str(cart.anonymous_id) if cart.anonymous_id else None,
            "is_authenticated": request.user.is_authenticated,
            "items_count": cart.items_count,
            "total_amount": cart.total_amount,
            "items": cart.items.select_related("product").all(),
            "applied_promo": None,
            "shipping_cost": 0,
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
            anonymous_cart_id = serializer.validated_data.get("anonymous_cart_id")

            # Try to convert anonymous_cart_id to UUID if provided
            if anonymous_cart_id:
                try:
                    anonymous_cart_id = uuid.UUID(anonymous_cart_id)
                except (ValueError, TypeError):
                    return Response(
                        {"error": "Invalid cart ID format"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

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

            # Get the appropriate cart
            cart, created = self.get_cart(request, anonymous_cart_id)

            # Get or create cart item
            cart_item, item_created = CartItem.objects.get_or_create(
                cart=cart, product=product, defaults={"quantity": quantity}
            )

            # If cart item already exists, update quantity
            if not item_created:
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
        anonymous_cart_id = request.data.get("anonymous_cart_id")

        # Try to convert anonymous_cart_id to UUID if provided
        if anonymous_cart_id:
            try:
                anonymous_cart_id = uuid.UUID(anonymous_cart_id)
            except (ValueError, TypeError):
                return Response(
                    {"error": "Invalid cart ID format"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

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

        # Get the appropriate cart
        cart, created = self.get_cart(request, anonymous_cart_id)

        # Get the product
        product = get_object_or_404(Product, id=product_id)

        # If quantity is 0, remove the item
        if quantity == 0:
            CartItem.objects.filter(cart=cart, product=product).delete()
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
            cart=cart, product=product, defaults={"quantity": quantity}
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
        anonymous_cart_id = request.data.get("anonymous_cart_id")

        # Try to convert anonymous_cart_id to UUID if provided
        if anonymous_cart_id:
            try:
                anonymous_cart_id = uuid.UUID(anonymous_cart_id)
            except (ValueError, TypeError):
                return Response(
                    {"error": "Invalid cart ID format"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        if not product_id:
            return Response(
                {"error": "Product ID is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Get the appropriate cart
        cart, created = self.get_cart(request, anonymous_cart_id)

        # Get the product
        product = get_object_or_404(Product, id=product_id)

        # Remove cart item
        CartItem.objects.filter(cart=cart, product=product).delete()

        # Get updated cart details
        return self.details(request)

    @action(detail=False, methods=["post"])
    def clear(self, request):
        """
        Clear cart
        """
        anonymous_cart_id = request.data.get("anonymous_cart_id")

        # Try to convert anonymous_cart_id to UUID if provided
        if anonymous_cart_id:
            try:
                anonymous_cart_id = uuid.UUID(anonymous_cart_id)
            except (ValueError, TypeError):
                return Response(
                    {"error": "Invalid cart ID format"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # Get the appropriate cart
        cart, created = self.get_cart(request, anonymous_cart_id)

        # Clear cart items
        cart.items.all().delete()

        # Get updated cart details
        return self.details(request)

    @action(detail=False, methods=["post"])
    def merge(self, request):
        """
        Merge anonymous cart with user cart
        """
        # This endpoint requires authentication
        if not request.user.is_authenticated:
            return Response(
                {"error": "Authentication required"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        anonymous_cart_id = request.data.get("anonymous_cart_id")

        if not anonymous_cart_id:
            return Response(
                {"error": "Anonymous cart ID is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            anonymous_id = uuid.UUID(anonymous_cart_id)
        except (ValueError, TypeError):
            return Response(
                {"error": "Invalid cart ID format"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Get user cart
        user_cart, created = Cart.objects.get_or_create(
            user=request.user, defaults={"anonymous_id": None}
        )

        # Get anonymous cart
        try:
            anonymous_cart = Cart.objects.get(anonymous_id=anonymous_id, user=None)
        except Cart.DoesNotExist:
            return Response(
                {"error": "Anonymous cart not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # Clear cart first
        CartItem.objects.filter(cart__user=request.user).delete()
        # Add items from anonymous cart to user cart
        for anon_item in anonymous_cart.items.all():
            # Check if product already exists in user cart
            try:
                user_item = CartItem.objects.get(
                    cart=user_cart, product=anon_item.product
                )
                user_item.quantity = anon_item.quantity
                user_item.save()
            except CartItem.DoesNotExist:
                # Copy the item to user cart
                CartItem.objects.create(
                    cart=user_cart,
                    product=anon_item.product,
                    quantity=anon_item.quantity,
                )

        # Delete the anonymous cart
        anonymous_cart.delete()

        # Return the updated cart
        return self.details(request)

    @action(detail=False, methods=["post"])
    def checkout(self, request):
        """
        Checkout and create order
        """
        shipping_info = request.data.get("shipping_info")
        anonymous_cart_id = request.data.get("anonymous_cart_id")

        if not shipping_info:
            return Response(
                {"error": "Shipping info is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Try to convert anonymous_cart_id to UUID if provided
        if anonymous_cart_id:
            try:
                anonymous_cart_id = uuid.UUID(anonymous_cart_id)
            except (ValueError, TypeError):
                return Response(
                    {"error": "Invalid cart ID format"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # Get the appropriate cart
        cart, created = self.get_cart(request, anonymous_cart_id)

        # Check if cart has items
        if not cart.items.exists():
            return Response(
                {"error": "Your cart is empty"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Calculate total amount
        total_amount = cart.total_amount
        phone_number = shipping_info["phone_number"]

        # Create order
        order = Order.objects.create(
            user=request.user if request.user.is_authenticated else None,
            total_amount=total_amount,
            phone_number=phone_number,
            status=OrderStatus.PENDING,
        )

        # Create shipping info
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
        for cart_item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                product=cart_item.product,
                quantity=cart_item.quantity,
                price=cart_item.product.price,
            )

        # Clear cart after checkout
        cart.items.all().delete()

        # Return order details
        serializer = OrderSerializer(order)
        return Response(serializer.data)

    @action(detail=False, methods=["post"])
    def apply_promo(self, request):
        """
        Apply promo code to cart
        """
        code = request.data.get("code")
        anonymous_cart_id = request.data.get("anonymous_cart_id")

        if not code:
            return Response(
                {"error": "Promo code is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Try to convert anonymous_cart_id to UUID if provided
        if anonymous_cart_id:
            try:
                anonymous_cart_id = uuid.UUID(anonymous_cart_id)
            except (ValueError, TypeError):
                return Response(
                    {"error": "Invalid cart ID format"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # Get the appropriate cart
        cart, created = self.get_cart(request, anonymous_cart_id)

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

        total_amount = cart.total_amount

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
        data = {
            "cart_id": str(cart.anonymous_id) if cart.anonymous_id else None,
            "is_authenticated": request.user.is_authenticated,
            "items_count": cart.items_count,
            "total_amount": total_amount - discount_amount,
            "items": cart.items.select_related("product").all(),
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
