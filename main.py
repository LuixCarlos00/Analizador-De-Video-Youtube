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
import speech_recognition as sr
from pydub import AudioSegment  








cancel_download = False
 

def abrir_Pasta(path):
    if os.name == 'nt':
        os.startfile(path)
    elif os.name == 'posix':
        subprocess.Popen(['open', path] if sys.platform == 'darwin' else ['xdg-open', path])









def triagem_download_multiplos_videos():
    video_urls = entry_multiple_videos.get("1.0", tk.END)
    urls_list = video_urls.split(',')
    downloade_multiplos_videos(urls_list, download_video)


def triagem_video():
    global cancel_download
    cancel_download = False
    video_url = entry_video.get()
    if e_valida_url(video_url):
        download_video(video_url)
        cancel_button.pack()
        cancel_button.config(command=Cancel_download)
    else:
        messagebox.showwarning("URL Inválido", "Por favor, insira um link válido do YouTube.")


def download_video(video_url):
    global cancel_download
    cancel_download = False
    
    def _download():
        try:
            user_home = os.path.expanduser("~")
            output_path = os.path.join(user_home, "Videos_Downloads")

            if not os.path.exists(output_path):
                os.makedirs(output_path)

            yt = YouTube(video_url, on_progress_callback=barra_Progesso)

            if yt.streams.filter(progressive=True).first() is None:
                raise Exception("O vídeo não está disponível para download.")

            stream = yt.streams.get_highest_resolution()

            stream.download(output_path=output_path)
            if not cancel_download:
                messagebox.showinfo("Sucesso", f"Vídeo baixado com sucesso!\n\nSalvo em: {output_path}\n\nVocê pode encontrar seu vídeo na pasta 'Vídeos_Downloads'.")
                abrir_Pasta(output_path)
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














def triagem_download_multiplos_audios():
    video_urls = entry_multiple_audios.get("1.0", tk.END)
    urls_list = video_urls.split(',')
    downloade_multiplos_videos(urls_list, download_audio)


def triagem_audio():
    global cancel_download
    cancel_download = False
    video_url = entry_audio.get()
    if e_valida_url(video_url):
        download_audio(video_url)
        cancel_button.pack()
        cancel_button.config(command=Cancel_download)
    else:
        messagebox.showwarning("URL Inválido", "Por favor, insira um link válido do YouTube.")


def download_audio(video_url):
    global cancel_download
    cancel_download = False

    def _download():
        try:
            user_home = os.path.expanduser("~")
            output_path = os.path.join(user_home, "Audios_Downloads")

            if not os.path.exists(output_path):
                os.makedirs(output_path)

            yt = YouTube(video_url, on_progress_callback=barra_Progesso)
            stream = yt.streams.get_audio_only()

            stream.download(output_path=output_path)
            if not cancel_download:
                messagebox.showinfo("Sucesso", f"Áudio baixado com sucesso e salvo em: {output_path}/{yt.title}.mp3")
                abrir_Pasta(output_path)
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












def triagem_transcricao():
    
    input_file = filedialog.askopenfilename(title="Escolha um arquivo de áudio", filetypes=[("Audio Files", "*.mp3;*.mp4;*.wav")])
    
    if not input_file:
        messagebox.showwarning("Nenhum arquivo selecionado", "Por favor, escolha um arquivo de áudio.")
        return
    
    user_home = os.path.expanduser("~")
    output_path = os.path.join(user_home, "Trascrições")
    
     
    if not os.path.exists(output_path):
        os.makedirs(output_path)
    
    output_file = "converted.wav"
    transcription_file = os.path.join(output_path, "transcricao.txt")   

    try:
        converte_mp3_para_wav(input_file, output_file)
         
        transcription = traducao_Com_Google(output_file)
 
        if transcription:
            entrada_Trascricao.delete(1.0, tk.END)
            entrada_Trascricao.insert(tk.END, transcription)

             
            with open(transcription_file, 'w', encoding='utf-8') as f:
                f.write(transcription)
            
             
            messagebox.showinfo("Sucesso", f"Transcrição salva em: {transcription_file}")
            abrir_Pasta(output_path)   

    except Exception as e:
        messagebox.showerror("Erro", f"Ocorreu um erro: {str(e)}")




def converte_mp3_para_wav(input_file, output_file):
    audio = AudioSegment.from_file(input_file)
    audio.export(output_file, format="wav")


def traducao_Com_Google(file_path):
    recognizer = sr.Recognizer()
    audio = AudioSegment.from_file(file_path)
    
    
    part_length_ms = 10 * 1000  # 10 segundos
    total_parts = len(audio) // part_length_ms + 1  # Total de partes
    transcription = ""

    for i in range(total_parts):
        start_time = i * part_length_ms
        end_time = min((i + 1) * part_length_ms, len(audio))
        audio_part = audio[start_time:end_time]
        print(f"Parte {i + 1} de {total_parts}")
        
        audio_part.export("temp_part.wav", format="wav")
        
        with sr.AudioFile("temp_part.wav") as source:
            audio_data = recognizer.record(source)
        
        try:
             
            text = recognizer.recognize_google(audio_data, language='pt-BR')
            transcription += text + " "
            print(f"Parte {i + 1}: {text}")
        except sr.UnknownValueError:
            print(f"Parte {i + 1} não pôde ser entendida.")
        except sr.RequestError as e:
            print(f"Erro no serviço de reconhecimento de fala; {e}")
            return None
        
         
        barra_ProgressoTrascricao(total_parts, i + 1)
    
    return transcription.strip()
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    

