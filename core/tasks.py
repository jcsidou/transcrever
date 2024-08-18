import json
import os
from pydub import AudioSegment
from .models import Video
import whisper
import logging
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import torch
from pyannote.audio import Pipeline
import pyannote.audio

# Configurar o logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

# Verificar se a GPU está disponível e carregar o modelo no dispositivo apropriado
device = "cuda" if torch.cuda.is_available() else "cpu"
log_message = lambda message: logging.info(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {message}")

log_message(f"Dispositivo de processamento: {'GPU' if device == 'cuda' else 'CPU'}")

# Defina o caminho para o diretório de áudios
# AUDIO_DIR = os.path.join(os.path.dirname(__file__), 'audios')
VIDEO_DIR = 'videos/'
AUDIO_DIR = 'media/audios/'

# Certifique-se de que o diretório de áudios existe
os.makedirs(AUDIO_DIR, exist_ok=True)

def process_video(video_id):
    log_message(f"Iniciando processamento do vídeo {video_id}...")  # Log adicional para iniciar o processo
    video = Video.objects.get(id=video_id)
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
            audio = AudioSegment.from_file(video.file.path)
            audio.export(mp3_path, format="mp3")
            video.error_on_convert = False
            log_message(f"Vídeo {video_id} convertido para MP3 com sucesso em {mp3_path}.")
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

            log_message(f"Versão da pyannote.audio: {pyannote.audio.__version__}")
            result = model.transcribe(mp3_path, fp16=False, language='pt', word_timestamps=True)  # Força a transcrição para Português do Brasil
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
                log_message(f"Tamanho do arquivo MP3: {os.path.getsize(mp3_path)} bytes")
                log_message(f"Duração do áudio: {AudioSegment.from_mp3(mp3_path).duration_seconds} segundos")
                
                diarization_pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization", use_auth_token="YOUR_HUGGINGFACE_TOKEN")
                
                if torch.cuda.is_available():
                    diarization_pipeline = diarization_pipeline.to(torch.device('cuda:0'))
                    log_message("Usando GPU para diarização.")
                else:
                    log_message("GPU não disponível. Usando CPU para diarização.")
                
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

                # diarization_str = ""
                # for turn, _, speaker in diarization.itertracks(yield_label=True):
                #     log_message(f"Processando: Speaker {speaker} from {turn.start:.1f}s to {turn.end:.1f}s")
                #     diarization_str += f"Speaker {speaker} from {turn.start:.1f}s to {turn.end:.1f}s\n"
                
                # if diarization_str:
                #     video.diarization = diarization_str
                #     video.is_diarized = True
                #     video.error_on_diarization = False
                #     log_message(f"Vídeo {video_id} diarizado com sucesso.")
                # else:
                #     video.is_diarized = False
                #     video.error_on_diarization = True
                #     log_message(f"Diarização do vídeo {video_id} não retornou nenhum resultado.")

            except Exception as e:
                video.error_on_diarization = True
                log_message(f"Erro ao diarizar vídeo {video_id}: {str(e)}")
                import traceback
                log_message(f"Traceback completo: {traceback.format_exc()}")
            finally:
                
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    log_message("Memória da GPU liberada após a diarização.")
        video.save()
        os.remove(mp3_path)
        log_message(f"Arquivo de áudio {mp3_path} removido após a transcrição.")
    
    except Exception as e:
        log_message(f"Erro geral ao processar o vídeo {video_id}: {e}")
        video.save()
                
def process_videos_in_parallel(video_ids):
    """Processa múltiplos vídeos em paralelo."""
    with ThreadPoolExecutor() as executor:
        executor.map(process_video, video_ids)

# Exemplo de uso:
# video_ids = [1, 2, 3, 4, 5]  # IDs dos vídeos que você quer processar
# process_videos_in_parallel(video_ids)

                
def is_gpu_available():
    if torch.cuda.is_available():
        try:
            torch.cuda.init()
            return True
        except RuntimeError:
            return False
    return False

