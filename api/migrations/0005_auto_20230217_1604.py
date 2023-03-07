# Generated by Django 3.2.9 on 2023-02-17 16:04

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0004_rename_accountdetail_account'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='account',
            name='active',
        ),
        migrations.AlterField(
            model_name='product',
            name='category',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='products', to='api.category'),
        ),
    ]