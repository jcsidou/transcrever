from django.shortcuts import render
from django.shortcuts import render, get_object_or_404
from .models import Video

def gallery(request):
    videos = Video.objects.all()
    return render(request, 'core/gallery.html', {'videos': videos})

def video_detail(request, video_id):
    video = get_object_or_404(Video, id=video_id)
    return render(request, 'core/video_detail.html', {'video': video})
