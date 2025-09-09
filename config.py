import re
import edge_tts
import asyncio
import json
import wave
from vosk import Model, KaldiRecognizer
import soundfile as sf

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

ayesha_img_url = "https://res.cloudinary.com/dvxt3ykbf/image/upload/v1757295754/ayesha_vb2w5f.png"

def convert_mp3_to_wav(mp3_file, wav_file):
    data, samplerate = sf.read(mp3_file)
    sf.write(wav_file, data, samplerate)
    return wav_file

def generate_audio_sync(speech, voice="en-US-AriaNeural", filename="output.mp3"):
    """
    Generate speech audio synchronously using Edge TTS.
    """
    async def _generate():
        tts = edge_tts.Communicate(text=speech, voice=voice)
        await tts.save(filename)

    # Run the async function synchronously
    asyncio.run(_generate())
    final = convert_mp3_to_wav(filename, "output.wav")
    return final

def generate_subtitles(audio_path, vtt_output_path):
    # Load Vosk Model
    model = Model("models/vosk-model-small-en-us-0.15")
    wf = wave.open(audio_path, "rb")

    # Validate audio format
    if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getframerate() > 48000:
        raise ValueError("Audio must be WAV mono PCM <= 48kHz")

    rec = KaldiRecognizer(model, wf.getframerate())
    rec.SetWords(True)

    def format_time(seconds):
        """Format seconds into hh:mm:ss.mmm for WebVTT"""
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds % 1) * 1000)
        return f"{h:02}:{m:02}:{s:02}.{ms:03}"

    # Prepare VTT file
    with open(vtt_output_path, "w", encoding="utf-8") as vtt:
        vtt.write("WEBVTT\n\n")
        index = 1

        # Process audio chunks
        while True:
            data = wf.readframes(4000)
            if len(data) == 0:
                break

            if rec.AcceptWaveform(data):
                result = json.loads(rec.Result())
                if "result" in result:
                    for word in result["result"]:
                        start = word["start"]
                        end = word["end"]
                        text = word["word"]
                        vtt.write(f"{format_time(start)} --> {format_time(end)}\n{text}\n\n")
                        index += 1

        # ✅ PROCESS FINAL BUFFER TO AVOID MISSING ENDING
        final_result = json.loads(rec.FinalResult())
        if "result" in final_result:
            for word in final_result["result"]:
                start = word["start"]
                end = word["end"]
                text = word["word"]
                vtt.write(f"{format_time(start)} --> {format_time(end)}\n{text}\n\n")
                index += 1

    wf.close()
    print(f"✅ Subtitles saved as {vtt_output_path}")
    return vtt_output_path
