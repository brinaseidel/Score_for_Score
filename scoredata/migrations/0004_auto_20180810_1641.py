# Generated by Django 2.0.5 on 2018-08-10 20:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scoredata', '0003_auto_20180810_1547'),
    ]

    operations = [
        migrations.AlterField(
            model_name='meet',
            name='id',
            field=models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'),
        ),
    ]
