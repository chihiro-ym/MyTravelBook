# Generated by Django 5.1.1 on 2024-10-18 11:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0006_rename_create_at_prefecture_created_at_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='photo',
            name='photo_url',
            field=models.ImageField(blank=True, null=True, upload_to='photos/'),
        ),
    ]