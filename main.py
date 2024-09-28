import pytube
import ffmpeg
import openai

# Função para transcrever áudio usando a API da OpenAI
def transcribe_audio(file_path):
    with open(file_path, "rb") as audio_file:
        transcript = openai.Audio.transcribe(
            model="whisper-1",
            file=audio_file
        )
    return transcript["text"]

# Função para resumir o texto usando a API da OpenAI
def summarize_text(transcript):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "Você é um assistente que resume vídeos. Responda em formato markdown."},
            {"role": "user", "content": f"Descreva o seguinte vídeo: {transcript}"},
        ]
    )
    return response.choices[0].message["content"]

# Solicita ao usuário que insira a URL do vídeo do YouTube
url = input("Por favor, insira a URL do vídeo do YouTube: ")
filename = "audio.wav"

# Baixando o vídeo do YouTube
yt = pytube.YouTube(url)
stream = yt.streams.filter(only_audio=True).first()
stream.download(filename=filename)

# Convertendo o vídeo para áudio
ffmpeg.input(filename).output("audio.wav", format="wav", loglevel="error").run()

# Transcrevendo o áudio
openai.api_key = "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"  # Coloque sua chave API aqui
transcript = transcribe_audio("audio.wav")

# Resumindo a transcrição
summary = summarize_text(transcript)

# Salvando o resumo em um arquivo Markdown
with open("output.md", "w", encoding="utf-8") as md_file:
    md_file.write(summary)

print("Resumo salvo em output.md")


O código feito em python consegue por meio de um link de videdo do youtube descrever e resumir o vídeo em poucos segundos