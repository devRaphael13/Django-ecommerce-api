# Generated by Django 4.2.11 on 2024-03-25 12:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0003_remove_category_image'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='display_image',
            field=models.URLField(default='https://google.com'),
            preserve_default=False,
        ),
    ]
