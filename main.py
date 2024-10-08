from youtube_transcript_api import YouTubeTranscriptApi
from transformers import pipeline

def get_video_transcript(video_id):
    transcript = YouTubeTranscriptApi.get_transcript(video_id)
    return ' '.join([entry['text'] for entry in transcript])

def summarize_text(text):
    summarizer = pipeline("summarization")
    summary = summarizer(text, max_length=150, min_length=30, do_sample=False)
    return summary[0]['summary_text']

def main(video_id):
    try:
        transcript = get_video_transcript(video_id)
        summary = summarize_text(transcript)
        print("Resumo do vídeo:")
        print(summary)
    except Exception as e:
        print(f"Ocorreu um erro: {e}")

if __name__ == "__main__":
    video_id = "SEU_VIDEO_ID_AQUI"  # Substitua pelo ID do vídeo do YouTube
    main(video_id)
