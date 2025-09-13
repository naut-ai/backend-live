import re
import edge_tts
import asyncio
import assemblyai as aai
import time
import requests

def make_speech_friendly(text: str) -> str:
    # Remove Markdown formatting
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)   # bold
    text = re.sub(r"\*(.*?)\*", r"\1", text)       # italic
    text = re.sub(r"`([^`]*)`", r"\1", text)       # inline code
    text = re.sub(r"#+\s*", "", text)              # headings
    text = re.sub(r"-\s*", "", text)               # bullet points
    
    # Replace links with just the text
    text = re.sub(r"\[(.*?)\]\(.*?\)", r"\1", text)

    # Replace multiple newlines with a single space
    text = re.sub(r"\n+", " ", text)

    # Normalize spaces
    text = re.sub(r"\s+", " ", text).strip()

    # Optional: Adjust style for speech
    text = text.replace("e.g.", "for example")
    text = text.replace("i.e.", "that is")

    return text

system_prompt = '''
"You are Ayesha, a friendly assistant to explain give about the given topic in ONLY 100 words. 
Do not include emojis in your response. 
Do not include the title and end of transcript and your reasoning steps.
'''

title_prompt = '''
You are a friendly assistant to give the best suitable title for the given content. 
Do not include your reasoning steps or explanations. 
You should return only title without "" and any other extra things.
'''

model_name = "mistralai/mistral-small-3.2-24b-instruct:free"

openrouter_url = "https://openrouter.ai/api/v1/chat/completions"

def generate_audio_sync(speech, voice="en-US-AriaNeural", filename="output.mp3"):
    async def _generate():
        tts = edge_tts.Communicate(text=speech, voice=voice)
        await tts.save(filename)

    asyncio.run(_generate())
    return filename

def generate_subtitles(audio_path):
    transcriber = aai.Transcriber()
    transcript = transcriber.transcribe(audio_path)

    if transcript.status == aai.TranscriptStatus.error:
        print("❌ Error:", transcript.error)

    with open("subtitles.vtt", "w", encoding="utf-8") as f:
        f.write(transcript.export_subtitles_vtt())

    return "subtitles.vtt"

def fetch_created_video(api_key, video_id):
    status_url = f"https://api.heygen.com/v1/video_status.get?video_id={video_id}"
    headers = {
    "X-Api-Key": f"{api_key}",
    "Accept": "application/json"
    }
    while True:
        status_res = requests.get(status_url, headers=headers)
        print(status_res)
        if status_res.status_code == 200:
            data = status_res.json()["data"]
            print("video-status:", data["status"])
            if data["status"] == "completed":
                print("video-url", data["video_url"])
                print("✅ Video fetched successfully!")
                return {"video_url":data["video_url"], "video_data":data}
        time.sleep(5)

def create_heygen_video(api_key, voiceover):
    url = "https://api.heygen.com/v2/video/generate"

    headers = {
    "X-Api-Key": f"{api_key}",
    "Accept": "application/json"
    }

    data = {
    "video_inputs": [
        {
        "character": {
            "type": "avatar",
            "avatar_id": "94e6212fc6bb4ea19cf785939f0d3af6",
            "avatar_style": "normal"
        },
        "voice": {
            "type": "audio",
            "audio_url":voiceover
        },
        }
    ],
    "dimension": {
        "width": 1280,
        "height": 720
    }
    }

    response = requests.post(url, headers=headers, json=data)
    print(response)

    if response.status_code == 200:
        video_info = response.json()
        print("✅ Video request accepted:", video_info)
        
        video_id = video_info["data"]["video_id"]
        print("✅ Video ID:", video_id)

        return {"video_id":video_id, "video_data":video_info["data"]}
    
    else:
        print("❌ Error from HeyGen:", response.text)
