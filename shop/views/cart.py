# shop/views/cart.py

from typing import Tuple, Optional, Any
from uuid import UUID
from django.utils import timezone
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
import uuid

from core.logging_utils import get_logger
from ..choices import OrderStatus
from ..models.cart import Cart, CartItem
from ..models.product import Product
from ..models.promo import PromoCode
from ..models.order import Order, OrderItem, ShippingInfo
from ..serializers.cart import (
    CartDetailsSerializer,
    CartItemSerializer,
    AddCartItemSerializer,
    UpdateCartItemSerializer,
    RemoveCartItemSerializer,
)
from ..serializers.order import OrderSerializer
from ..serializers.shipping import (
    ShippingEstimateRequestSerializer,
    ShippingEstimateResponseSerializer,
)
from ..services.shipping import ShippingCalculator
from ..services.order import OrderService
from ..services.cart import CartService

# Initialize logger
logger = get_logger(__name__)


class CartViewSet(viewsets.ViewSet):
    """
    API endpoint for shopping cart with support for both authenticated and anonymous users
    """

    permission_classes = (permissions.AllowAny,)

    def get_cart(self, request: Request, anonymous_cart_id: Optional[UUID] = None) -> Tuple[Cart, bool]:
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
    def details(self, request: Request) -> Response:
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

        # Optimize queries to prevent N+1 issues
        cart_items = cart.items.select_related(
            "product__category"
        ).prefetch_related(
            "product__images"
        ).all()

        data = {
            "cart_id": str(cart.anonymous_id) if cart.anonymous_id else None,
            "is_authenticated": request.user.is_authenticated,
            "items_count": cart.items_count,
            "total_amount": cart.total_amount,
            "items": cart_items,
            "applied_promo": None,
            "shipping_cost": 0,
        }

        serializer = CartDetailsSerializer(data)
        return Response(serializer.data)

    @action(detail=False, methods=["post"])
    def add_item(self, request: Request) -> Response:
        """
        Add item to cart
        """
        serializer = AddCartItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        product_id = serializer.validated_data["product_id"]
        quantity = serializer.validated_data["quantity"]
        anonymous_cart_id = serializer.validated_data.get("anonymous_cart_id")

        product = get_object_or_404(Product, id=product_id)

        # Get the appropriate cart
        cart, created = self.get_cart(request, anonymous_cart_id)

        try:
            # Use CartService to add item
            CartService.add_item(cart, product, quantity)
        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        # Get updated cart details
        return self.details(request)

    @action(detail=False, methods=["post"])
    def update_quantity(self, request: Request) -> Response:
        """
        Update item quantity in cart
        """
        serializer = UpdateCartItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        product_id = serializer.validated_data["product_id"]
        quantity = serializer.validated_data["quantity"]
        anonymous_cart_id = serializer.validated_data.get("anonymous_cart_id")

        # Get the appropriate cart
        cart, created = self.get_cart(request, anonymous_cart_id)

        # Get the product
        product = get_object_or_404(Product, id=product_id)

        try:
            # Use CartService to update quantity
            CartService.update_quantity(cart, product, quantity)
        except CartItem.DoesNotExist:
            return Response(
                {"error": "Item not found in cart"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        # Get updated cart details
        return self.details(request)

    @action(detail=False, methods=["post"])
    def remove_item(self, request: Request) -> Response:
        """
        Remove item from cart
        """
        serializer = RemoveCartItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        product_id = serializer.validated_data["product_id"]
        anonymous_cart_id = serializer.validated_data.get("anonymous_cart_id")

        # Get the appropriate cart
        cart, created = self.get_cart(request, anonymous_cart_id)

        # Get the product
        product = get_object_or_404(Product, id=product_id)

        # Remove cart item
        CartItem.objects.filter(cart=cart, product=product).delete()

        # Get updated cart details
        return self.details(request)

    @action(detail=False, methods=["post"])
    def clear(self, request: Request) -> Response:
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
    def merge(self, request: Request) -> Response:
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
        # Add items from anonymous cart to user cart with optimized query
        for anon_item in anonymous_cart.items.select_related("product").all():
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

    @action(detail=False, methods=["post"], url_path="shipping-estimate")
    def shipping_estimate(self, request: Request) -> Response:
        """
        Get shipping methods estimate for given location and cart
        """
        serializer = ShippingEstimateRequestSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        province = serializer.validated_data["province"]
        city = serializer.validated_data["city"]
        cart_id = serializer.validated_data.get("cart_id")

        # Try to convert cart_id to UUID if provided
        anonymous_cart_id = None
        if cart_id:
            try:
                anonymous_cart_id = uuid.UUID(str(cart_id))
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
                {
                    "code": "EMPTY_CART",
                    "message": "سبد خرید خالی است",
                    "severity": "error",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get cart total
        cart_total = cart.total_amount

        # Get available shipping methods
        shipping_methods = ShippingCalculator.get_shipping_methods(
            province, city, cart_total
        )

        # Prepare response
        response_data = {
            "shipping_methods": shipping_methods,
            "cart_total": cart_total,
            "free_shipping_threshold": ShippingCalculator.FREE_SHIPPING_THRESHOLD,
            "message": f"ارسال رایگان برای سفارش‌های بالای {ShippingCalculator.FREE_SHIPPING_THRESHOLD:,} تومان",
        }

        response_serializer = ShippingEstimateResponseSerializer(response_data)
        return Response(response_serializer.data)

    @action(detail=False, methods=["post"])
    def checkout(self, request: Request) -> Response:
        """
        Checkout and create order
        """
        shipping_info = request.data.get("shipping_info")
        shipping_method_id = request.data.get("shipping_method_id")
        anonymous_cart_id = request.data.get("anonymous_cart_id")

        if not shipping_info:
            return Response(
                {"error": "Shipping info is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not shipping_method_id:
            return Response(
                {"error": "Shipping method is required"},
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

        # Get province from shipping info for validation
        province = shipping_info.get("province")
        if not province:
            return Response(
                {"error": "Province is required in shipping info"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate shipping method
        is_valid, error_message = ShippingCalculator.validate_shipping_method(
            shipping_method_id, province
        )
        if not is_valid:
            return Response({"error": error_message}, status=status.HTTP_400_BAD_REQUEST)

        # Calculate total amount and shipping cost
        items_total = cart.total_amount
        try:
            shipping_cost = ShippingCalculator.calculate_shipping_cost(
                shipping_method_id, province, items_total
            )
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # Create order using OrderService
        try:
            order = OrderService.create_from_cart(
                cart=cart,
                shipping_info=shipping_info,
                shipping_method_id=shipping_method_id,
                shipping_cost=shipping_cost,
                user=request.user if request.user.is_authenticated else None,
            )
        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Return order details
        serializer = OrderSerializer(order)
        return Response(serializer.data)

    @action(detail=False, methods=["post"])
    def apply_promo(self, request: Request) -> Response:
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
            # Use CartService to apply promo code
            promo, discount_amount = CartService.apply_promo_code(cart, code)
        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Store promo code in session
        request.session["applied_promo"] = {
            "code": promo.code,
            "discount_amount": float(discount_amount),
        }

        # Get updated cart details with promo applied
        cart_items_with_promo = cart.items.select_related(
            "product__category"
        ).prefetch_related(
            "product__images"
        ).all()

        total_amount = CartService.calculate_total(cart)

        data = {
            "cart_id": str(cart.anonymous_id) if cart.anonymous_id else None,
            "is_authenticated": request.user.is_authenticated,
            "items_count": cart.items_count,
            "total_amount": total_amount,
            "items": cart_items_with_promo,
            "applied_promo": {"code": promo.code, "discount_amount": float(discount_amount)},
            "shipping_cost": 0,
        }

        serializer = CartDetailsSerializer(data)
        return Response(
            {
                "success": True,
                "message": "Promo code applied",
                "discount_amount": float(discount_amount),
                "cart": serializer.data,
            }
        )
