import re
import edge_tts
import asyncio

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
"You are Ayesha, a friendly assistant to explain give about the given topic in ONLY 50 words. 
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

elevenlabs_voice_id = "NaKPQmdr7mMxXuXrNeFC"
elevenlabs_url = f"https://api.elevenlabs.io/v1/text-to-speech/{elevenlabs_voice_id}"

did_url = "https://api.d-id.com/talks"

ayesha_img_url = "https://res.cloudinary.com/dvxt3ykbf/image/upload/v1753942461/g6tl0cqqlbbz8pg26vsk.png"

def generate_audio_sync(speech, voice="en-US-AriaNeural", filename="output.mp3"):
    """
    Generate speech audio synchronously using Edge TTS.
    """
    async def _generate():
        tts = edge_tts.Communicate(text=speech, voice=voice)
        await tts.save(filename)

    # Run the async function synchronously
    asyncio.run(_generate())
    return filename
