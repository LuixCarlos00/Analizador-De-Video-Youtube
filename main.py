from pytubefix import YouTube, Playlist
import re
import os
import subprocess
import tkinter as tk
from tkinter import messagebox
from google.cloud import speech
import io

def open_folder(path):
    # Verifica o sistema operacional e executa o comando apropriado para abrir a pasta
    if os.name == 'nt':  # Windows
        os.startfile(path)
    elif os.name == 'posix':  # macOS e Linux
        subprocess.Popen(['open', path] if sys.platform == 'darwin' else ['xdg-open', path])

def download_video(video_url, output_path=None):
    try:
        if output_path is None:
            user_home = os.path.expanduser("~")
            output_path = os.path.join(user_home, "Videos_Downloads")

        output_dir = os.path.dirname(output_path)

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        yt = YouTube(video_url)

        # Verifica se o vídeo está disponível
        if yt.streams.filter(progressive=True).first() is None:
            raise Exception("O vídeo não está disponível para download.")

        stream = yt.streams.get_highest_resolution()
        stream.download(output_path=output_path)
        messagebox.showinfo("Sucesso", f"Vídeo baixado com sucesso!\n\nSalvo em: {output_path}\n\nVocê pode encontrar seu vídeo na pasta 'Vídeos_Downloads'.")
        open_folder(output_path)
    except Exception as e:
        messagebox.showerror("Erro", f"Ocorreu um erro ao baixar o vídeo: {e}")



def download_audio(video_url, output_path=None):
    try:
        if output_path is None:
            user_home = os.path.expanduser("~")
            output_path = os.path.join(user_home, "Audios_Downloads")

        if not os.path.exists(output_path):
            os.makedirs(output_path)

        yt = YouTube(video_url)
        stream = yt.streams.get_audio_only()
        stream.download(output_path=output_path)
        messagebox.showinfo("Sucesso", f"Áudio baixado com sucesso e salvo em: {output_path}/{yt.title}.mp3")
        open_folder(output_path)
    except Exception as e:
        messagebox.showerror("Erro", f"Ocorreu um erro ao baixar o áudio: {e}")

def is_valid_url(url):
    regex = r'^(https?://)?(www\.)?(youtube\.com|youtu\.?be)/.+$'
    return re.match(regex, url) is not None



def download_multiple_videos(urls, download_function):
    for url in urls:
        url = url.strip()
        if is_valid_url(url):
            download_function(url)
        else:
            messagebox.showwarning("URL Inválido", f"URL inválido: {url}")



def on_download_video():
    video_url = entry_video.get()
    if is_valid_url(video_url):
        download_video(video_url)
    else:
        messagebox.showwarning("URL Inválido", "Por favor, insira um link válido do YouTube.")

def on_download_audio():
    video_url = entry_audio.get()
    if is_valid_url(video_url):
        download_audio(video_url)
    else:
        messagebox.showwarning("URL Inválido", "Por favor, insira um link válido do YouTube.")

def on_download_multiple_videos():
    video_urls = entry_multiple_videos.get()
    urls_list = video_urls.split(',')
    download_multiple_videos(urls_list, download_video)

def on_download_multiple_audios():
    video_urls = entry_multiple_audios.get()
    urls_list = video_urls.split(',')
    download_multiple_videos(urls_list, download_audio)
    
    
    
    
def on_transcribe_audio(output_path=None):
    audio_filename = entry_transcribe.get()
     
    if not os.path.exists(output_path):
            os.makedirs(output_path)
            
    audio_path = os.path.join(output_path, audio_filename)   
    if os.path.exists(audio_path):
        transcribe_audio(audio_path)
    else:
        messagebox.showwarning("Arquivo Inválido", "Por favor, insira um caminho válido para o arquivo de áudio.")

   
    
    
def transcribe_audio(file_path):
    client = speech.SpeechClient()

    with io.open(file_path, "rb") as audio_file:
        content = audio_file.read()

    audio = speech.RecognitionAudio(content=content)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=16000,
        language_code="pt-BR",
    ) 
    
    
    
    
    
    
