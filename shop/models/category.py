# shop/models/category.py

from django.db import models
from django.utils.translation import gettext_lazy as _

from .base import BaseModel


class Category(BaseModel):
    name = models.CharField(_("Name"), max_length=255)
    slug = models.SlugField(_("Slug"), max_length=255, unique=True)
    description = models.TextField(_("Description"), blank=True)
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        related_name="children",
        verbose_name=_("Parent Category"),
        blank=True,
        null=True,
    )
    image = models.ImageField(
        _("Image"), upload_to="categories/", blank=True, null=True
    )

    class Meta:
        verbose_name = _("Category")
        verbose_name_plural = _("Categories")
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def image_url(self):
        return self.image.url if self.image else None
