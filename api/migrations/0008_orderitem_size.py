# Generated by Django 3.2.9 on 2023-02-19 16:57

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0007_alter_account_brand'),
    ]

    operations = [
        migrations.AddField(
            model_name='orderitem',
            name='size',
            field=models.OneToOneField(default=1, on_delete=django.db.models.deletion.CASCADE, to='api.size'),
            preserve_default=False,
        ),
    ]
