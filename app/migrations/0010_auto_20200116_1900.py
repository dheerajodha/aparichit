# Generated by Django 3.0.2 on 2020-01-16 13:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0009_launchpad_missile'),
    ]

    operations = [
        migrations.AlterField(
            model_name='launchpad',
            name='missile',
            field=models.CharField(default='No missiles', max_length=30),
        ),
    ]
