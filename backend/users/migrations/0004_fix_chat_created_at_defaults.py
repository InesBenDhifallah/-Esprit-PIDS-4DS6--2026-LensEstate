# Generated manually on 2026-05-01

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0003_chatsession_chatmessage"),
    ]

    operations = [
        migrations.AlterField(
            model_name="chatsession",
            name="created_at",
            field=models.DateTimeField(
                auto_now_add=True,
                default=django.utils.timezone.now,
            ),
        ),
        migrations.AlterField(
            model_name="chatmessage",
            name="created_at",
            field=models.DateTimeField(
                auto_now_add=True,
                default=django.utils.timezone.now,
            ),
        ),
    ]
