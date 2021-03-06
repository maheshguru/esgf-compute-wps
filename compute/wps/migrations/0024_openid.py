# -*- coding: utf-8 -*-
# Generated by Django 1.11.1 on 2017-09-05 15:19
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('wps', '0023_file_tracking'),
    ]

    operations = [
        migrations.CreateModel(
            name='OpenIDAssociation',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('server_url', models.CharField(max_length=2048)),
                ('handle', models.CharField(max_length=256)),
                ('secret', models.TextField(max_length=256)),
                ('issued', models.IntegerField()),
                ('lifetime', models.IntegerField()),
                ('assoc_type', models.TextField(max_length=64)),
                ('user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='OpenIDNonce',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('server_url', models.CharField(max_length=2048)),
                ('timestamp', models.IntegerField()),
                ('salt', models.CharField(max_length=40)),
                ('user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='files',
            unique_together=set([('name', 'host')]),
        ),
        migrations.AlterUniqueTogether(
            name='openidnonce',
            unique_together=set([('server_url', 'timestamp', 'salt')]),
        ),
        migrations.AlterUniqueTogether(
            name='openidassociation',
            unique_together=set([('server_url', 'handle')]),
        ),
    ]
