from pytubefix import YouTube
import re

def download_video(video_url, output_path="C:/Users/Videos_Downloads/video.mp4"):
    try:
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