# shop/services/shipping.py

from typing import List, Dict, Any, Tuple

from ..choices import ShippingMethod


class ShippingCalculator:
    """Calculate shipping costs and availability based on location"""

    FREE_SHIPPING_THRESHOLD = 1_000_000
    STANDARD_COST_TEHRAN = 50_000
    STANDARD_COST_OTHER = 70_000
    EXPRESS_COST = 80_000
    TEHRAN_PROVINCE = "تهران"

    @classmethod
    def get_shipping_methods(cls, province: str, city: str, cart_total: int) -> List[Dict[str, Any]]:
        """
        Get available shipping methods with costs for the given location and cart total

        Args:
            province: Province name in Farsi
            city: City name in Farsi
            cart_total: Total cart amount

        Returns:
            List of shipping methods with availability and cost information
        """
        is_tehran = province == cls.TEHRAN_PROVINCE
        is_free_shipping = cart_total >= cls.FREE_SHIPPING_THRESHOLD

        # Standard post is available everywhere
        standard_cost = (
            cls.STANDARD_COST_TEHRAN if is_tehran else cls.STANDARD_COST_OTHER
        )
        standard_post = {
            "id": ShippingMethod.STANDARD_POST,
            "name": "پست معمولی",
            "description": "ارسال از طریق پست",
            "cost": 0 if is_free_shipping else standard_cost,
            "original_cost": standard_cost,
            "is_free": is_free_shipping,
            "estimated_delivery_days_min": 3,
            "estimated_delivery_days_max": 7,
            "is_available": True,
        }

        methods = [standard_post]

        # Express is only available in Tehran
        if is_tehran:
            express = {
                "id": ShippingMethod.EXPRESS,
                "name": "پیک موتوری",
                "description": "ارسال سریع با پیک",
                "cost": cls.EXPRESS_COST,
                "original_cost": cls.EXPRESS_COST,
                "is_free": False,
                "estimated_delivery_hours_min": 2,
                "estimated_delivery_hours_max": 4,
                "is_available": True,
                "available_for_provinces": [cls.TEHRAN_PROVINCE],
            }
            methods.append(express)

        return methods

    @classmethod
    def calculate_shipping_cost(
        cls, shipping_method_id: str, province: str, cart_total: int
    ) -> int:
        """
        Calculate shipping cost for a specific method

        Args:
            shipping_method_id: The shipping method ID
            province: Province name in Farsi
            cart_total: Total cart amount

        Returns:
            Shipping cost as integer

        Raises:
            ValueError: If shipping method is invalid or not available for province
        """
        is_tehran = province == cls.TEHRAN_PROVINCE
        is_free_shipping = cart_total >= cls.FREE_SHIPPING_THRESHOLD

        if shipping_method_id == ShippingMethod.STANDARD_POST:
            if is_free_shipping:
                return 0
            return cls.STANDARD_COST_TEHRAN if is_tehran else cls.STANDARD_COST_OTHER

        elif shipping_method_id == ShippingMethod.EXPRESS:
            if not is_tehran:
                raise ValueError("Express shipping is only available in Tehran province")
            return cls.EXPRESS_COST

        else:
            raise ValueError(f"Invalid shipping method: {shipping_method_id}")

    @classmethod
    def validate_shipping_method(
        cls, shipping_method_id: str, province: str
    ) -> Tuple[bool, str]:
        """
        Validate if a shipping method is available for the given province

        Args:
            shipping_method_id: The shipping method ID
            province: Province name in Farsi

        Returns:
            Tuple of (is_valid, error_message)
        """
        is_tehran = province == cls.TEHRAN_PROVINCE

        if shipping_method_id == ShippingMethod.STANDARD_POST:
            return True, ""

        elif shipping_method_id == ShippingMethod.EXPRESS:
            if not is_tehran:
                return False, "Express shipping is only available in Tehran province"
            return True, ""

        else:
            return False, f"Invalid shipping method: {shipping_method_id}"
