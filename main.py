from pytubefix import YouTube
import re
import os
import tkinter as tk
from tkinter import messagebox

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


root = tk.Tk()
root.geometry('500x700')
root.title("Downloader de Vídeos e Áudios do YouTube")


frame_video = tk.Frame(root)
frame_video.pack(pady=20)

tk.Label(frame_video, text="Baixar Vídeo").grid(row=0, column=0, sticky="w", padx=5 ) 
entry_video = tk.Entry(frame_video,   width=75)
entry_video.grid(row=1, column=0, padx=5 )  
tk.Button(frame_video, text="Baixar Vídeo", command=on_download_video).grid(row=2, column=0,  sticky="w", padx=5 ) 




frame_audio = tk.Frame(root)
frame_audio.pack(pady=20)

tk.Label(frame_audio, text="Baixar Áudio").grid(row=0, column=0, sticky="w", padx=5 )
entry_audio = tk.Entry(frame_audio, width=75)
entry_audio.grid(row=1, column=0, padx=5 )
tk.Button(frame_audio, text="Baixar Áudio", command=on_download_audio).grid(row=2, column=0, sticky="w", padx=5 )




frame_multiple_videos = tk.Frame(root)
frame_multiple_videos.pack(pady=40)

tk.Label(frame_multiple_videos, text="Baixar Múltiplos Vídeos ").grid(row=0, column=0, sticky="w", padx=5,  )
tk.Label(frame_multiple_videos, text="(Separados os links por vírgula)").grid(row=1, column=0, sticky="w", padx=5,  )
entry_multiple_videos = tk.Text(frame_multiple_videos, width=57 ,height=4)
entry_multiple_videos.grid(row=2, column=0, padx=5 )
tk.Button(frame_multiple_videos, text="Baixar Múltiplos Vídeos", command=on_download_multiple_videos).grid(row=3, column=0, sticky="w", padx=5 )





frame_multiple_audios = tk.Frame(root)
frame_multiple_audios.pack(pady=40)

tk.Label(frame_multiple_audios, text="Baixar Múltiplos Áudios").grid(row=0, column=0, sticky="w", padx=5,  )
tk.Label(frame_multiple_audios, text="(Separados os links por vírgula)").grid(row=1, column=0, sticky="w", padx=5,  )
entry_multiple_audios = tk.Text(frame_multiple_audios,  width=57 ,height=4)
entry_multiple_audios.grid(row=2, column=0, padx=5 )
tk.Button(frame_multiple_audios, text="Baixar Múltiplos Áudios", command=on_download_multiple_audios).grid(row=3, column=0, sticky="w", padx=5 )




tk.Button(root, text="Sair", command=root.quit).pack(pady=20, side="bottom"  )

root.mainloop()
