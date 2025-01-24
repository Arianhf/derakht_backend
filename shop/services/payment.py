from typing import Dict, Any

from ..choices import PaymentStatus, OrderStatus
from ..gateways.zarinpal import ZarinpalGateway
from ..models import Payment, Order


class PaymentService:
    def __init__(self):
        self.gateway = ZarinpalGateway()

    def create_payment(self, order: Order) -> Payment:
        return Payment.objects.create(
            order=order,
            amount=order.total_amount,
            currency=order.currency
        )

    def request_payment(self, payment: Payment) -> Dict[str, Any]:
        result = self.gateway.request_payment(payment)

        if result.get('code') == 100:
            payment.status = PaymentStatus.PROCESSING
            payment.reference_id = result.get('authority')
            payment.save()

            return {
                'success': True,
                'redirect_url': self.gateway.get_payment_url(
                    payment,
                    result.get('authority')
                )
            }

        payment.status = PaymentStatus.FAILED
        payment.save()
        return {'success': False, 'message': result.get('message')}

    def verify_payment(self, payment: Payment, request_data: Dict) -> Dict[str, Any]:
        result = self.gateway.verify_payment(payment, request_data)

        if result.get('code') == 100:
            payment.status = PaymentStatus.COMPLETED
            payment.save()

            # Update order status
            order = payment.order
            order.status = OrderStatus.CONFIRMED
            order.save()

            return {'success': True, 'ref_id': result.get('ref_id')}

        payment.status = PaymentStatus.FAILED
        payment.save()
        return {'success': False, 'message': result.get('message')}
