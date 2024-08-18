from django import forms
from .models import Video

class VideoUploadForm(forms.ModelForm):
    class Meta:
        label = "Upload de Vídeo"
        title = 'Upload de Vídeo'
        model = Video
        fields = ['file']
