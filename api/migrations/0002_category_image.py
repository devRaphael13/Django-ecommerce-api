# Generated by Django 4.2.11 on 2024-03-14 12:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='category',
            name='image',
            field=models.URLField(default='https://google.com'),
            preserve_default=False,
        ),
    ]