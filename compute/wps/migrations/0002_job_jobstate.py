# -*- coding: utf-8 -*-
# Generated by Django 1.10.6 on 2017-03-03 23:21
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('wps', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Job',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('result', models.TextField()),
                ('server', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='wps.Server')),
            ],
        ),
        migrations.CreateModel(
            name='JobState',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('state', models.IntegerField()),
                ('create', models.DateTimeField(auto_now_add=True)),
                ('job', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='wps.Job')),
            ],
        ),
    ]
