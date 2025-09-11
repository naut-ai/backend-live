from flask import Flask, request, jsonify
import requests
import base64
from flask_cors import CORS
import json
import cloudinary
import cloudinary.uploader
import time
from dotenv import load_dotenv
import os
from config import system_prompt, title_prompt, did_url, ayesha_img_url, make_speech_friendly, openrouter_url, generate_audio_sync, generate_subtitles
from vosk import Model
import assemblyai as aai

app = Flask(__name__)
CORS(app)

load_dotenv()

#configure environment variables
cloud_name = os.getenv("CLOUD_NAME")
cloudinary_api_key = os.getenv("CLOUDINARY_API_KEY")
cloudinary_api_secret = os.getenv("CLOUDINARY_API_SECRET")
openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
aai.settings.api_key = os.getenv("ASSEMBLY_API_KEY")
# gemini_api_key = os.getenv("GEMINI_API_KEY")

cloudinary.config(
  cloud_name = cloud_name,
  api_key = cloudinary_api_key,
  api_secret = cloudinary_api_secret,
  secure = True
)

vosk_model = Model("vosk-model-small-en-us-0.15")

video_obj = {}

@app.before_request
def debug_origin():
    print("🚀 NautAI Server v2 Running...")
    print("Request Origin:", request.headers.get("Origin"))

@app.route('/ask_video', methods=['POST'])
def ask_avatar():
    print("user hit the url")
    user_input = request.json['question']
    api_credentials = request.json['apiKeys']
    print(api_credentials)
    print("Got prompt from user...")

    #Step 1: Get response from LLM
    try:
        headers = {
            "Authorization": f"Bearer {openrouter_api_key}",
            "Content-Type": "application/json"
        }
        body = {
            "model": "mistralai/mistral-small-3.2-24b-instruct:free",
            "messages": [{"role": "user", "content": system_prompt + f" Topic: {user_input}"}]
        }
        response = requests.post(openrouter_url, headers=headers, json=body)
        print(response.json())
        message = response.json()['choices'][0]['message']['content']

        print("✅ Script generated from LLM!")

        title_body = {
            "model": "mistralai/mistral-small-3.2-24b-instruct:free",
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
        subtitle_name = generate_subtitles("output.wav")
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
    
    did_headers = {
        "Authorization": f"Basic {api_credentials["didApiKey"]}",
        "Content-Type": "application/json"
    }
   
    did_data =  {
  "script": {
    "type": "audio",
    "audio_url": audio_upload_result["secure_url"]
  },
  "source_url": ayesha_img_url,
  "config": {
     "driver_expressions": {
        "expressions": [
            {
                "start_frame": 0,
                "expression": "surprise",
                "intensity": 0.2
            },
            {
                "start_frame": 100,
                "expression": "neutral",
                "intensity": 1.0
            },
            {
                "start_frame": 200,
                "expression": "happy",
                "intensity": 0.3
            }
        ],
        "transition_frames": 20
    }
  },
}
    try:
        did_response = requests.post(did_url, headers=did_headers, json=did_data)
        print("Status Code:", did_response.status_code)
        print("Response Text:", did_response.text)
        print(did_response)
        video = did_response.json()
        
        video_obj["metadata"] = video
        video_obj["video_id"] = video["id"]

        print("✅ Final Video generated from D-ID!")
    except Exception as e:
        print(e)
        return jsonify({"message":"DID API Crendentials expired!"})

    #Step 6: Return the Video ID to Frontend
    return jsonify({"video_id":video_obj["video_id"]})

@app.route('/get_video', methods=['POST'])
def fetch_video():
    api_credentials = request.json['apiKeys']
    talk_id = request.json['talk_id']
    print(api_credentials)
    fetch_url = f"https://api.d-id.com/talks/{talk_id}"

    headers = {
        "Authorization": f"Basic {api_credentials["didApiKey"]}",
        "Content-Type": "application/json",
        "accept": "application/json"
    }
    
    try:
        while True:
            response = requests.get(fetch_url, headers=headers)
            resdict = json.loads(response.text)
            print("Fetching video from D-ID...")
            state = resdict.get("status")
            print("Status:", state)
            video_url = resdict.get("result_url")
            if video_url:
                print("✅ Fetched video from D-ID!")
                upload_result = cloudinary.uploader.upload(
                                video_url,
                                resource_type="video",
                                folder="naut-videos"
                )
                print("✅ Video saved to Cloudinary!")
                print("Video link: ", upload_result["secure_url"])
                video_obj["video_url"] = upload_result["secure_url"]
                video_obj["metadata"] = resdict
                break
            time.sleep(5)
        
        print("✅ Final Video Object:")
        print(video_obj)

        return jsonify(video_obj)
    except Exception as e:
        print(e)
        return jsonify({"message":"Video not found!"})

if __name__ == '__main__':
    app.run(debug=True, port=8000)
