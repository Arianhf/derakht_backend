# Generated manually for adding story colors
import re
from django.core.exceptions import ValidationError
from django.db import migrations, models


def validate_hex_color(value):
    """Validate that the value is a valid hex color code"""
    if not value:
        return
    hex_color_regex = r'^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$'
    if not re.match(hex_color_regex, value):
        raise ValidationError(
            f'{value} is not a valid hex color code. Use format #RRGGBB or #RGB'
        )


class Migration(migrations.Migration):

    dependencies = [
        ("stories", "0005_story_background_image_story_cover_image_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="story",
            name="background_image",
        ),
        migrations.AddField(
            model_name="story",
            name="background_color",
            field=models.CharField(
                max_length=7,
                null=True,
                blank=True,
                validators=[validate_hex_color],
                help_text="Hex color code (e.g., #FF5733 or #FFF)",
            ),
        ),
        migrations.AddField(
            model_name="story",
            name="font_color",
            field=models.CharField(
                max_length=7,
                null=True,
                blank=True,
                validators=[validate_hex_color],
                help_text="Hex color code for text (e.g., #000000 or #000)",
            ),
        ),
    ]
