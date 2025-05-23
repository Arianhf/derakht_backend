# Generated by Django 5.1.7 on 2025-04-20 01:29

import modelcluster.fields
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("blog", "0006_alter_blogpost_categories"),
    ]

    operations = [
        migrations.AddField(
            model_name="blogpost",
            name="related_posts",
            field=modelcluster.fields.ParentalManyToManyField(
                blank=True, related_name="posts_related_to", to="blog.blogpost"
            ),
        ),
    ]
