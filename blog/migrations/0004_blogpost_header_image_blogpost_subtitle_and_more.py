# Generated by Django 5.1.2 on 2024-11-03 15:01

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0003_blogposttag_blogpost_tags'),
        ('wagtailimages', '0026_delete_uploadedimage'),
    ]

    operations = [
        migrations.AddField(
            model_name='blogpost',
            name='header_image',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='wagtailimages.image'),
        ),
        migrations.AddField(
            model_name='blogpost',
            name='subtitle',
            field=models.CharField(blank=True, max_length=250),
        ),
        migrations.DeleteModel(
            name='BlogPageGalleryImage',
        ),
    ]
