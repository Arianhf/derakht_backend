# shop/models/comment.py
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

from .base import BaseModel
from .product import Product


class ProductComment(BaseModel):
    """
    Model for product comments/reviews
    """
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="comments",
        verbose_name=_("Product"),
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="product_comments",
        verbose_name=_("User"),
        null=True,
        blank=True,
    )
    user_name = models.CharField(
        _("User Name"),
        max_length=255,
        help_text=_("Display name or 'کاربر ناشناس' for anonymous users"),
    )
    text = models.TextField(_("Comment Text"))
    is_approved = models.BooleanField(_("Is Approved"), default=False)
    is_deleted = models.BooleanField(_("Is Deleted"), default=False)

    class Meta:
        verbose_name = _("Product Comment")
        verbose_name_plural = _("Product Comments")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["product", "-created_at"]),
            models.Index(fields=["user"]),
            models.Index(fields=["is_approved", "is_deleted"]),
        ]

    def __str__(self):
        return f"Comment by {self.user_name} on {self.product.title}"

    def save(self, *args, **kwargs):
        # Set user_name if not provided
        if not self.user_name:
            if self.user:
                # Use user's full name or email
                if self.user.first_name and self.user.last_name:
                    self.user_name = f"{self.user.first_name} {self.user.last_name}"
                else:
                    self.user_name = self.user.email.split("@")[0]
            else:
                self.user_name = "کاربر ناشناس"
        super().save(*args, **kwargs)
