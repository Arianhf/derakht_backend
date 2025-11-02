# Generated manually for user/author SEO improvements

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0003_address'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='bio',
            field=models.TextField(
                blank=True,
                help_text='Short author biography (100-200 characters recommended)'
            ),
        ),
        migrations.AddField(
            model_name='user',
            name='social_links',
            field=models.JSONField(
                default=dict,
                blank=True,
                help_text='Social media links as JSON: {"twitter": "url", "instagram": "url", "linkedin": "url"}'
            ),
        ),
    ]
