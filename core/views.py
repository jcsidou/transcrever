from django.shortcuts import render, get_object_or_404, redirect
from django.conf import settings
from .models import Video
from .forms import VideoUploadForm
from .tasks import process_video
from django.http import HttpResponse
from datetime import datetime, timedelta, time
import docx
import json
import logging
import os
from docx import Document
from docx.shared import Pt, Mm
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from docx.oxml.ns import nsdecls
from docx.oxml import OxmlElement, ns
from .models import Video

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
log_message = lambda message: logging.info(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {message}")

def gallery(request):
    videos = Video.objects.all()
    return render(request, 'core/gallery.html', {'videos': videos})

def video_detail(request, video_id):
    video = get_object_or_404(Video, id=video_id)
    return render(request, 'core/video_detail.html', {'video': video})

def upload_video(request):
    if request.method == 'POST':
        log_message(f"Postando arquivo ({request.FILES['file'].name})")
        form = VideoUploadForm(request.POST, request.FILES)
        if form.is_valid():
            log_message(f"Salvando formulario")
            video = form.save()
            process_video(video.id)
            return redirect('gallery')
    else:
        form = VideoUploadForm()
    return render(request, 'core/upload_video.html', {'form': form})

def export_to_docx(request, video_id):
    video = get_object_or_404(Video, id=video_id)
    
    doc = docx.Document()
    doc.add_heading(f'Transcrição do Vídeo: {video.file.name}', 0)

    if video.transcription:
        for line in video.transcription.splitlines():
            doc.add_paragraph(line)
    else:
        doc.add_paragraph("Transcrição não disponível.")
    
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
    response['Content-Disposition'] = f'attachment; filename={video.file.name}.docx'
    doc.save(response)
    return response

def format_time(seconds):
    """Converte segundos para o formato HH:MM:ss"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = round(seconds % 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}"

def video_detail_view(request, video_id):
    # Recupera o objeto Video do banco de dados
    video = get_object_or_404(Video, id=video_id)

    # Converte a string JSON em uma lista de dicionários, se necessário
    if isinstance(video.transcription_phrases, str):
        video.transcription_phrases = json.loads(video.transcription_phrases)

    # Construa a URL completa usando MEDIA_URL
    video_url = f"{settings.MEDIA_URL}videos/{os.path.basename(video.file.name)}"
    
    # Converte o tempo de start e end para HH:MM:ss
    for phrase in video.transcription_phrases:
        phrase['start'] = format_time(float(phrase['start']))
        phrase['end'] = format_time(float(phrase['end']))

    # Renderiza o template passando o contexto com o vídeo
    return render(request, 'core/video_detail.html', {'video': video})

def format_duration(duration):
    """Converte um objeto `timedelta` ou `datetime.time` em uma string formatada HH:MM:SS"""
    if isinstance(duration, timedelta):
        total_seconds = int(duration.total_seconds())
    elif isinstance(duration, time):
        total_seconds = duration.hour * 3600 + duration.minute * 60 + duration.second
    else:
        total_seconds = int(duration)
        
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f'{hours:02}:{minutes:02}:{seconds:02}'

def convert_seconds_to_hms(seconds):
    """Converte tempo em segundos para o formato HH:MM:SS"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = int(seconds % 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}"

def set_cell_vertical_alignment(cell, alignment):
    """Alinha verticalmente o conteúdo da célula ao centro"""
    tc = cell._element
    tcPr = tc.get_or_add_tcPr()
    tcVAlign = OxmlElement('w:vAlign')
    tcVAlign.set(ns.qn('w:val'), alignment)
    tcPr.append(tcVAlign)

def set_cell_margins(cell, top=0, bottom=0):
    """Configura as margens internas superior e inferior da célula"""
    tc = cell._element
    tcPr = tc.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    tcMar.set(ns.qn('w:top'), str(top))
    tcMar.set(ns.qn('w:bottom'), str(bottom))
    tcPr.append(tcMar)

def generate_docx(request, video_id):
    video = get_object_or_404(Video, id=video_id)
    
    # Cria o documento
    doc = Document()

    # Configurações do documento - A4 é 210 x 297 mm
    section = doc.sections[0]
    section.page_width = Mm(210)   # 210 mm
    section.page_height = Mm(297)  # 297 mm
    section.left_margin = Mm(30)   # 30 mm para a margem esquerda
    section.right_margin = Mm(25)  # 25 mm para a margem direita
    section.top_margin = Mm(20)    # 25 mm para a margem superior
    section.bottom_margin = Mm(20) # 25 mm para a margem inferior

    # Título
    title = doc.add_heading(f'Transcrição do Vídeo: {video.file.name}', level=1)
    title.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER

    # Ajusta o tamanho da fonte do título
    run = title.runs[0]
    run.font.name = 'Arial'
    run.font.size = Pt(14)

    # Cria a tabela para a transcrição
    if video.transcription_phrases:
        table = doc.add_table(rows=1, cols=2)
        table.style = 'Table Grid'
        table.autofit = True 
        table.allow_autofit = False
        table.width = Mm(section.page_width - section.left_margin - section.right_margin)
        hdr_cells = table.rows[0].cells
        hdr_cells[0].text = 'Início'
        for paragraph in hdr_cells[0].paragraphs:
                paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
        hdr_cells[1].text = 'Texto'
        for paragraph in hdr_cells[1].paragraphs:
                paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
        
        # Define as células da primeira linha como cabeçalhos
        hdr_cells[0].paragraphs[0].runs[0].font.bold = True
        hdr_cells[1].paragraphs[0].runs[0].font.bold = True

        # Repete a linha de cabeçalho em todas as páginas
        tbl = table._tbl
        tbl_header = tbl.xpath(".//w:tr")[0]
        tbl_header_pr = tbl_header.get_or_add_trPr()
        tbl_header_pr.append(OxmlElement('w:tblHeader'))

        for phrase in video.transcription_phrases:
            row_cells = table.add_row().cells
            # Converta o tempo de início para HH:MM:SS e remova espaços
            start_time = convert_seconds_to_hms(float(phrase['start'])).strip()
            row_cells[0].text = start_time
            row_cells[0].width = Mm(20)  # Ajusta a largura da coluna de início
            for paragraph in row_cells[0].paragraphs:
                paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
                
            # Remove espaços e ajusta o alinhamento do texto
            text_content = str(phrase['text']).strip()
            row_cells[1].text = text_content
            row_cells[1].width = Mm(section.page_width - section.left_margin - section.right_margin - 20)
            for paragraph in row_cells[1].paragraphs:
                paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.JUSTIFY

            # Ajusta o alinhamento vertical e margens internas das células
            # for cell in row_cells:
                
        # Ajustar o tamanho da fonte da tabela
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    for run in paragraph.runs:
                        run.font.name = 'Arial'
                        run.font.size = Pt(12)
                        
                set_cell_vertical_alignment(cell, 'center')
                set_cell_margins(cell, top=Mm(2.5), bottom=Mm(2.5))  # 0,25 cm em pontos

    else:
        doc.add_paragraph("Transcrição não disponível.")

    # Gera o arquivo DOCX
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
    response['Content-Disposition'] = f'attachment; filename={video.file.name}.docx'
    doc.save(response)
    return response

def gallery_view(request):
    videos = Video.objects.all()
    for video in videos:
        # Certifique-se de que cada vídeo tem a duração formatada
        video.formatted_duration = format_duration(video.duration)
    return render(request, 'core/gallery.html', {'videos': videos})