# Generated by Django 4.2.23 on 2025-07-16 07:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_user_paypal_subscription_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="trial_ip",
            field=models.GenericIPAddressField(blank=True, null=True),
        ),
    ]
