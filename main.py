from pytubefix import YouTube, Playlist
import re
import os 
import subprocess
import threading
import tkinter as tk
from tkinter import messagebox, ttk
from google.cloud import speech
import io
from moviepy.editor import AudioFileClip

# Variável global para controlar o cancelamento
cancel_download = False

def open_folder(path):
    if os.name == 'nt':
        os.startfile(path)
    elif os.name == 'posix':
        subprocess.Popen(['open', path] if sys.platform == 'darwin' else ['xdg-open', path])

# Função para baixar um vídeo
def download_video(video_url):
    global cancel_download
    cancel_download = False

    def _download():
        try:
            user_home = os.path.expanduser("~")
            output_path = os.path.join(user_home, "Videos_Downloads")

            if not os.path.exists(output_path):
                os.makedirs(output_path)

            yt = YouTube(video_url)

            if yt.streams.filter(progressive=True).first() is None:
                raise Exception("O vídeo não está disponível para download.")

            stream = yt.streams.get_highest_resolution()
            stream.download(output_path=output_path)

            if not cancel_download:
                messagebox.showinfo("Sucesso", f"Vídeo baixado com sucesso!\n\nSalvo em: {output_path}\n\nVocê pode encontrar seu vídeo na pasta 'Videos_Downloads'.")
                open_folder(output_path)
        except Exception as e:
            if not cancel_download:
                messagebox.showerror("Erro", f"Ocorreu um erro ao baixar o vídeo: {e}")
        finally:
            progress['value'] = 0
            progress_label.config(text="")
            cancel_button.pack_forget()
            cancel_button.config(command=None)

    thread = threading.Thread(target=_download)
    thread.start()

# Função para baixar um áudio
def download_audio(video_url, output_path):
    global cancel_download
    cancel_download = False

    def _download():
        try:
            yt = YouTube(video_url)
            audio_stream = yt.streams.filter(only_audio=True).first()
            print(f'Iniciando download do áudio: {yt.title}')  # Depuração
            output_file = audio_stream.download(output_path=output_path)
            audio_path = os.path.splitext(output_file)[0] + ".mp3"

            # Renomear o arquivo para ter extensão .mp3
            os.rename(output_file, audio_path)

            if not cancel_download:
                messagebox.showinfo("Sucesso", f"Áudio baixado com sucesso e salvo em: {audio_path}")
                open_folder(output_path)
        except Exception as e:
            if not cancel_download:
                print(f'Ocorreu um erro ao baixar o áudio: {e}')  # Depuração
                messagebox.showerror("Erro", f"Ocorreu um erro ao baixar o áudio: {e}")
        finally:
            progress['value'] = 0
            progress_label.config(text="")
            cancel_button.pack_forget()
            cancel_button.config(command=None)

    thread = threading.Thread(target=_download)
    thread.start()

# Função de progresso
def progress_callback(stream, chunk, bytes_remaining):
    if cancel_download:
        return
    total_size = stream.filesize
    bytes_downloaded = total_size - bytes_remaining
    percentage = (bytes_downloaded / total_size) * 100
    progress['value'] = percentage
    progress_label.config(text=f"{percentage:.2f}%")

# Função para verificar se é uma URL válida
def is_valid_url(url):
    regex = r'^(https?://)?(www\.)?(youtube\.com|youtu\.?be)/.+$'
    return re.match(regex, url) is not None

# Função para baixar múltiplos vídeos
def download_multiple_videos(urls, download_function):
    for url in urls:
        url = url.strip()
        if is_valid_url(url):
            download_function(url)
        else:
            messagebox.showwarning("URL Inválido", f"URL inválido: {url}")

# Funções de download
def on_download_video():
    video_url = entry_video.get()
    if is_valid_url(video_url):
        download_video(video_url)
        cancel_button.pack()
        cancel_button.config(command=on_cancel_download)
    else:
        messagebox.showwarning("URL Inválido", "Por favor, insira um link válido do YouTube.")

# Função de download de áudio
def on_download_audio():
    video_url = entry_audio.get()
    if is_valid_url(video_url):
        user_home = os.path.expanduser("~")
        output_path = os.path.join(user_home, "Audio_Downloads")
        if not os.path.exists(output_path):
            os.makedirs(output_path)
        download_audio(video_url, output_path)
        cancel_button.pack()
        cancel_button.config(command=on_cancel_download)
    else:
        messagebox.showwarning("URL Inválido", "Por favor, insira um link válido do YouTube.")

# Função de cancelamento
def on_cancel_download():
    global cancel_download
    cancel_download = True
    messagebox.showinfo("Cancelado", "O download foi cancelado.")
    progress['value'] = 0
    progress_label.config(text="")
    cancel_button.pack_forget()
    cancel_button.config(command=None)

# Função para baixar múltiplos arquivos
def on_download_multiple_videos():
    video_urls = entry_multiple_videos.get("1.0", tk.END)
    urls_list = video_urls.split(',')
    download_multiple_videos(urls_list, download_video)

# Função para baixar múltiplos arquivos
def on_download_multiple_audios():
    video_urls = entry_multiple_audios.get("1.0", tk.END)
    urls_list = video_urls.split(',')
    download_multiple_videos(urls_list, download_audio)

