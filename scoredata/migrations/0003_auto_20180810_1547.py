# Generated by Django 2.0.5 on 2018-08-10 19:47

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('scoredata', '0002_auto_20180724_2137'),
    ]

    operations = [
        migrations.AlterField(
            model_name='gymnast',
            name='id',
            field=models.UUIDField(default=uuid.uuid4, help_text='Unique ID for this particular gymnast across whole database', primary_key=True, serialize=False),
        ),
        migrations.AlterField(
            model_name='meet',
            name='id',
            field=models.UUIDField(default=uuid.uuid4, help_text='Unique ID for this particular meet across whole database', primary_key=True, serialize=False),
        ),
    ]
