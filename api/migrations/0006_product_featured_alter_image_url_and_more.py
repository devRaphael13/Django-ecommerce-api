# Generated by Django 4.2.11 on 2024-07-13 21:07

import cloudinary.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0005_product_reviews_product_stars'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='featured',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='image',
            name='url',
            field=cloudinary.models.CloudinaryField(max_length=255, verbose_name='image_url'),
        ),
        migrations.AlterField(
            model_name='product',
            name='display_image',
            field=cloudinary.models.CloudinaryField(max_length=255, verbose_name='display_image'),
        ),
    ]