def download_audio_from_youtube(url, output_path):
    try:
        # Baixar o áudio do YouTube usando pytubefix
        yt = YouTube(url)
        audio_stream = yt.streams.filter(only_audio=True).first()
        
        if audio_stream:
            output_file = audio_stream.download(output_path=output_path)
            audio_path = os.path.splitext(output_file)[0] + ".mp3"

            # Renomear o arquivo para ter extensão .mp3
            os.rename(output_file, audio_path)
            return audio_path
        else:
            print("Nenhum stream de áudio disponível.")
            return None
    except Exception as e:
        print(f"Erro ao baixar ou converter o vídeo: {e}")
        return None

def on_transcribe_audio():
    # Obter a URL do YouTube a partir do campo de entrada
    youtube_url = entry_transcribe.get().strip()
    print('URL do YouTube inserida:', youtube_url)

    # Obter o diretório do usuário
    user_home = os.path.expanduser("~")
    print('Diretório do usuário:', user_home)

    # Criar o caminho de saída para salvar as transcrições
    output_path = os.path.join(user_home, "Transcriptions")
    print('Caminho de saída para transcrições:', output_path)

    # Se o diretório de saída não existir, criar o diretório
    if not os.path.exists(output_path):
        os.makedirs(output_path)
        print('Diretório "Transcriptions" criado.')

    # Baixar e converter o vídeo do YouTube em áudio
    audio_path = download_audio_from_youtube(youtube_url, output_path)
    
    if audio_path and os.path.exists(audio_path):
        print('Arquivo de áudio encontrado. Iniciando transcrição...')
        # Chamar a função de transcrição
        transcribe_audio(audio_path)
    else:
        print('Arquivo de áudio não encontrado.')
        messagebox.showwarning("Arquivo Inválido", "Por favor, insira uma URL válida do YouTube.")

def transcribe_audio(audio_path):
    # Implementação da transcrição do áudio
    print(f'Transcrevendo o áudio: {audio_path}')

    # Use a biblioteca Google Speech para transcrição
    client = speech.SpeechClient()

    with io.open(audio_path, "rb") as audio_file:
        content = audio_file.read()

    audio = speech.RecognitionAudio(content=content)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=16000,
        language_code="pt-BR",
    )

    response = client.recognize(config=config, audio=audio)

    # Criar um arquivo de texto para salvar a transcrição
    transcription_path = os.path.splitext(audio_path)[0] + ".txt"
    with open(transcription_path, "w") as f:
        for result in response.results:
            f.write(result.alternatives[0].transcript + "\n")
    
    print(f'Transcrição concluída e salva em: {transcription_path}')
    messagebox.showinfo("Transcrição Completa", f"Transcrição salva em: {transcription_path}")

def toggle_dark_mode():
    if root.cget("bg") == "white":
        root.config(bg="black")
        dark_mode_button.config(bg="grey", fg="white")
        for frame in [frame_video, frame_multiple_videos, frame_transcribe]:
            frame.config(bg="black")
            for widget in frame.winfo_children():
                widget.config(bg="black", fg="white")
        for widget in [progress, progress_label, cancel_button]:
            widget.config(bg="black", fg="white")
    else:
        root.config(bg="white")
        dark_mode_button.config(bg="white", fg="black")
        for frame in [frame_video, frame_multiple_videos, frame_transcribe]:
            frame.config(bg="white")
            for widget in frame.winfo_children():
                widget.config(bg="white", fg="black")
        for widget in [progress, progress_label, cancel_button]:
            widget.config(bg="white", fg="black")

# Configuração da interface gráfica
root = tk.Tk()
root.title("YouTube Downloader e Transcriber")
root.geometry("500x500")

# Frames para diferentes funcionalidades
frame_video = ttk.LabelFrame(root, text="Baixar Vídeo")
frame_video.pack(padx=10, pady=10, fill="x")

entry_video = tk.Entry(frame_video, width=50)
entry_video.pack(padx=10, pady=10)
button_download_video = tk.Button(frame_video, text="Baixar Vídeo", command=on_download_video)
button_download_video.pack(padx=10, pady=10)

frame_multiple_videos = ttk.LabelFrame(root, text="Baixar Múltiplos Vídeos")
frame_multiple_videos.pack(padx=10, pady=10, fill="x")

entry_multiple_videos = tk.Text(frame_multiple_videos, height=5, width=60)
entry_multiple_videos.pack(padx=10, pady=10)
button_download_multiple_videos = tk.Button(frame_multiple_videos, text="Baixar Múltiplos Vídeos", command=on_download_multiple_videos)
button_download_multiple_videos.pack(padx=10, pady=10)

frame_transcribe = ttk.LabelFrame(root, text="Transcrever Áudio")
frame_transcribe.pack(padx=10, pady=10, fill="x")

entry_transcribe = tk.Entry(frame_transcribe, width=50)
entry_transcribe.pack(padx=10, pady=10)
button_transcribe_audio = tk.Button(frame_transcribe, text="Transcrever Áudio", command=on_transcribe_audio)
button_transcribe_audio.pack(padx=10, pady=10)

entry_audio = tk.Entry(root, width=50)
entry_audio.pack(padx=10, pady=10)
button_download_audio = tk.Button(root, text="Baixar Áudio", command=on_download_audio)
button_download_audio.pack(padx=10, pady=10)

progress = ttk.Progressbar(root, orient="horizontal", length=300, mode="determinate")
progress.pack(padx=10, pady=10)

progress_label = tk.Label(root, text="")
progress_label.pack(padx=10, pady=10)

cancel_button = tk.Button(root, text="Cancelar Download", command=on_cancel_download)

dark_mode_button = tk.Button(root, text="Alternar Modo Escuro", command=toggle_dark_mode)
dark_mode_button.pack(pady=10)

root.mainloop()
