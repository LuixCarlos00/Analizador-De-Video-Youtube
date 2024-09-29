# main.py
import pytube
import openai
import ffmpeg

# Função para baixar o vídeo do YouTube
def download_video(url):
    yt = pytube.YouTube(url)
    stream = yt.streams.filter(only_audio=True).first()
    stream.download(output_path='downloads', filename='video.mp4')

# Função para extrair áudio do vídeo
def extract_audio(video_path):
    audio_path = 'downloads/audio.mp3'
    ffmpeg.input(video_path).output(audio_path).run()
    return audio_path

# Função para resumir o áudio usando OpenAI
def summarize_audio(audio_path):
    with open(audio_path, 'rb') as f:
        audio_data = f.read()

    # Substitua 'your-openai-api-key' com sua chave da API OpenAI
    openai.api_key = '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'
    
    response = openai.Audio.transcriptions.create(
        audio=audio_data,
        model='whisper-1',  # Supondo que esteja usando o modelo Whisper
        response_format='text'
    )
    
    return response['text']

# Função principal
def main():
    url = input("Insira o link do vídeo do YouTube: ")
    download_video(url)
    audio_path = extract_audio('downloads/video.mp4')
    summary = summarize_audio(audio_path)
    print("Resumo do vídeo: ")
    print(summary)

if __name__ == "__main__":
    main()