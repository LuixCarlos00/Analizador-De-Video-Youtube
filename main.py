from pytubefix import YouTube
import re
import os

def download_video(video_url, output_path=None):
    try:
        if output_path is None:
            NomeUser = os.path.expanduser("~")
            output_path = os.path.join(NomeUser, "Videos_Downloads")

        output_dir = os.path.dirname(output_path)

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            print(f"output_path criada: {output_dir}")

        yt = YouTube(video_url)
        stream = yt.streams.get_highest_resolution()
        stream.download(output_path=output_path)
        print(f"Vídeo baixado com sucesso e salvo em: {output_path}/{yt.title}")
    except Exception as e:
        print(f"Ocorreu um erro ao baixar o vídeo: {e}")

def download_audio(video_url, output_path=None):
    try:
        if output_path is None:
            user_home = os.path.expanduser("~")
            output_path = os.path.join(user_home, "Audios_Downloads")

        if not os.path.exists(output_path):
            os.makedirs(output_path)
            print(f"output_path criada: {output_path}")

        yt = YouTube(video_url)
        stream = yt.streams.get_audio_only()
        
        stream.download(output_path=output_path)
        print(f"Áudio baixado com sucesso e salvo em: {output_path}/{yt.title}.mp3")
    except Exception as e:
        print(f"Ocorreu um erro ao baixar o áudio: {e}")

def is_valid_url(url):
    regex = r'^(https?://)?(www\.)?(youtube\.com|youtu\.?be)/.+$'
    return re.match(regex, url) is not None

def download_multiple_videos(urls, download_function):
    for url in urls:
        url = url.strip()  # Remove espaços em branco
        if is_valid_url(url):
            download_function(url)
        else:
            print(f"URL inválido: {url}")

def main():
    while True:
        print("Selecione uma opção:")
        print("1 - Baixar vídeo")
        print("2 - Baixar áudio")
        print("3 - Baixar lista de vídeos")
        print("4 - Baixar lista de áudios a partir de vídeos")
        print("5 - Encerrar")
        choice = input("Opção: ")

        if choice == "1":
            video_url = input("Digite o link do vídeo do YouTube que você deseja baixar: ")
            if is_valid_url(video_url):
                download_video(video_url)
            else:
                print("URL inválido. Por favor, insira um link válido do YouTube.")

        elif choice == "2":
            video_url = input("Digite o link do áudio do YouTube que você deseja baixar: ")
            if is_valid_url(video_url):
                download_audio(video_url)
            else:
                print("URL inválido. Por favor, insira um link válido do YouTube.")

        elif choice == "3":
            video_urls = input("Digite os links dos vídeos do YouTube que você deseja baixar (separados por vírgula): ")
            urls_list = video_urls.split(',')
            download_multiple_videos(urls_list, download_video)

        elif choice == "4":
            video_urls = input("Digite os links dos vídeos do YouTube que você deseja baixar como áudios (separados por vírgula): ")
            urls_list = video_urls.split(',')
            download_multiple_videos(urls_list, download_audio)

        elif choice == "5":
            print("Saindo...")
            break 

        else:
            print("Opção inválida. Por favor, escolha uma opção disponível.")

if __name__ == "__main__":
    main()
