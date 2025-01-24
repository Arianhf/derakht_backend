from abc import ABC, abstractmethod
from typing import Dict, Any

from ..models import Payment


class PaymentGateway(ABC):
    @abstractmethod
    def request_payment(self, payment: Payment) -> Dict[str, Any]:
        """Request a payment and return the response"""
        pass

    @abstractmethod
    def verify_payment(self, payment: Payment, request_data: Dict) -> Dict[str, Any]:
        """Verify a payment after user is redirected back"""
        pass

    @abstractmethod
    def get_payment_url(self, payment: Payment, token: str) -> str:
        """Get the URL to redirect user to for payment"""
        pass
