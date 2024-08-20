from django.db import models

class modelos(models.Model):
    nome = models.CharField(max_length=50)
MODEL_CHOICES= (
    ("large-v3", "Grande aprimorado"),
    ("large", "Grande"),
    ("medium", "Médio"),
    ("base", "Básico"),
)

class Video(models.Model):
    file = models.FileField(upload_to='videos/')
    duration = models.TimeField(blank=True, null=True)
    transcription = models.TextField(blank=True, null=True)
    transcription_segments = models.JSONField(blank=True, null=True)
    transcription_phrases = models.JSONField(blank=True, null=True)
    word_timestamps = models.JSONField(blank=True, null=True)
    diarization = models.JSONField(blank=True, null=True)
    is_transcribed = models.BooleanField(default=False)
    is_diarized = models.BooleanField(default=False)
    error_on_convert = models.BooleanField(default=False)
    error_on_transcript = models.BooleanField(default=False)
    error_on_diarization = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    model = models.CharField(max_length=50, choices=MODEL_CHOICES, default='medium')
    diarize = models.BooleanField(default=False)
    in_process = models.BooleanField(default=False) 
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # from .tasks import process_video
        # process_video(self.id)

    def __str__(self):
        return self.file.name
