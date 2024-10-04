import os
from pydub import AudioSegment
import numpy as np
import noisereduce as nr
from .models import Video
import whisper
import logging
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import torch
from pyannote.audio import Pipeline
import pyannote.audio
import threading
from queue import Queue

# Configurar o logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

# Verificar se a GPU está disponível e carregar o modelo no dispositivo apropriado
device = "cuda" if torch.cuda.is_available() else "cpu"
log_message = lambda message: logging.info(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {message}")

log_message(f"Dispositivo de processamento: {'GPU' if device == 'cuda' else 'CPU'}")

# Defina o caminho para o diretório de áudios
VIDEO_DIR = 'videos/'
AUDIO_DIR = 'media/audios/'

# Certifique-se de que o diretório de áudios existe
os.makedirs(AUDIO_DIR, exist_ok=True)
os.makedirs(VIDEO_DIR, exist_ok=True)

# Fila de processamento
video_queue = Queue()

def process_video(video_id):
    log_message(f"Iniciando processamento do vídeo {video_id}...")  # Log adicional para iniciar o processo
    video = Video.objects.get(id=video_id)
    video.in_process = True 
    video.save()
    if not video.file or not os.path.exists(video.file.path):
        return
    
    if video.is_transcribed:
        log_message(f"Vídeo {video_id} já foi transcrito anteriormente. Ignorando novo processamento.")
        return

    try:
        # Extrair o nome do arquivo do vídeo sem o diretório
        video_basename = os.path.basename(video.file.name)
        # Substituir a extensão por .mp3 para o arquivo de áudio
        mp3_filename = f"{os.path.splitext(video_basename)[0]}.mp3"
        # Construir o caminho completo do arquivo MP3
        mp3_path = os.path.join(AUDIO_DIR, mp3_filename)

        try:
            # Verificar se o caminho do vídeo é válido
            if not os.path.exists(video.file.path):
                log_message(f"Arquivo de vídeo {video.file.path} não encontrado.")
                video.error_on_convert = True
                video.save()
                return

            # Converter o vídeo para MP3 e salvar no diretório de áudios
            log_message(f"Iniciando a conversão do Vídeo {video_id} para MP3 em {mp3_path}...")
            video.process_times['video'] = video.file.name
            video.process_times['conversion_start'] = format_datetime(datetime.now())
            audio = AudioSegment.from_file(video.file.path)
            audio.export(mp3_path, format="mp3")
            video.error_on_convert = False
            log_message(f"Vídeo {video_id} convertido para MP3 com sucesso em {mp3_path}.")
            video.process_times['conversion_end'] = format_datetime(datetime.now())
        except Exception as convert_error:
            video.error_on_convert = True
            log_message(f"Erro na conversão do vídeo {video_id} para MP3: {convert_error}")
            video.save()
            return  # Interromper o processo se a conversão falhar
        
        try:
            # Realizar a transcrição usando o arquivo MP3
            log_message(f"Iniciando a transcrição do Vídeo {video_id}...")
            log_message(f"Definindo o modelo: {video.model}")
            model = whisper.load_model(video.model).to(device)
            video.process_times['transcription_device'] = "GPU" if torch.cuda.is_available() else "CPU"
            video.process_times['transcription_start'] = format_datetime(datetime.now())
            result = model.transcribe(mp3_path, fp16=False, language='pt', word_timestamps=True) 
            video.process_times['transcription_end'] = format_datetime(datetime.now())
            video.process_times['model'] = video.model
            log_message(f"Transcrição do Vídeo {video_id} concluída.")
            log_message(f"Salvando o texto...")
            video.transcription = result['text']
            
            log_message(f"Salvando os segmentos...")
            video.transcription_segments = result['segments']
            clean_segments = []
            for segment in result['segments']:
                clean_segments.append({
                    'id': segment['id'],
                    'start': segment['start'],
                    'end': segment['end'],
                    'text': segment['text']
                })
            video.transcription_phrases = clean_segments
            
            log_message(f"Salvando a lista de palavras...")
            word_timestamps = []
            for segment in result['segments']:
                for word in segment['words']:
                    word_timestamps.append({
                        'word': word['word'],
                        'start': word['start'],
                        'end': word['end']
                    })
            video.word_timestamps = word_timestamps
            
            log_message(f"Determinando a duração do vídeo...")
            audio = AudioSegment.from_file(mp3_path)
            audio_duration = len(audio) / 1000.0 
            audio_duration_timedelta = timedelta(seconds=audio_duration)
            video.duration = (datetime.min + audio_duration_timedelta).time()
            video.process_times['lenght'] = len(audio)/1000
            log_message(f"Duração do áudio: {len(audio) / 1000} segundos")
            log_message(f"Máximo dB do áudio: {audio.max_dBFS}")
            
            log_message(f"Ajustando parâmetros do banco de dados...")
            video.is_transcribed = True
            video.error_on_transcript = False
                        
            log_message(f"Transcrição salva no banco de dados.")
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                log_message("Memória da GPU liberada após a transcrição.")
        except Exception as e:
            video.error_on_transcript = True
            log_message(f"Erro ao transcrever vídeo {video_id}: {e}")
            video.save()
            return
        finally:
            video.save()
        
        if not video.diarize:
            log_message(f"Não foi assinalada a diarização.")
        else:
            try:
                log_message(f"Iniciando a diarização do Vídeo {video_id}...")
                video.process_times['diarization_start'] = format_datetime(datetime.now())
                log_message(f"Versão da pyannote.audio: {pyannote.audio.__version__}")
                log_message(f"Tamanho do arquivo MP3: {os.path.getsize(mp3_path)} bytes")
                log_message(f"Duração do áudio: {AudioSegment.from_mp3(mp3_path).duration_seconds} segundos")
                
                diarization_pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization", use_auth_token="YOUR_HUGGINGFACE_TOKEN")
                
                if torch.cuda.is_available():
                    diarization_pipeline = diarization_pipeline.to(torch.device('cuda:0'))
                    log_message("Usando GPU para diarização.")
                else:
                    log_message("GPU não disponível. Usando CPU para diarização.")
                video.process_times['diarization_device'] = "GPU" if torch.cuda.is_available() else "CPU"
                
                log_message("Iniciando a diarização...")
                diarization = diarization_pipeline(mp3_path)
                log_message("Diarização concluída. Processando resultados...")
                
                log_message(f"Conteúdo de diarization: {diarization}")
                log_message(f"Diarization labels: {diarization.labels()}")
                log_message(f"Diarization tracks: {list(diarization.itertracks())}")
                
                diarization_list = []
                for turn, _, speaker in diarization.itertracks(yield_label=True):
                    log_message(f"Processando: Speaker {speaker} from {turn.start:.1f}s to {turn.end:.1f}s")
                    diarization_list.append({
                        "speaker": speaker,
                        "start": round(turn.start, 1),
                        "end": round(turn.end, 1)
                    })

                if diarization_list:
                    video.diarization = diarization_list
                    video.is_diarized = True
                    video.error_on_diarization = False
                    log_message(f"Vídeo {video_id} diarizado com sucesso.")
                else:
                    video.is_diarized = False
                    video.error_on_diarization = True
                    log_message(f"Diarização do vídeo {video_id} não retornou nenhum resultado.")

            except Exception as e:
                video.error_on_diarization = True
                log_message(f"Erro ao diarizar vídeo {video_id}: {str(e)}")
                import traceback
                log_message(f"Traceback completo: {traceback.format_exc()}")
            finally:
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    log_message("Memória da GPU liberada após a diarização.")
                video.process_times['diarization_end'] = format_datetime(datetime.now())
        # video.in_process = False
        # video.calculate_durations()
        # video.save()
        os.remove(mp3_path)
        log_message(f"Arquivo de áudio {mp3_path} removido após a transcrição.")
    
    except Exception as e:
        log_message(f"Erro geral ao processar o vídeo {video_id}: {e}")
        # video.in_process = False
        # video.save()
        # video.calculate_durations()
    
    finally:
        video.in_process = False
        video.calculate_durations()
        video.save()

                
def process_videos_in_parallel(video_ids):
    """Processa múltiplos vídeos em paralelo."""
    with ThreadPoolExecutor() as executor:
        executor.map(process_video, video_ids)


                
def is_gpu_available():
    if torch.cuda.is_available():
        try:
            torch.cuda.init()
            return True
        except RuntimeError:
            return False
    return False

# @shared_task
# def process_video_task(video_id):
#     try:
#         video = Video.objects.get(id=video_id)
#         video.process_video()  # Supondo que você tenha um método `process_video` no modelo Video
#         log_message(f'Vídeo {video_id} processado com sucesso.')
#     except Video.DoesNotExist:
#         log_message(f'Vídeo {video_id} não encontrado para processamento.')
        
def worker():
    while True:
        video_id = video_queue.get()
        try:
            process_video(video_id)
        finally:
            video_queue.task_done()
            
def add_video_to_queue(video_id):
    log_message(f"Adicionando vídeo {video_id} à fila.")
    video_queue.put(video_id)

def format_datetime(dt):
    """Converte um objeto datetime em uma string ISO 8601"""
    return dt.strftime('%Y-%m-%d %H:%M:%S') if dt else None

# Iniciar o worker em uma nova thread
def start_worker():
    threading.Thread(target=worker, daemon=True).start()

def reset_in_process_state():
    Video.objects.filter(in_process=True).update(in_process=False)
    
reset_in_process_state()
# Iniciar o worker ao carregar o módulo
start_worker()