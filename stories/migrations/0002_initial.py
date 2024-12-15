# Generated by Django 5.1.2 on 2024-11-11 15:12

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('stories', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='story',
            name='author',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='stories', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='storypart',
            name='story',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='parts', to='stories.story'),
        ),
        migrations.AddField(
            model_name='storyparttemplate',
            name='template',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='template_parts', to='stories.storytemplate'),
        ),
        migrations.AddField(
            model_name='storycollection',
            name='stories',
            field=models.ManyToManyField(to='stories.storytemplate'),
        ),
        migrations.AlterUniqueTogether(
            name='storypart',
            unique_together={('story', 'position')},
        ),
        migrations.AlterUniqueTogether(
            name='storyparttemplate',
            unique_together={('template', 'position')},
        ),
    ]
