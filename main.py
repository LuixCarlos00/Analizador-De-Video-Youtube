from pytubefix import YouTube, Playlist
import re
import os
import subprocess
import tkinter as tk
from tkinter import messagebox
from google.cloud import speech
import io

# Define the path for audio transcription
TRANSCRIPTION_PATH = r"C:\Users\luixc\Trascricoes_de_Videos"

def open_folder(path):
    if os.name == 'nt':
        os.startfile(path)
    elif os.name == 'posix':
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

def download_playlist_videos(playlist_url, output_path=None):
    try:
        if output_path is None:
            user_home = os.path.expanduser("~")
            output_path = os.path.join(user_home, "Videos_Downloads")

        pl = Playlist(playlist_url)
        for video in pl.videos:
            download_video(video.watch_url, output_path)
    except Exception as e:
        messagebox.showerror("Erro", f"Ocorreu um erro ao baixar a playlist: {e}")

def download_playlist_audios(playlist_url, output_path=None):
    try:
        if output_path is None:
            user_home = os.path.expanduser("~")
            output_path = os.path.join(user_home, "Audios_Downloads")

        pl = Playlist(playlist_url)
        for video in pl.videos:
            download_audio(video.watch_url, output_path)
    except Exception as e:
        messagebox.showerror("Erro", f"Ocorreu um erro ao baixar a playlist: {e}")

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

    response = client.recognize(config=config, audio=audio)

    for result in response.results:
        print("Transcript: {}".format(result.alternatives[0].transcript))

def on_transcribe_audio():
    audio_filename = entry_transcribe.get()
    audio_path = os.path.join(TRANSCRIPTION_PATH, audio_filename)  # Build the full path
    if os.path.exists(audio_path):
        transcribe_audio(audio_path)
    else:
        messagebox.showwarning("Arquivo Inválido", "Por favor, insira um caminho válido para o arquivo de áudio.")

def is_valid_url(url):
    regex = r'^(https?://)?(www\.)?(youtube\.com|youtu\.?be)/.+$'
    return re.match(regex, url) is not None

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

def on_download_playlist_videos():
    playlist_url = entry_playlist_videos.get()
    if is_valid_url(playlist_url):
        download_playlist_videos(playlist_url)
    else:
        messagebox.showwarning("URL Inválido", "Por favor, insira um link válido da playlist do YouTube.")

def on_download_playlist_audios():
    playlist_url = entry_playlist_audios.get()
    if is_valid_url(playlist_url):
        download_playlist_audios(playlist_url)
    else:
        messagebox.showwarning("URL Inválido", "Por favor, insira um link válido da playlist do YouTube.")

def toggle_dark_mode():
    if root.cget("bg") == "white":
        root.config(bg="black")
        dark_mode_button.config(bg="grey", fg="white")
        for frame in [frame_video, frame_audio, frame_playlist_videos, frame_playlist_audios, frame_transcribe]:
            frame.config(bg="black")
            for widget in frame.winfo_children():
                widget.config(bg="black", fg="white")
        for widget in root.winfo_children():
            widget.config(bg="black", fg="white")
    else:
        root.config(bg="white")
        dark_mode_button.config(bg="white", fg="black")
        for frame in [frame_video, frame_audio, frame_playlist_videos, frame_playlist_audios, frame_transcribe]:
            frame.config(bg="white")
            for widget in frame.winfo_children():
                widget.config(bg="white", fg="black")
        for widget in root.winfo_children():
            widget.config(bg="white", fg="black")

root = tk.Tk()
root.geometry('500x550')
root.title("Downloader de Vídeos e Áudios do YouTube")
root.config(bg="white")

frame_video = tk.Frame(root, bg="white")
frame_video.pack(pady=10)

tk.Label(frame_video, text="Baixar Vídeo", bg="white").grid(row=0, column=0, sticky="w", padx=5)
entry_video = tk.Entry(frame_video, width=75, bg="white")
entry_video.grid(row=1, column=0, padx=5)
tk.Button(frame_video, text="Baixar Vídeo", command=on_download_video, bg="white").grid(row=2, column=0, sticky="w", padx=5)

frame_audio = tk.Frame(root, bg="white")
frame_audio.pack(pady=10)

tk.Label(frame_audio, text="Baixar Áudio", bg="white").grid(row=0, column=0, sticky="w", padx=5)
entry_audio = tk.Entry(frame_audio, width=75, bg="white")
entry_audio.grid(row=1, column=0, padx=5)
tk.Button(frame_audio, text="Baixar Áudio", command=on_download_audio, bg="white").grid(row=2, column=0, sticky="w", padx=5)

frame_playlist_videos = tk.Frame(root, bg="white")
frame_playlist_videos.pack(pady=10)

tk.Label(frame_playlist_videos, text="Baixar Todos os Vídeos da Playlist", bg="white").grid(row=0, column=0, sticky="w", padx=5)
entry_playlist_videos = tk.Entry(frame_playlist_videos, width=75, bg="white")
entry_playlist_videos.grid(row=1, column=0, padx=5)
tk.Button(frame_playlist_videos, text="Baixar Vídeos da Playlist", command=on_download_playlist_videos, bg="white").grid(row=2, column=0, sticky="w", padx=5)

frame_playlist_audios = tk.Frame(root, bg="white")
frame_playlist_audios.pack(pady=10)

tk.Label(frame_playlist_audios, text="Baixar Todos os Áudios da Playlist", bg="white").grid(row=0, column=0, sticky="w", padx=5)
entry_playlist_audios = tk.Entry(frame_playlist_audios, width=75, bg="white")
entry_playlist_audios.grid(row=1, column=0, padx=5)
tk.Button(frame_playlist_audios, text="Baixar Áudios da Playlist", command=on_download_playlist_audios, bg="white").grid(row=2, column=0, sticky="w", padx=5)

frame_transcribe = tk.Frame(root, bg="white")
frame_transcribe.pack(pady=10)

tk.Label(frame_transcribe, text="Transcrever Áudio", bg="white").grid(row=0, column=0, sticky="w", padx=5)
entry_transcribe = tk.Entry(frame_transcribe, width=75, bg="white")
entry_transcribe.grid(row=1, column=0, padx=5)
tk.Button(frame_transcribe, text="Transcrever", command=on_transcribe_audio, bg="white").grid(row=2, column=0, sticky="w", padx=5)

dark_mode_button = tk.Button(root, text="Modo Escuro", command=toggle_dark_mode, bg="white")
dark_mode_button.pack(pady=10)

root.mainloop()
