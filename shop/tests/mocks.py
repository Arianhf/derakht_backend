from shop.gateways.base import PaymentGateway
from shop.models import Order, Payment
from typing import Dict, Any
from uuid import uuid4


class MockPaymentGateway(PaymentGateway):
    """Mock payment gateway for testing"""

    def __init__(self):
        self.should_succeed = True
        self.payment_url = "https://mock-gateway.com/pay/12345"
        self.authority = "A00000000000000000000000000012345678"
        self.reference_id = "REF123456"

    def request_payment(self, order: Order) -> Dict[str, Any]:
        if self.should_succeed:
            return {
                "success": True,
                "payment_url": self.payment_url,
                "authority": self.authority,
                "payment_id": uuid4(),
                "gateway": "mock",
            }
        else:
            return {
                "success": False,
                "error_message": "Mock gateway error",
            }

    def verify_payment(self, payment: Payment, request_data: Dict) -> Dict[str, Any]:
        authority = request_data.get('authority', '')
        if self.should_succeed and authority == self.authority:
            return {
                "success": True,
                "reference_id": self.reference_id,
                "status": "COMPLETED",
                "amount": payment.amount,
            }
        else:
            return {
                "success": False,
                "error_message": "Verification failed",
                "status": "FAILED",
            }

    def get_payment_url(self, payment: Payment, token: str) -> str:
        return f"{self.payment_url}?token={token}"
