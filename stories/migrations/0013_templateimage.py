# Generated manually for template image optimization
import uuid
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('stories', '0012_dual_canvas_refactor'),
    ]

    operations = [
        migrations.CreateModel(
            name='TemplateImage',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('part_index', models.IntegerField(help_text='Which template part this image belongs to')),
                ('image', models.ImageField(help_text='Image file', upload_to='story_templates/images/%Y/%m/')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('template', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='images', to='stories.storytemplate')),
            ],
            options={
                'ordering': ['template', 'part_index', 'created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='templateimage',
            index=models.Index(fields=['template', 'part_index'], name='stories_tem_templat_idx'),
        ),
    ]
