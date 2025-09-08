import asyncio
import edge_tts

def generate_audio():
    tts = edge_tts.Communicate(
        text="Hello, this is a test using Edge TTS!",
        voice="en-US-AvaNeural"
    )
    tts.save("test.mp3")
    print("✅ Audio saved as test.mp3")

asyncio.run(generate_audio())