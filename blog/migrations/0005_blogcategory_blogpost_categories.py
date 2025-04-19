# Generated by Django 5.1.7 on 2025-04-19 15:43

import django.db.models.deletion
import modelcluster.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("blog", "0004_blogpost_hero_alter_blogpost_featured"),
        ("wagtailimages", "0027_image_description"),
    ]

    operations = [
        migrations.CreateModel(
            name="BlogCategory",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=255)),
                (
                    "slug",
                    models.SlugField(
                        allow_unicode=True,
                        help_text="A slug to identify posts by this category",
                        max_length=255,
                        unique=True,
                        verbose_name="slug",
                    ),
                ),
                ("description", models.TextField(blank=True)),
                (
                    "icon",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to="wagtailimages.image",
                    ),
                ),
            ],
            options={
                "verbose_name": "Blog Category",
                "verbose_name_plural": "Blog Categories",
                "ordering": ["name"],
            },
        ),
        migrations.AddField(
            model_name="blogpost",
            name="categories",
            field=modelcluster.fields.ParentalManyToManyField(
                blank=True, to="blog.blogcategory"
            ),
        ),
    ]
