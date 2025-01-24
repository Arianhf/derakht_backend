# shop/gateways/zarinpal.py

from typing import Dict, Any

import requests
from django.conf import settings

from .base import PaymentGateway
from ..models import Payment, PaymentTransaction


class ZarinpalGateway(PaymentGateway):
    SANDBOX = getattr(settings, 'ZARINPAL_SANDBOX', True)
    MERCHANT_ID = getattr(settings, 'ZARINPAL_MERCHANT_ID', 'YOUR-MERCHANT-ID')

    def __init__(self):
        if self.SANDBOX:
            self.base_url = 'https://sandbox.zarinpal.com/pg/rest/WebGate'
            self.payment_url = 'https://sandbox.zarinpal.com/pg/StartPay/'
        else:
            self.base_url = 'https://api.zarinpal.com/pg/v4/payment'
            self.payment_url = 'https://www.zarinpal.com/pg/StartPay/'

    def request_payment(self, payment: Payment) -> Dict[str, Any]:
        callback_url = f"{settings.SITE_URL}/payments/verify/{payment.id}/"

        data = {
            'merchant_id': self.MERCHANT_ID,
            'amount': int(payment.amount / 10),  # Convert to Toman
            'description': f'Payment for order {payment.order.id}',
            'callback_url': callback_url,
            'metadata': {
                'mobile': payment.order.phone_number,
                'email': payment.order.user.email
            }
        }

        response = requests.post(
            f"{self.base_url}/request",
            json=data
        )
        result = response.json()

        # Create transaction record
        PaymentTransaction.objects.create(
            payment=payment,
            amount=payment.amount,
            raw_response=result
        )

        return result

    def verify_payment(self, payment: Payment, request_data: Dict) -> Dict[str, Any]:
        authority = request_data.get('Authority')
        data = {
            'merchant_id': self.MERCHANT_ID,
            'authority': authority,
            'amount': int(payment.amount / 10)  # Convert to Toman
        }

        response = requests.post(
            f"{self.base_url}/verify",
            json=data
        )
        result = response.json()

        # Create verification transaction
        PaymentTransaction.objects.create(
            payment=payment,
            amount=payment.amount,
            transaction_id=result.get('ref_id'),
            provider_status=str(result.get('code')),
            raw_response=result
        )

        return result

    def get_payment_url(self, payment: Payment, token: str) -> str:
        return f"{self.payment_url}{token}"
