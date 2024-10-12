from pytubefix import YouTube, Playlist
import re
import os
import subprocess
import threading
import tkinter as tk
from tkinter import messagebox, ttk
import whisper
import sys
from tkinter import filedialog
   
cancel_download = False




def open_folder(path):
    if os.name == 'nt':
        os.startfile(path)
    elif os.name == 'posix':
        subprocess.Popen(['open', path] if sys.platform == 'darwin' else ['xdg-open', path])





def download_video(video_url):
    global cancel_download
    cancel_download = False
    
    def _download():
        try:
            user_home = os.path.expanduser("~")
            output_path = os.path.join(user_home, "Videos_Downloads")

            if not os.path.exists(output_path):
                os.makedirs(output_path)

            yt = YouTube(video_url, on_progress_callback=progress_callback)

            if yt.streams.filter(progressive=True).first() is None:
                raise Exception("O vídeo não está disponível para download.")

            stream = yt.streams.get_highest_resolution()

            stream.download(output_path=output_path)
            if not cancel_download:
                messagebox.showinfo("Sucesso", f"Vídeo baixado com sucesso!\n\nSalvo em: {output_path}\n\nVocê pode encontrar seu vídeo na pasta 'Vídeos_Downloads'.")
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






def download_audio(video_url):
    global cancel_download
    cancel_download = False

    def _download():
        try:
            user_home = os.path.expanduser("~")
            output_path = os.path.join(user_home, "Audios_Downloads")

            if not os.path.exists(output_path):
                os.makedirs(output_path)

            yt = YouTube(video_url, on_progress_callback=progress_callback)
            stream = yt.streams.get_audio_only()

            stream.download(output_path=output_path)
            if not cancel_download:
                messagebox.showinfo("Sucesso", f"Áudio baixado com sucesso e salvo em: {output_path}/{yt.title}.mp3")
                open_folder(output_path)
        except Exception as e:
            if not cancel_download:
                messagebox.showerror("Erro", f"Ocorreu um erro ao baixar o áudio: {e}")
        finally:
            progress['value'] = 0
            progress_label.config(text="")
            cancel_button.pack_forget()
            cancel_button.config(command=None)

    thread = threading.Thread(target=_download)
    thread.start()







def progress_callback(stream, chunk, bytes_remaining):
    total_size = stream.filesize
    bytes_downloaded = total_size - bytes_remaining
    percentage = (bytes_downloaded / total_size) * 100
    progress['value'] = percentage
    progress_label.config(text=f"{percentage:.2f}%")






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
    global cancel_download
    cancel_download = False
    video_url = entry_video.get()
    if is_valid_url(video_url):
        download_video(video_url)
        cancel_button.pack()
        cancel_button.config(command=on_cancel_download)
    else:
        messagebox.showwarning("URL Inválido", "Por favor, insira um link válido do YouTube.")





def on_download_audio():
    global cancel_download
    cancel_download = False
    video_url = entry_audio.get()
    if is_valid_url(video_url):
        download_audio(video_url)
        cancel_button.pack()
        cancel_button.config(command=on_cancel_download)
    else:
        messagebox.showwarning("URL Inválido", "Por favor, insira um link válido do YouTube.")




def on_cancel_download():
    global cancel_download
    cancel_download = True
    messagebox.showinfo("Cancelado", "O download foi cancelado.")
    progress['value'] = 0
    progress_label.config(text="")
    cancel_button.pack_forget()
    cancel_button.config(command=None)






def on_download_multiple_videos():
    video_urls = entry_multiple_videos.get("1.0", tk.END)
    urls_list = video_urls.split(',')
    download_multiple_videos(urls_list, download_video)

def on_download_multiple_audios():
    video_urls = entry_multiple_audios.get("1.0", tk.END)
    urls_list = video_urls.split(',')
    download_multiple_videos(urls_list, download_audio)




 

 





