# core/migrations/0002_enable_pg_trgm.py
from django.contrib.postgres.operations import TrigramExtension
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        TrigramExtension(),
    ]
