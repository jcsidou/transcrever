from django.urls import path
from . import views

urlpatterns = [
    path('', views.gallery_view, name='gallery'),
    path('gallery/', views.gallery_view, name='gallery'),
    path('upload/', views.upload_video, name='upload_video'),
    path('video/<int:video_id>/export/', views.export_to_docx, name='export_to_docx'),
    path('video/<int:video_id>/', views.video_detail_view, name='video_detail'),  # Associa a view à URL
    path('video/<int:video_id>/generate_docx/', views.generate_docx, name='generate_docx'),
    path('video/<int:video_id>/delete/', views.delete_transcription, name='delete_transcription'),
]