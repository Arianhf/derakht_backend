# shop/tests/test_services/test_shipping.py

from django.test import TestCase
from shop.services.shipping import ShippingCalculator
from shop.choices import ShippingMethod


class ShippingCalculatorTest(TestCase):
    """Test cases for ShippingCalculator service"""

    def test_get_shipping_methods_tehran_below_threshold(self):
        """Test shipping methods for Tehran with cart below free shipping threshold"""
        province = "تهران"
        city = "تهران"
        cart_total = 500_000  # Below threshold

        methods = ShippingCalculator.get_shipping_methods(province, city, cart_total)

        # Should have 2 methods (standard post + express)
        self.assertEqual(len(methods), 2)

        # Check standard post
        standard = methods[0]
        self.assertEqual(standard["id"], ShippingMethod.STANDARD_POST)
        self.assertEqual(standard["cost"], ShippingCalculator.STANDARD_COST_TEHRAN)
        self.assertFalse(standard["is_free"])
        self.assertTrue(standard["is_available"])

        # Check express
        express = methods[1]
        self.assertEqual(express["id"], ShippingMethod.EXPRESS)
        self.assertEqual(express["cost"], ShippingCalculator.EXPRESS_COST)
        self.assertFalse(express["is_free"])
        self.assertTrue(express["is_available"])

    def test_get_shipping_methods_tehran_above_threshold(self):
        """Test shipping methods for Tehran with cart above free shipping threshold"""
        province = "تهران"
        city = "تهران"
        cart_total = 1_500_000  # Above threshold

        methods = ShippingCalculator.get_shipping_methods(province, city, cart_total)

        # Should have 2 methods
        self.assertEqual(len(methods), 2)

        # Standard post should be free
        standard = methods[0]
        self.assertEqual(standard["id"], ShippingMethod.STANDARD_POST)
        self.assertEqual(standard["cost"], 0)
        self.assertTrue(standard["is_free"])
        self.assertEqual(
            standard["original_cost"], ShippingCalculator.STANDARD_COST_TEHRAN
        )

        # Express should not be free
        express = methods[1]
        self.assertEqual(express["id"], ShippingMethod.EXPRESS)
        self.assertEqual(express["cost"], ShippingCalculator.EXPRESS_COST)
        self.assertFalse(express["is_free"])

    def test_get_shipping_methods_other_province_below_threshold(self):
        """Test shipping methods for non-Tehran province below threshold"""
        province = "اصفهان"
        city = "اصفهان"
        cart_total = 500_000

        methods = ShippingCalculator.get_shipping_methods(province, city, cart_total)

        # Should have only 1 method (standard post, no express)
        self.assertEqual(len(methods), 1)

        standard = methods[0]
        self.assertEqual(standard["id"], ShippingMethod.STANDARD_POST)
        self.assertEqual(standard["cost"], ShippingCalculator.STANDARD_COST_OTHER)
        self.assertFalse(standard["is_free"])

    def test_get_shipping_methods_other_province_above_threshold(self):
        """Test shipping methods for non-Tehran province above threshold"""
        province = "اصفهان"
        city = "اصفهان"
        cart_total = 1_500_000

        methods = ShippingCalculator.get_shipping_methods(province, city, cart_total)

        # Standard post should be free
        standard = methods[0]
        self.assertEqual(standard["cost"], 0)
        self.assertTrue(standard["is_free"])
        self.assertEqual(
            standard["original_cost"], ShippingCalculator.STANDARD_COST_OTHER
        )

    def test_calculate_shipping_cost_standard_tehran_below_threshold(self):
        """Test standard shipping cost calculation for Tehran below threshold"""
        cost = ShippingCalculator.calculate_shipping_cost(
            ShippingMethod.STANDARD_POST, "تهران", 500_000
        )
        self.assertEqual(cost, ShippingCalculator.STANDARD_COST_TEHRAN)

    def test_calculate_shipping_cost_standard_tehran_above_threshold(self):
        """Test standard shipping cost calculation for Tehran above threshold"""
        cost = ShippingCalculator.calculate_shipping_cost(
            ShippingMethod.STANDARD_POST, "تهران", 1_500_000
        )
        self.assertEqual(cost, 0)

    def test_calculate_shipping_cost_standard_other_province(self):
        """Test standard shipping cost calculation for other provinces"""
        cost = ShippingCalculator.calculate_shipping_cost(
            ShippingMethod.STANDARD_POST, "اصفهان", 500_000
        )
        self.assertEqual(cost, ShippingCalculator.STANDARD_COST_OTHER)

    def test_calculate_shipping_cost_express_tehran(self):
        """Test express shipping cost calculation for Tehran"""
        cost = ShippingCalculator.calculate_shipping_cost(
            ShippingMethod.EXPRESS, "تهران", 500_000
        )
        self.assertEqual(cost, ShippingCalculator.EXPRESS_COST)

    def test_calculate_shipping_cost_express_other_province_raises_error(self):
        """Test that express shipping raises error for non-Tehran provinces"""
        with self.assertRaises(ValueError) as context:
            ShippingCalculator.calculate_shipping_cost(
                ShippingMethod.EXPRESS, "اصفهان", 500_000
            )

        self.assertIn("Express shipping is only available in Tehran", str(context.exception))

    def test_calculate_shipping_cost_invalid_method_raises_error(self):
        """Test that invalid shipping method raises error"""
        with self.assertRaises(ValueError) as context:
            ShippingCalculator.calculate_shipping_cost("invalid_method", "تهران", 500_000)

        self.assertIn("Invalid shipping method", str(context.exception))

    def test_validate_shipping_method_standard_post_any_province(self):
        """Test validation of standard post for any province"""
        is_valid, error = ShippingCalculator.validate_shipping_method(
            ShippingMethod.STANDARD_POST, "تهران"
        )
        self.assertTrue(is_valid)
        self.assertEqual(error, "")

        is_valid, error = ShippingCalculator.validate_shipping_method(
            ShippingMethod.STANDARD_POST, "اصفهان"
        )
        self.assertTrue(is_valid)
        self.assertEqual(error, "")

    def test_validate_shipping_method_express_tehran(self):
        """Test validation of express shipping for Tehran"""
        is_valid, error = ShippingCalculator.validate_shipping_method(
            ShippingMethod.EXPRESS, "تهران"
        )
        self.assertTrue(is_valid)
        self.assertEqual(error, "")

    def test_validate_shipping_method_express_other_province(self):
        """Test validation of express shipping for non-Tehran province"""
        is_valid, error = ShippingCalculator.validate_shipping_method(
            ShippingMethod.EXPRESS, "اصفهان"
        )
        self.assertFalse(is_valid)
        self.assertIn("Express shipping is only available in Tehran", error)

    def test_validate_shipping_method_invalid_method(self):
        """Test validation of invalid shipping method"""
        is_valid, error = ShippingCalculator.validate_shipping_method(
            "invalid_method", "تهران"
        )
        self.assertFalse(is_valid)
        self.assertIn("Invalid shipping method", error)

    def test_free_shipping_threshold_boundary(self):
        """Test free shipping at exact threshold"""
        # Exactly at threshold
        cost = ShippingCalculator.calculate_shipping_cost(
            ShippingMethod.STANDARD_POST,
            "تهران",
            ShippingCalculator.FREE_SHIPPING_THRESHOLD,
        )
        self.assertEqual(cost, 0)

        # Just below threshold
        cost = ShippingCalculator.calculate_shipping_cost(
            ShippingMethod.STANDARD_POST,
            "تهران",
            ShippingCalculator.FREE_SHIPPING_THRESHOLD - 1,
        )
        self.assertEqual(cost, ShippingCalculator.STANDARD_COST_TEHRAN)
