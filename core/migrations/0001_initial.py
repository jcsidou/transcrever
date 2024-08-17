# Generated by Django 5.0.8 on 2024-08-17 17:15

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Video',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file', models.FileField(upload_to='videos/')),
                ('transcription', models.TextField(blank=True, null=True)),
                ('diarization', models.TextField(blank=True, null=True)),
                ('is_transcribed', models.BooleanField(default=False)),
                ('is_diarized', models.BooleanField(default=False)),
                ('progress', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('metadata', models.TextField(blank=True, null=True)),
                ('title', models.CharField(blank=True, max_length=255, null=True)),
            ],
        ),
    ]