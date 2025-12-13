"""
Integration tests for Payment API endpoints.
Tests the critical payment processing flow with Zarinpal integration.

Priority: P0 - Financial transactions require zero tolerance for bugs
"""

import pytest
import responses
from decimal import Decimal
from django.urls import reverse
from rest_framework import status

from shop.models import Payment, PaymentTransaction, Invoice, Order
from shop.tests.factories import create_order_with_items, PaymentFactory


@pytest.mark.integration
@pytest.mark.payment
class TestPaymentRequestAPI:
    """Test payment request endpoint."""

    @responses.activate
    def test_request_payment_success(self, authenticated_client, order):
        """Test successful payment request creates payment and returns authority."""
        # Mock Zarinpal API response
        responses.add(
            responses.POST,
            "https://payment.zarinpal.com/pg/v4/payment/request.json",
            json={
                "data": {"authority": "A00000000000000000000000000123456"},
                "errors": [],
            },
            status=200,
        )

        url = reverse("payment-request", kwargs={"order_id": order.id})
        response = authenticated_client.post(url, {"gateway": "zarinpal"})

        assert response.status_code == status.HTTP_200_OK
        assert "authority" in response.data
        assert "payment_url" in response.data

        # Verify payment record created
        assert Payment.objects.filter(order=order).exists()
        payment = Payment.objects.get(order=order)
        assert payment.gateway == "ZARINPAL"
        assert payment.status == "PENDING"

    def test_request_payment_unauthenticated(self, api_client, order):
        """Test unauthenticated users cannot request payment."""
        url = reverse("payment-request", kwargs={"order_id": order.id})
        response = api_client.post(url, {"gateway": "zarinpal"})

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_request_payment_for_other_users_order(
        self, authenticated_client, user_factory
    ):
        """Test users cannot request payment for other users' orders."""
        other_user = user_factory()
        other_order = create_order_with_items(user=other_user)

        url = reverse("payment-request", kwargs={"order_id": other_order.id})
        response = authenticated_client.post(url, {"gateway": "zarinpal"})

        assert response.status_code in [
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
        ]

    def test_request_payment_invalid_order_status(self, authenticated_client, user):
        """Test payment request fails for orders not in valid status."""
        # Create a delivered order (cannot request payment for completed order)
        order = create_order_with_items(user=user, status="DELIVERED")

        url = reverse("payment-request", kwargs={"order_id": order.id})
        response = authenticated_client.post(url, {"gateway": "zarinpal"})

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @responses.activate
    def test_request_payment_with_promo_code(
        self, authenticated_client, order, active_promo_code
    ):
        """Test payment request with applied promo code."""
        # Apply promo code to order
        order.promo_code = active_promo_code
        order.discount_amount = Decimal("10.00")
        order.save()

        responses.add(
            responses.POST,
            "https://payment.zarinpal.com/pg/v4/payment/request.json",
            json={
                "data": {"authority": "A00000000000000000000000000123456"},
                "errors": [],
            },
            status=200,
        )

        url = reverse("payment-request", kwargs={"order_id": order.id})
        response = authenticated_client.post(url, {"gateway": "zarinpal"})

        assert response.status_code == status.HTTP_200_OK

        # Verify payment amount includes discount
        payment = Payment.objects.get(order=order)
        expected_amount = order.total_amount - order.discount_amount
        assert payment.amount == expected_amount


