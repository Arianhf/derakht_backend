"""
Factory Boy factories for shop app models.
Provides easy creation of test data with realistic defaults.
"""

import factory
from factory.django import DjangoModelFactory
from decimal import Decimal
from django.contrib.auth import get_user_model
from faker import Faker
import uuid

from shop.models import (
    Category,
    Product,
    ProductImage,
    Cart,
    CartItem,
    Order,
    OrderItem,
    ShippingInfo,
    Payment,
    PaymentTransaction,
    Invoice,
    InvoiceItem,
    PromoCode,
    PaymentInfo,
)

User = get_user_model()
fake = Faker()


# ============================================================================
# USER FACTORY (for shop tests)
# ============================================================================


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User

    email = factory.Sequence(lambda n: f"user{n}@example.com")
    name = factory.Faker("name")
    phone_number = "+989123456789"
    age = factory.Faker("random_int", min=18, max=80)
    is_active = True

    @factory.post_generation
    def password(obj, create, extracted, **kwargs):
        if create:
            obj.set_password(extracted or "testpass123")
            obj.save()


# ============================================================================
# PRODUCT & CATEGORY FACTORIES
# ============================================================================


class CategoryFactory(DjangoModelFactory):
    class Meta:
        model = Category

    name = factory.Faker("word")
    slug = factory.LazyAttribute(lambda obj: f"{obj.name.lower()}-{uuid.uuid4().hex[:6]}")
    description = factory.Faker("paragraph")
    parent = None
    is_active = True

    @factory.post_generation
    def with_subcategory(obj, create, extracted, **kwargs):
        """
        Usage: CategoryFactory(with_subcategory=True)
        """
        if extracted and create:
            CategoryFactory(parent=obj)


class ProductFactory(DjangoModelFactory):
    class Meta:
        model = Product

    title = factory.Faker("sentence", nb_words=4)
    slug = factory.LazyAttribute(lambda obj: f"{obj.title[:30].lower().replace(' ', '-')}-{uuid.uuid4().hex[:6]}")
    description = factory.Faker("paragraph")
    price = factory.Faker("pydecimal", left_digits=4, right_digits=2, positive=True, min_value=1000)
    stock = factory.Faker("random_int", min=0, max=100)
    sku = factory.Sequence(lambda n: f"SKU{n:06d}")
    is_available = True
    is_active = True
    age_min = factory.Faker("random_int", min=3, max=10)
    age_max = factory.LazyAttribute(lambda obj: obj.age_min + fake.random_int(min=2, max=8))

    category = factory.SubFactory(CategoryFactory)

    @factory.post_generation
    def images(obj, create, extracted, **kwargs):
        """
        Usage: ProductFactory(images=3)  # Creates product with 3 images
        """
        if create and extracted:
            for i in range(extracted):
                ProductImageFactory(product=obj, is_featured=(i == 0))


class ProductImageFactory(DjangoModelFactory):
    class Meta:
        model = ProductImage

    product = factory.SubFactory(ProductFactory)
    # Note: Wagtail images require more complex setup, so we'll skip the actual image field
    # In real tests, you'd mock the image or use django.core.files.uploadedfile.SimpleUploadedFile
    alt_text = factory.Faker("sentence", nb_words=5)
    is_featured = False


# ============================================================================
# CART FACTORIES
# ============================================================================


class CartFactory(DjangoModelFactory):
    class Meta:
        model = Cart

    user = factory.SubFactory(UserFactory)
    anonymous_id = None
    is_active = True

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """
        Ensure either user or anonymous_id is set (but not both).
        """
        if "anonymous" in kwargs and kwargs.pop("anonymous"):
            kwargs["user"] = None
            kwargs["anonymous_id"] = str(uuid.uuid4())
        return super()._create(model_class, *args, **kwargs)


class CartItemFactory(DjangoModelFactory):
    class Meta:
        model = CartItem

    cart = factory.SubFactory(CartFactory)
    product = factory.SubFactory(ProductFactory)
    quantity = factory.Faker("random_int", min=1, max=5)


# ============================================================================
# ORDER FACTORIES
# ============================================================================


class OrderFactory(DjangoModelFactory):
    class Meta:
        model = Order

    user = factory.SubFactory(UserFactory)
    status = "PENDING"
    total_amount = Decimal("0.00")  # Will be calculated by signals
    promo_code = None
    discount_amount = Decimal("0.00")
    is_active = True

    @factory.post_generation
    def items(obj, create, extracted, **kwargs):
        """
        Usage: OrderFactory(items=3)  # Creates order with 3 items
        """
        if create and extracted:
            for _ in range(extracted):
                OrderItemFactory(order=obj)

    @factory.post_generation
    def with_shipping(obj, create, extracted, **kwargs):
        """
        Usage: OrderFactory(with_shipping=True)
        """
        if create and extracted:
            ShippingInfoFactory(order=obj)

    @factory.post_generation
    def with_payment_info(obj, create, extracted, **kwargs):
        """
        Usage: OrderFactory(with_payment_info=True)
        """
        if create and extracted:
            PaymentInfoFactory(order=obj)


