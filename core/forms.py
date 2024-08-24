from django import forms
from .models import Video, MODEL_CHOICES

class VideoUploadForm(forms.ModelForm):
    diarize = forms.BooleanField(required=False, label="Fazer diarização")
    class Meta:
        model = Video
        label = "Upload de Vídeo"
        title = 'Upload de Vídeo'
        # fields = ['file', 'model']
        fields = ['file', 'model', 'diarize']
        widgets = {
            'model': forms.Select(choices=MODEL_CHOICES, attrs={'default': 'medium'}),
            'diarize': forms.BooleanField(required=False, label="Identificar oradores")
        }   

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            # Define o valor padrão como "medium"
            self.fields['model'].initial = 'medium'