def toggle_dark_mode():
    if root.cget("bg") == "#1a1a1a":  #escuro
        root.config(bg="MidnightBlue")   
        dark_mode_button.config(bg="#007BFF", fg="white")   
        for frame in [frame_video, frame_multiple_videos,frame_progress]:
            frame.config(bg="MidnightBlue")
            for widget in frame.winfo_children():
                widget.config(bg="MidnightBlue", fg="white")
        for widget in root.winfo_children():
            widget.config(bg="MidnightBlue", fg="white")
    else:  # Claro
        root.config(bg="#1a1a1a")   
        dark_mode_button.config(bg="#007BFF", fg="black")
        for frame in [frame_video, frame_multiple_videos,frame_progress]:
            frame.config(bg="#1a1a1a")
            for widget in frame.winfo_children():
                widget.config(bg="#1a1a1a", fg="white")
        for widget in root.winfo_children():
            widget.config(bg="#1a1a1a", fg="white")

root = tk.Tk()
root.geometry('1000x600')
root.title("Downloader de Vídeos e Áudios do YouTube")

root.config(bg="MidnightBlue")  
frame_video = tk.Frame(root, bg="MidnightBlue")  
frame_video.pack(pady=10)


tk.Label(frame_video, text="Baixar Vídeo").grid(row=0, column=0, sticky="w", padx=5, pady=(5, 0))
entry_video = tk.Entry(frame_video, width=75)
entry_video.grid(row=1, column=0,  padx=5, pady=5)
tk.Button(frame_video, text="Baixar Vídeo", command=on_download_video).grid(row=2, column=0, sticky="w",  padx=5, pady=5)

tk.Label(frame_video, text="Baixar Áudio").grid(row=0, column=2, sticky="w", padx=5, pady=(5, 0))
entry_audio = tk.Entry(frame_video, width=75)
entry_audio.grid(row=1, column=2,  padx=5, pady=5)
tk.Button(frame_video, text="Baixar Áudio", command=on_download_audio).grid(row=2, column=2, sticky="w",  padx=5, pady=5)



frame_multiple_videos = tk.Frame(root, bg="MidnightBlue")
frame_multiple_videos.pack(pady=20)

tk.Label(frame_multiple_videos, text="Baixar Múltiplos Vídeos ").grid(row=0, column=0, sticky="w",  padx=5, pady=5)
tk.Label(frame_multiple_videos, text="(Separados os links por vírgula)").grid(row=1, column=0, sticky="w",  padx=5, pady=5)
entry_multiple_videos = tk.Text(frame_multiple_videos, width=56, height=4)
entry_multiple_videos.grid(row=2, column=0,  padx=5, pady=5)
tk.Button(frame_multiple_videos, text="Baixar Múltiplos Vídeos", command=on_download_multiple_videos).grid(row=3, column=0, sticky="w",  padx=5, pady=5)

tk.Label(frame_multiple_videos, text="Baixar Múltiplos Áudios ").grid(row=0, column=1, sticky="w",  padx=5, pady=5)
tk.Label(frame_multiple_videos, text="(Separados os links por vírgula)").grid(row=1, column=1, sticky="w",  padx=5, pady=5)
entry_multiple_audios = tk.Text(frame_multiple_videos, width=56, height=4)
entry_multiple_audios.grid(row=2, column=1,  padx=5, pady=5)
tk.Button(frame_multiple_videos, text="Baixar Múltiplos Áudios", command=on_download_multiple_audios).grid(row=3, column=1, sticky="w",  padx=5, pady=5)



frame_progress = tk.Frame(root, bg="MidnightBlue")
frame_progress.pack(pady=10)

progress = ttk.Progressbar(frame_progress, orient="horizontal", length=800, mode="determinate", maximum=100 ) 
progress.pack(pady=10)
progress_label = tk.Label(frame_progress, text="")
progress_label.pack()


cancel_button = tk.Button(root, text="Cancelar Download")

dark_mode_button = tk.Button(root, text="Modo Escuro/Claro", command=toggle_dark_mode)
dark_mode_button.pack(pady=10)

root.mainloop()