def toggle_dark_mode():
    if root.cget("bg") == "white":
        root.config(bg="black")
        dark_mode_button.config(bg="grey", fg="white")
        for frame in [frame_video, frame_multiple_videos, frame_transcribe]:
            frame.config(bg="black")
            for widget in frame.winfo_children():
                widget.config(bg="black", fg="white")
        for widget in root.winfo_children():
            widget.config(bg="black", fg="white")
    else:
        root.config(bg="white")
        dark_mode_button.config(bg="white", fg="black")
        for frame in [frame_video, frame_multiple_videos,  frame_transcribe]:
            frame.config(bg="white")
            for widget in frame.winfo_children():
                widget.config(bg="white", fg="black")
        for widget in root.winfo_children():
            widget.config(bg="white", fg="black")










root = tk.Tk()
root.geometry('1000x500')
root.title("Downloader de Vídeos e Áudios do YouTube")



frame_video = tk.Frame(root)
frame_video.pack(pady=10)

tk.Label(frame_video, text="Baixar Vídeo").grid(row=0, column=0, sticky="w", padx=5) 
entry_video = tk.Entry(frame_video, width=75)
entry_video.grid(row=1, column=0, padx=5)  
tk.Button(frame_video, text="Baixar Vídeo", command=on_download_video).grid(row=2, column=0, sticky="w", padx=5) 
 
tk.Label(frame_video, text="Baixar Áudio").grid(row=0, column=1, sticky="w", padx=5)
entry_audio = tk.Entry(frame_video, width=75)
entry_audio.grid(row=1, column=1, padx=5)
tk.Button(frame_video, text="Baixar Áudio", command=on_download_audio).grid(row=2, column=1, sticky="w", padx=5)



frame_multiple_videos = tk.Frame(root)
frame_multiple_videos.pack(pady=20)

tk.Label(frame_multiple_videos, text="Baixar Múltiplos Vídeos ").grid(row=0, column=0, sticky="w", padx=5)
tk.Label(frame_multiple_videos, text="(Separados os links por vírgula)").grid(row=1, column=0, sticky="w", padx=5)
entry_multiple_videos = tk.Text(frame_multiple_videos, width=57, height=4)
entry_multiple_videos.grid(row=2, column=0, padx=5)
tk.Button(frame_multiple_videos, text="Baixar Múltiplos Vídeos", command=on_download_multiple_videos).grid(row=3, column=0, sticky="w", padx=5)
 

tk.Label(frame_multiple_videos, text="Baixar Múltiplos Áudios").grid(row=0, column=1, sticky="w", padx=5)
tk.Label(frame_multiple_videos, text="(Separados os links por vírgula)").grid(row=1, column=1, sticky="w", padx=5)
entry_multiple_audios = tk.Text(frame_multiple_videos, width=57, height=4)
entry_multiple_audios.grid(row=2, column=1, padx=5)
tk.Button(frame_multiple_videos, text="Baixar Múltiplos Áudios", command=on_download_multiple_audios).grid(row=3, column=1, sticky="w", padx=5)



frame_transcribe = tk.Frame(root, bg="white")
frame_transcribe.pack(pady=10)

tk.Label(frame_transcribe, text="Transcrever Áudio", bg="white").grid(row=0, column=0, sticky="w", padx=5)
entry_transcribe = tk.Entry(frame_transcribe, width=75, bg="white")
entry_transcribe.grid(row=1, column=0, padx=5)
tk.Button(frame_transcribe, text="Transcrever", command=on_transcribe_audio, bg="white").grid(row=2, column=0, sticky="w", padx=5)


dark_mode_button = tk.Button(root, text="Modo Escuro", command=toggle_dark_mode, bg="white")
dark_mode_button.pack(pady=10)

tk.Button(root, text="Sair", command=root.quit).pack(pady=20, side="bottom")

root.mainloop()
