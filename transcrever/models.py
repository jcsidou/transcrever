from django.db import models

class Video(models.Model):
    file = models.FileField(upload_to='videos/')
    transcription = models.TextField(blank=True, null=True)
    diarization = models.TextField(blank=True, null=True)
    is_transcribed = models.BooleanField(default=False)
    is_diarized = models.BooleanField(default=False)
    progress = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    metadata = models.TextField(blank=True, null=True)
    title = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.file.name
