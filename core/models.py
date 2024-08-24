from django.db import models
from datetime import datetime

class modelos(models.Model):
    nome = models.CharField(max_length=50)

MODEL_CHOICES = (
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
    process_times = models.JSONField(blank=True, null=True, default=dict)

    def save(self, *args, **kwargs):
        # Certifique-se de que todos os valores de datetime sejam strings
        if self.process_times:
            for key, value in self.process_times.items():
                if isinstance(value, datetime):
                    self.process_times[key] = value.strftime('%Y-%m-%d %H:%M:%S')
        super().save(*args, **kwargs)

    def calculate_durations(self):
        """Calcula as durações das etapas de processamento e o tempo total."""
        if not self.process_times:
            self.process_times = {}
        
        print("CALCULAR")
        conversion_start = parse_datetime(self.process_times.get('conversion_start'))
        conversion_end = parse_datetime(self.process_times.get('conversion_end'))
        transcription_start = parse_datetime(self.process_times.get('transcription_start'))
        transcription_end = parse_datetime(self.process_times.get('transcription_end'))
        diarization_start = parse_datetime(self.process_times.get('diarization_start'))
        diarization_end = parse_datetime(self.process_times.get('diarization_end'))
        
        # durations = {}
        print("process_times",self.process_times)
        if conversion_start and conversion_end:
            print("CALCULAR DURAÇÃO")
            self.process_times['conversion_duration'] = (conversion_end - conversion_start).total_seconds()

        if transcription_start and transcription_end:
            print("CALCULAR TRANSCRIÇAO")
            self.process_times['transcription_duration'] = (transcription_end - transcription_start).total_seconds()

        if diarization_start and diarization_end:
            print("CALCULAR DIARIZAÇÃO")
            self.process_times['diarization_duration'] = (diarization_end - diarization_start).total_seconds()

        # Cálculo do tempo total de processamento
        if conversion_start and (diarization_end or transcription_end):
            print("CALCULAR TOTAL")
            if diarization_end:
                self.process_times['total_duration'] = (diarization_end - conversion_start).total_seconds()
            else:
                self.process_times['total_duration'] = (transcription_end - conversion_start).total_seconds()

        print("process_times",self.process_times)
            # Após calcular, salvar o modelo para persistir as mudanças
        self.save()

        return self.process_times  # Retorne o JSON atualizado para conferência

    def __str__(self):
        return self.file.name

def parse_datetime(dt_str):
    """Converte uma string ISO 8601 em um objeto datetime"""
    return datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S') if dt_str else None