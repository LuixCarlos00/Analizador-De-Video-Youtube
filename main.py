from pytubefix import YouTube
import re
import os

def download_video(video_url, output_path=None):
    try:
         
        if output_path is None:
              
            user_home = os.path.expanduser("~")
            output_path = os.path.join(user_home, "Videos_Downloads", "video.mp4")

         
        output_dir = os.path.dirname(output_path)

         
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            print(f"Pasta criada: {output_dir}")

        yt = YouTube(video_url)
        stream = yt.streams.get_highest_resolution()
        stream.download(output_path=output_path)
        print(f"Vídeo baixado com sucesso e salvo em: {output_path}")
    except Exception as e:
        print(f"Ocorreu um erro ao baixar o vídeo: {e}")

def is_valid_url(url):
    regex = r'^(https?://)?(www\.)?(youtube\.com|youtu\.?be)/.+$'
    return re.match(regex, url) is not None

def main():
    video_url = input("Digite o link do vídeo do YouTube: ")
    if is_valid_url(video_url):
        download_video(video_url)
    else:
        print("URL inválido. Por favor, insira um link válido do YouTube.")

if __name__ == "__main__":
    main()
