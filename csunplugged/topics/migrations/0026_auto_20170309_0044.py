# -*- coding: utf-8 -*- # Generated by Django 1.10.6 on 2017-03-09 00:44
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('topics', '0025_auto_20170307_0343'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='lesson',
            name='ages',
        ),
        migrations.AddField(
            model_name='lesson',
            name='max_age',
            field=models.PositiveSmallIntegerField(default=1),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='lesson',
            name='min_age',
            field=models.PositiveSmallIntegerField(default=1),
            preserve_default=False,
        ),
        migrations.DeleteModel(
            name='Age',
        ),
    ]
