from youtube_transcript_api import YouTubeTranscriptApi
from transformers import pipeline
import re

def get_video_id(video_url):
    match = re.search(r"(?<=v=|/)([0-9A-Za-z_-]{11})", video_url)
    return match.group(0) if match else None

def get_video_transcript(video_id):
    transcript = YouTubeTranscriptApi.get_transcript(video_id)
    return ' '.join([entry['text'] for entry in transcript])

def summarize_text(text):
    summarizer = pipeline("summarization")
    summary = summarizer(text, max_length=150, min_length=30, do_sample=False)
    return summary[0]['summary_text']

def main():
    video_url = input("Digite o link do vídeo do YouTube: ")
    video_id = get_video_id(video_url)
    
    if not video_id:
        print("ID do vídeo não encontrado. Verifique o link e tente novamente.")
        return
    
    try:
        transcript = get_video_transcript(video_id)
        summary = summarize_text(transcript)
        print("Resumo do vídeo:")
        print(summary)
    except Exception as e:
        print(f"Ocorreu um erro: {e}")

if __name__ == "__main__":
    main()
