from celery import shared_task
from .models import Video
import whisper
from pyannote.audio import Pipeline

@shared_task
def transcribe_video(video_id):
    video = Video.objects.get(id=video_id)
    model = whisper.load_model("base")
    result = model.transcribe(video.file.path)
    video.transcription = result['text']
    video.progress = 50
    video.save()

@shared_task
def diarize_video(video_id):
    video = Video.objects.get(id=video_id)
    pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization")
    diarization = pipeline(video.file.path)
    video.diarization = str(diarization)
    video.is_transcribed = True
    video.progress = 100
    video.save()
