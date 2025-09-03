gemini_api_key="AIzaSyDLZR-W2hAvpJL_GDGzqkwuUcmOzIYob98"

import time
from google import genai
from google.genai import types

client = genai.Client(api_key=gemini_api_key)

operation = client.models.generate_videos(
    model="veo-3.0-fast-generate-preview",
    prompt="a close-up shot of a golden retriever playing in a field of sunflowers",
    config=types.GenerateVideosConfig(
        negative_prompt="barking, woofing",
    ),
)

# Waiting for the video(s) to be generated
while not operation.done:
    time.sleep(20)
    operation = client.operations.get(operation)

generated_video = operation.result.generated_videos[0]
client.files.download(file=generated_video.video)
generated_video.video.save("veo3_video.mp4")