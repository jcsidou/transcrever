from django.urls import path
from . import views

urlpatterns = [
    path('', views.gallery_view, name='gallery'),
    path('gallery/', views.gallery_view, name='gallery'),
    path('ajax/gallery/', views.ajax_gallery_view, name='ajax_gallery_view'),
    path('upload/', views.upload_video, name='upload_video'),
    path('video/<int:video_id>/export/', views.export_to_docx, name='export_to_docx'),
    path('video/<int:video_id>/', views.video_detail_view, name='video_detail'),  # Associa a view à URL
    path('video/<int:video_id>/generate_docx/', views.generate_docx, name='generate_docx'),
    path('video/<int:video_id>/delete/', views.delete_transcription, name='delete_transcription'),
    path('video/<int:video_id>/update_transcription_table/', views.update_transcription_table, name='update_transcription_table'),
    path('ajax/question-answer/<int:video_id>/', views.ajax_question_answer, name='ajax_question_answer'),
]