@pytest.mark.integration
@pytest.mark.payment
class TestPaymentVerificationAPI:
    """Test payment verification endpoint."""

    @responses.activate
    def test_verify_payment_success(self, authenticated_client, payment_flow):
        """Test successful payment verification updates payment and order status."""
        order, payment, transaction = payment_flow

        # Mock Zarinpal verification response
        responses.add(
            responses.POST,
            "https://payment.zarinpal.com/pg/v4/payment/verify.json",
            json={
                "data": {
                    "ref_id": "12345678",
                    "status": "success",
                    "card_pan": "123456******1234",
                },
                "errors": [],
            },
            status=200,
        )

        url = reverse("payment-verify")
        response = authenticated_client.post(
            url,
            {
                "payment_id": payment.id,
                "authority": transaction.authority,
                "status": "OK",
            },
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "success"

        # Verify payment updated
        payment.refresh_from_db()
        assert payment.status == "COMPLETED"
        assert payment.reference_id == "12345678"

        # Verify order status updated
        order.refresh_from_db()
        assert order.status in ["PROCESSING", "CONFIRMED"]

    @responses.activate
    def test_verify_payment_creates_invoice(self, authenticated_client, payment_flow):
        """Test that successful payment automatically creates invoice."""
        order, payment, transaction = payment_flow

        responses.add(
            responses.POST,
            "https://payment.zarinpal.com/pg/v4/payment/verify.json",
            json={
                "data": {"ref_id": "12345678", "status": "success"},
                "errors": [],
            },
            status=200,
        )

        url = reverse("payment-verify")
        response = authenticated_client.post(
            url,
            {
                "payment_id": payment.id,
                "authority": transaction.authority,
                "status": "OK",
            },
        )

        assert response.status_code == status.HTTP_200_OK

        # Verify invoice created (via signal)
        assert Invoice.objects.filter(order=order).exists()
        invoice = Invoice.objects.get(order=order)
        assert invoice.total_amount == order.total_amount
        assert invoice.invoice_number.startswith("INV")

    @responses.activate
    def test_verify_payment_failure(self, authenticated_client, payment_flow):
        """Test payment verification failure updates payment status."""
        order, payment, transaction = payment_flow

        responses.add(
            responses.POST,
            "https://payment.zarinpal.com/pg/v4/payment/verify.json",
            json={"data": {}, "errors": ["Payment verification failed"]},
            status=400,
        )

        url = reverse("payment-verify")
        response = authenticated_client.post(
            url,
            {
                "payment_id": payment.id,
                "authority": transaction.authority,
                "status": "NOK",
            },
        )

        # Should handle failure gracefully
        payment.refresh_from_db()
        assert payment.status == "FAILED"

        # Order should remain in pending state
        order.refresh_from_db()
        assert order.status == "PENDING"

    def test_verify_payment_unauthenticated(self, api_client, payment_flow):
        """Test unauthenticated users cannot verify payments."""
        _, payment, transaction = payment_flow

        url = reverse("payment-verify")
        response = api_client.post(
            url,
            {
                "payment_id": payment.id,
                "authority": transaction.authority,
                "status": "OK",
            },
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_verify_payment_duplicate_verification(
        self, authenticated_client, payment_flow
    ):
        """Test that already-verified payments cannot be re-verified."""
        order, payment, transaction = payment_flow

        # Mark payment as already completed
        payment.status = "COMPLETED"
        payment.reference_id = "12345678"
        payment.save()

        url = reverse("payment-verify")
        response = authenticated_client.post(
            url,
            {
                "payment_id": payment.id,
                "authority": transaction.authority,
                "status": "OK",
            },
        )

        # Should reject duplicate verification
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.integration
@pytest.mark.payment
class TestPaymentCallbackAPI:
    """Test payment gateway callback endpoint."""

    @responses.activate
    def test_zarinpal_callback_success(self, api_client, payment_flow):
        """Test Zarinpal callback webhook handles successful payment."""
        order, payment, transaction = payment_flow

        responses.add(
            responses.POST,
            "https://payment.zarinpal.com/pg/v4/payment/verify.json",
            json={"data": {"ref_id": "12345678", "status": "success"}, "errors": []},
            status=200,
        )

        url = reverse(
            "payment-callback",
            kwargs={"gateway": "zarinpal", "payment_id": payment.id},
        )
        response = api_client.get(
            url, {"Authority": transaction.authority, "Status": "OK"}
        )

        # Should redirect to frontend with success
        assert response.status_code in [
            status.HTTP_302_FOUND,
            status.HTTP_200_OK,
        ]

        payment.refresh_from_db()
        assert payment.status == "COMPLETED"

    def test_zarinpal_callback_cancelled(self, api_client, payment_flow):
        """Test Zarinpal callback when user cancels payment."""
        order, payment, transaction = payment_flow

        url = reverse(
            "payment-callback",
            kwargs={"gateway": "zarinpal", "payment_id": payment.id},
        )
        response = api_client.get(
            url, {"Authority": transaction.authority, "Status": "NOK"}
        )

        # Should handle cancellation
        payment.refresh_from_db()
        assert payment.status in ["CANCELLED", "FAILED"]


@pytest.mark.integration
@pytest.mark.payment
class TestManualPaymentVerification:
    """Test manual payment verification with receipt upload."""

    def test_upload_payment_receipt(self, authenticated_client, payment):
        """Test uploading payment receipt for manual verification."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        receipt = SimpleUploadedFile(
            "receipt.jpg", b"fake_image_content", content_type="image/jpeg"
        )

        url = reverse("payment-upload-receipt")
        response = authenticated_client.post(
            url, {"payment_id": payment.id, "receipt": receipt}
        )

        assert response.status_code == status.HTTP_200_OK

        # Verify payment status updated to awaiting verification
        payment.refresh_from_db()
        assert payment.status == "AWAITING_VERIFICATION"

        # Verify order status updated
        order = payment.order
        order.refresh_from_db()
        assert order.status == "AWAITING_VERIFICATION"

    def test_upload_receipt_without_file(self, authenticated_client, payment):
        """Test that receipt upload requires a file."""
        url = reverse("payment-upload-receipt")
        response = authenticated_client.post(url, {"payment_id": payment.id})

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.integration
@pytest.mark.payment
class TestPaymentStatus:
    """Test payment status check endpoint."""

    def test_get_payment_status(self, authenticated_client, payment):
        """Test retrieving payment status."""
        url = reverse("payment-status", kwargs={"payment_id": payment.id})
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == payment.status
        assert response.data["amount"] == str(payment.amount)

    def test_get_payment_status_unauthenticated(self, api_client, payment):
        """Test unauthenticated users cannot view payment status."""
        url = reverse("payment-status", kwargs={"payment_id": payment.id})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.integration
@pytest.mark.payment
class TestPaymentTransactionLogging:
    """Test that payment transactions are logged correctly."""

    @responses.activate
    def test_payment_request_logs_transaction(self, authenticated_client, order):
        """Test that payment requests create transaction logs."""
        responses.add(
            responses.POST,
            "https://payment.zarinpal.com/pg/v4/payment/request.json",
            json={
                "data": {"authority": "A00000000000000000000000000123456"},
                "errors": [],
            },
            status=200,
        )

        url = reverse("payment-request", kwargs={"order_id": order.id})
        response = authenticated_client.post(url, {"gateway": "zarinpal"})

        assert response.status_code == status.HTTP_200_OK

        # Verify transaction logged
        payment = Payment.objects.get(order=order)
        assert PaymentTransaction.objects.filter(payment=payment).exists()

        transaction = PaymentTransaction.objects.get(payment=payment)
        assert transaction.authority is not None
        assert transaction.raw_request is not None
        assert transaction.raw_response is not None

    @responses.activate
    def test_payment_verification_logs_transaction(
        self, authenticated_client, payment_flow
    ):
        """Test that payment verification logs are created."""
        order, payment, transaction = payment_flow

        responses.add(
            responses.POST,
            "https://payment.zarinpal.com/pg/v4/payment/verify.json",
            json={"data": {"ref_id": "12345678", "status": "success"}, "errors": []},
            status=200,
        )

        url = reverse("payment-verify")
        response = authenticated_client.post(
            url,
            {
                "payment_id": payment.id,
                "authority": transaction.authority,
                "status": "OK",
            },
        )

        assert response.status_code == status.HTTP_200_OK

        # Transaction should be updated with verification result
        transaction.refresh_from_db()
        assert transaction.status == "COMPLETED"