def barra_Progesso(stream, chunk, bytes_remaining):
    total_size = stream.filesize
    bytes_downloaded = total_size - bytes_remaining
    percentage = (bytes_downloaded / total_size) * 100
    progress['value'] = percentage
    progress_label.config(text=f"{percentage:.2f}%")


def barra_ProgressoTrascricao(total_parts, parts_processed):
    percentage = (parts_processed / total_parts) * 100
    progress['value'] = percentage
    progress_label.config(text=f"{percentage:.2f}%")
    root.update_idletasks()


def e_valida_url(url):
    regex = r'^(https?://)?(www\.)?(youtube\.com|youtu\.?be)/.+$'
    return re.match(regex, url) is not None
 

def downloade_multiplos_videos(urls, download_function):
    for url in urls:
        url = url.strip()
        if e_valida_url(url):
            download_function(url)
        else:
            messagebox.showwarning("URL Inválido", f"URL inválido: {url}")
 

def Cancel_download():
    global cancel_download
    cancel_download = True
    messagebox.showinfo("Cancelado", "O download foi cancelado.")
    progress['value'] = 0
    progress_label.config(text="")
    cancel_button.pack_forget()
    cancel_button.config(command=None)

 

def modoDark():
    if root.cget("bg") == "#1a1a1a":  # Escuro
        root.config(bg="MidnightBlue")   
        dark_mode_button.config(bg="#007BFF", fg="white")   
        for frame in [frame_video, frame_multiple_videos,  frame_Trascricao ,button_frame ]:
            frame.config(bg="MidnightBlue")
            for widget in frame.winfo_children():
                widget.config(bg="MidnightBlue", fg="white")
        for widget in root.winfo_children():
            widget.config(bg="MidnightBlue", fg="white")
    else:  # Claro
        root.config(bg="#1a1a1a")   
        dark_mode_button.config(bg="#007BFF", fg="black")
        for frame in [frame_video, frame_multiple_videos, frame_Trascricao,button_frame ]:
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
tk.Button(frame_video, text="Baixar Vídeo", command=triagem_video).grid(row=2, column=0, sticky="w",  padx=5, pady=5)

tk.Label(frame_video, text="Baixar Áudio").grid(row=0, column=2, sticky="w", padx=5, pady=(5, 0))
entry_audio = tk.Entry(frame_video, width=75)
entry_audio.grid(row=1, column=2,  padx=5, pady=5)
tk.Button(frame_video, text="Baixar Áudio", command=triagem_audio).grid(row=2, column=2, sticky="w",  padx=5, pady=5)





frame_multiple_videos = tk.Frame(root, bg="MidnightBlue")
frame_multiple_videos.pack(pady=20)

tk.Label(frame_multiple_videos, text="Baixar Múltiplos Vídeos (Separados os links por vírgula)  ").grid(row=0, column=0, sticky="w",  padx=5, pady=5)
entry_multiple_videos = tk.Text(frame_multiple_videos, width=56, height=4)
entry_multiple_videos.grid(row=2, column=0,  padx=5, pady=5)
tk.Button(frame_multiple_videos, text="Baixar Múltiplos Vídeos", command=triagem_download_multiplos_videos).grid(row=3, column=0, sticky="w",  padx=5, pady=5)

tk.Label(frame_multiple_videos, text="Baixar Múltiplos Áudios (Separados os links por vírgula)  ").grid(row=0, column=1, sticky="w",  padx=5, pady=5)
entry_multiple_audios = tk.Text(frame_multiple_videos, width=56, height=4)
entry_multiple_audios.grid(row=2, column=1,  padx=5, pady=5)
tk.Button(frame_multiple_videos, text="Baixar Múltiplos Áudios", command=triagem_download_multiplos_audios).grid(row=3, column=1, sticky="w",  padx=5, pady=5)



frame_Trascricao = tk.Frame(root, bg="MidnightBlue")
frame_Trascricao.pack(pady=10)

tk.Label(frame_Trascricao, text="Escolha um arquivo de audio para transcrição", bg="MidnightBlue", fg="white").grid(row=0, column=0, sticky="w", padx=5, pady=5)
entrada_Trascricao = tk.Text(frame_Trascricao, width=100, height=4, bg="white", fg="black")
entrada_Trascricao.grid(row=1, column=0, padx=5, pady=5)
tk.Button(frame_Trascricao, text="Buscar", command=triagem_transcricao, bg="#007BFF", fg="white").grid(row=2, column=0, sticky="w", padx=5, pady=5)

 
progress = ttk.Progressbar(frame_Trascricao, orient="horizontal", length=800, mode="determinate", maximum=100)
progress.grid(row=3, column=0, padx=5, pady=5)

progress_label = tk.Label(frame_Trascricao, text="", bg="MidnightBlue", fg="white")
progress_label.grid(row=4, column=0, padx=5, pady=5)

 
 

button_frame = tk.Frame(root, bg="MidnightBlue")  
button_frame.pack(pady=10)   

 
cancel_button = tk.Button(button_frame, text="Cancelar Download", bg="#007BFF", fg="white") 
cancel_button.pack(side=tk.LEFT, padx=5, pady=5)  
 
dark_mode_button = tk.Button(button_frame, text="Modo Escuro/Claro", command=modoDark, bg="#007BFF", fg="white") 
dark_mode_button.pack(side=tk.LEFT, padx=5, pady=5)  
 
 
 



 
root.mainloop()