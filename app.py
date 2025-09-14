from flask import Flask, request, jsonify
import requests
from flask_cors import CORS, cross_origin
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv
import os
from config import system_prompt, title_prompt, make_speech_friendly, openrouter_url, generate_audio_sync, generate_subtitles, create_heygen_video, fetch_created_video
import assemblyai as aai

app = Flask(__name__)

CORS(app, supports_credentials=True, origins=["https://naut-demo.web.app"])

load_dotenv()

#configure environment variables
cloud_name = os.getenv("CLOUD_NAME")
cloudinary_api_key = os.getenv("CLOUDINARY_API_KEY")
cloudinary_api_secret = os.getenv("CLOUDINARY_API_SECRET")
openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
aai.settings.api_key = os.getenv("ASSEMBLYAI_API_KEY")
# gemini_api_key = os.getenv("GEMINI_API_KEY")

cloudinary.config(
  cloud_name = cloud_name,
  api_key = cloudinary_api_key,
  api_secret = cloudinary_api_secret,
  secure = True
)

video_obj = {}

@app.before_request
def debug_origin():
    print("🚀 NautAI Server v3 Running...")
    print("Request Origin:", request.headers.get("Origin"))

@app.route('/ask_video', methods=['POST'])
def ask_avatar():
    print("user hit the url")
    user_input = request.json['question']
    api_credentials = request.json['apiKeys']

    #Step 1: Get response from LLM
    try:
        headers = {
            "Authorization": f"Bearer {openrouter_api_key}",
            "Content-Type": "application/json"
        }
        body = {
            "model": "mistralai/mistral-small-24b-instruct-2501:free",
            "messages": [{"role": "user", "content": system_prompt + f" Topic: {user_input}"}]
        }
        response = requests.post(openrouter_url, headers=headers, json=body)
        print(response.json())
        message = response.json()['choices'][0]['message']['content']

        print("✅ Script generated from LLM!")

        title_body = {
            "model": "mistralai/mistral-small-24b-instruct-2501:free",
            "messages": [{"role": "user", "content": title_prompt + f" Content: {message}"}]
        }
        title_response = requests.post(openrouter_url, headers=headers, json=title_body)
        print(title_response.json())
        title_message = title_response.json()['choices'][0]['message']['content']

        print("✅ Title generated from LLM!")

    except Exception as e:
        print(e)
        return jsonify({"message":"Error from OpenRouter!"})

    video_obj["video_title"] = title_message.replace('"', "")
    video_obj["video_content"] = message

    speech = make_speech_friendly(message)

    print("✅ Speech generated from script!")

    #Step 2: Convert Script to Voiceover using EdgeTTS

    try:
        audio_name = generate_audio_sync(speech=speech)
        print("✅ Voiceover generated from EdgeTTS!")
    except Exception as e:
        print(e)
        return jsonify({"message":"Error from EdgeTTS!"})

    #Step 3: Create subtitles for voiceover

    try:
        subtitle_name = generate_subtitles("output.mp3")
        print("✅ Subtitles generated from Assembly AI!")
    except Exception as e:
        print(e)
        return jsonify({"message":"Error from Vrok!"})
    
    # Step 4: Save audio and subtitles to Cloudinary

    try:
        audio_upload_result = cloudinary.uploader.upload(
        audio_name,
        resource_type="video",  # audio is treated as video resource
        folder="naut-audios"
        )
    except Exception as e:
        print(e)
        return jsonify({"message":"Error from Cloudinary Audio!"})

    print("✅ Voiceover saved to Cloudinary!")
    print("Audio URL:", audio_upload_result["secure_url"])

    try:
        subtitles_upload_result = cloudinary.uploader.upload(
        subtitle_name,
        resource_type="raw",
        folder="naut-subtitles"
        )
    except Exception as e:
        print(e)
        return jsonify({"message":"Error from Cloudinary Subtitles!"})

    print("✅ Subtitles saved to Cloudinary!")
    print("Subtitles URL:", subtitles_upload_result["secure_url"])

    video_obj["subtitle_url"] = subtitles_upload_result["secure_url"]

    # Step 5: Generate talking avatar video with D-ID
    
    try:
        heygen_response = create_heygen_video(api_key=api_credentials["heygenApiKey"], voiceover=audio_upload_result["secure_url"])
        print("✅ Final Video generated from HeyGen!")
    except Exception as e:
        print(e)
        return jsonify({"message":"HeyGen API Crendentials expired!"})

    video_obj["video_id"] = heygen_response["video_id"]

    #Step 6: Return the Video ID to Frontend
    print(video_obj)
    return jsonify({"video_id":video_obj["video_id"]})

@app.route('/get_video', methods=['POST'])
def fetch_video():
    api_credentials = request.json['apiKeys']
    talk_id = request.json['talk_id']
    
    try:
        response = fetch_created_video(api_key=api_credentials["heygenApiKey"], video_id=talk_id)
        if response["status"] == "pending":
            return jsonify({"message":"Video is still processing..."})
        if response["status"] == "expired":
            return jsonify({"message":"API Credentials Expired!"})
        if response["status"] == "error":
            return jsonify({"message":"Error from HeyGen!"})    
        print("✅ Fetched video from HeyGen!")
        upload_result = cloudinary.uploader.upload(
                                    response["video_url"],
                                    resource_type="video",
                                    folder="naut-videos"
                    )
        print("✅ Video saved to Cloudinary!")
        print("Video link: ", upload_result["secure_url"])

    except Exception as e:
        print(e)
        return jsonify({"message":"Video not found!"})
    
    video_obj["metadata"] = response["video_data"]
    video_obj["video_url"] = upload_result["secure_url"]
    print("✅ Final Video Object:")
    print(video_obj)
    return jsonify(video_obj)

if __name__ == '__main__':
    app.run(debug=True, port=8000)
