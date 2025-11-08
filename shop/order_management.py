from typing import List

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from .choices import OrderStatus


class OrderStatusTransition:
    ALLOWED_TRANSITIONS = {
        OrderStatus.CART: [OrderStatus.PENDING],
        OrderStatus.PENDING: [OrderStatus.PROCESSING, OrderStatus.AWAITING_VERIFICATION, OrderStatus.CANCELLED],
        OrderStatus.AWAITING_VERIFICATION: [OrderStatus.CONFIRMED, OrderStatus.CANCELLED],
        OrderStatus.PROCESSING: [OrderStatus.CONFIRMED, OrderStatus.CANCELLED],
        OrderStatus.CONFIRMED: [OrderStatus.SHIPPED, OrderStatus.CANCELLED],
        OrderStatus.SHIPPED: [OrderStatus.DELIVERED, OrderStatus.RETURNED],
        OrderStatus.DELIVERED: [OrderStatus.RETURNED],
        OrderStatus.RETURNED: [OrderStatus.REFUNDED],
        OrderStatus.CANCELLED: [OrderStatus.REFUNDED],
    }

    @classmethod
    def get_allowed_transitions(cls, current_status: str) -> List[str]:
        """Get allowed next statuses for current status"""
        return cls.ALLOWED_TRANSITIONS.get(current_status, [])

    @classmethod
    def can_transition(cls, current_status: str, new_status: str) -> bool:
        """Check if status transition is allowed"""
        return new_status in cls.get_allowed_transitions(current_status)

    @classmethod
    def validate_transition(cls, current_status: str, new_status: str) -> None:
        """Validate status transition"""
        if not cls.can_transition(current_status, new_status):
            raise ValidationError(
                _('Cannot transition from %(current)s to %(new)s') % {
                    'current': current_status,
                    'new': new_status
                }
            )