class OrderItemFactory(DjangoModelFactory):
    class Meta:
        model = OrderItem

    order = factory.SubFactory(OrderFactory)
    product = factory.SubFactory(ProductFactory)
    quantity = factory.Faker("random_int", min=1, max=3)
    price = factory.LazyAttribute(lambda obj: obj.product.price)


class ShippingInfoFactory(DjangoModelFactory):
    class Meta:
        model = ShippingInfo

    order = factory.SubFactory(OrderFactory)
    recipient_name = factory.Faker("name")
    address = factory.Faker("address")
    city = factory.Faker("city")
    province = factory.Faker("state")
    postal_code = factory.Faker("postcode")
    phone_number = "+989123456789"


class PaymentInfoFactory(DjangoModelFactory):
    class Meta:
        model = PaymentInfo

    order = factory.SubFactory(OrderFactory)
    payment_method = "ONLINE"
    status = "PENDING"


# ============================================================================
# PAYMENT FACTORIES
# ============================================================================


class PaymentFactory(DjangoModelFactory):
    class Meta:
        model = Payment

    order = factory.SubFactory(OrderFactory)
    amount = factory.LazyAttribute(lambda obj: obj.order.total_amount)
    gateway = "ZARINPAL"
    status = "PENDING"
    reference_id = None
    transaction_id = None


class PaymentTransactionFactory(DjangoModelFactory):
    class Meta:
        model = PaymentTransaction

    payment = factory.SubFactory(PaymentFactory)
    gateway = "ZARINPAL"
    authority = factory.LazyAttribute(lambda obj: f"A{uuid.uuid4().hex[:35].upper()}")
    status = "PENDING"
    raw_request = factory.Faker("json")
    raw_response = factory.Faker("json")


# ============================================================================
# INVOICE FACTORIES
# ============================================================================


class InvoiceFactory(DjangoModelFactory):
    class Meta:
        model = Invoice

    order = factory.SubFactory(OrderFactory)
    invoice_number = factory.Sequence(lambda n: f"INV{n:06d}")
    total_amount = factory.LazyAttribute(lambda obj: obj.order.total_amount)

    @factory.post_generation
    def items(obj, create, extracted, **kwargs):
        """
        Usage: InvoiceFactory(items=3)
        """
        if create and extracted:
            for _ in range(extracted):
                InvoiceItemFactory(invoice=obj)


class InvoiceItemFactory(DjangoModelFactory):
    class Meta:
        model = InvoiceItem

    invoice = factory.SubFactory(InvoiceFactory)
    product_name = factory.Faker("product_name")
    quantity = factory.Faker("random_int", min=1, max=3)
    price = factory.Faker("pydecimal", left_digits=4, right_digits=2, positive=True)
    total_price = factory.LazyAttribute(lambda obj: obj.price * obj.quantity)


# ============================================================================
# PROMO CODE FACTORY
# ============================================================================


class PromoCodeFactory(DjangoModelFactory):
    class Meta:
        model = PromoCode

    code = factory.Sequence(lambda n: f"PROMO{n:04d}")
    discount_type = "PERCENTAGE"
    discount_value = Decimal("10.00")
    min_purchase_amount = Decimal("0.00")
    max_discount_amount = None
    usage_limit = None
    times_used = 0
    valid_from = factory.Faker("past_datetime", start_date="-30d")
    valid_until = factory.Faker("future_datetime", end_date="+30d")
    is_active = True


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def create_order_with_items(user=None, item_count=3, status="PENDING"):
    """
    Helper function to create a complete order with items.

    Usage:
        order = create_order_with_items(user=my_user, item_count=5)
    """
    if user is None:
        user = UserFactory()

    order = OrderFactory(user=user, status=status)

    for _ in range(item_count):
        product = ProductFactory(stock=10)
        OrderItemFactory(order=order, product=product, quantity=1)

    order.calculate_total()
    order.save()

    return order


def create_cart_with_items(user=None, item_count=2, anonymous=False):
    """
    Helper function to create a cart with items.

    Usage:
        cart = create_cart_with_items(user=my_user, item_count=3)
        anonymous_cart = create_cart_with_items(anonymous=True)
    """
    if anonymous:
        cart = CartFactory(anonymous=True)
    else:
        if user is None:
            user = UserFactory()
        cart = CartFactory(user=user)

    for _ in range(item_count):
        product = ProductFactory(stock=10, price=Decimal("100.00"))
        CartItemFactory(cart=cart, product=product, quantity=1)

    return cart


def create_payment_flow(order=None):
    """
    Helper to create a complete payment flow for testing.

    Returns: (order, payment, transaction)
    """
    if order is None:
        order = create_order_with_items(item_count=2)

    payment = PaymentFactory(order=order, amount=order.total_amount)
    transaction = PaymentTransactionFactory(payment=payment)

    return order, payment, transaction
