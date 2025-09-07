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
from config import system_prompt, title_prompt, did_url, ayesha_img_url, make_speech_friendly, openrouter_url, generate_audio_sync

app = Flask(__name__)
CORS(app)

load_dotenv()

#configure environment variables
cloud_name = os.getenv("CLOUD_NAME")
cloudinary_api_key = os.getenv("CLOUDINARY_API_KEY")
cloudinary_api_secret = os.getenv("CLOUDINARY_API_SECRET")
openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
# did_api_key = os.getenv("DID_API_KEY")
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
    print("🚀 NautAI Server v2 Running...")
    print("Request Origin:", request.headers.get("Origin"))

@app.route('/ask_video', methods=['POST'])
def ask_avatar():
    print("user hit the url")
    user_input = request.json['question']
    api_credentials = request.json['apiKeys']
    print(api_credentials)
    print("Got prompt from user...")

    # # Step 1: Get response from LLM
    # headers = {
    #     "Authorization": f"Bearer {openrouter_api_key}",
    #     "Content-Type": "application/json"
    # }
    # body = {
    #     "model": model_name,
    #     "messages": [{"role": "user", "content": system_prompt + f" Topic: {user_input}"}]
    # }
    # response = requests.post(openrouter_url, headers=headers, json=body)
    # print(response.json())
    # message = response.json()['choices'][0]['message']['content']

    # title_body = {
    #     "model": model_name,
    #     "messages": [{"role": "user", "content": title_prompt + f" Content: {message}"}]
    # }
    # title_response = requests.post(openrouter_url, headers=headers, json=title_body)
    # print(title_response.json())
    # title_message = title_response.json()['choices'][0]['message']['content']

    try:

        #Using openrouter Mistral instead of Gemini
      
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

        title_body = {
            "model": "mistralai/mistral-small-3.2-24b-instruct:free",
            "messages": [{"role": "user", "content": title_prompt + f" Content: {message}"}]
        }
        title_response = requests.post(openrouter_url, headers=headers, json=title_body)
        print(title_response.json())
        title_message = title_response.json()['choices'][0]['message']['content']

    #     response = completion(
    #     model="gemini/gemini-2.5-flash-preview-04-17",  
    #     messages=[
    #         {"role": "system", "content": system_prompt},
    #         {"role": "user", "content": f"Topic: {user_input}"}
    #     ],
    #     api_key=api_credentials["geminiApiKey"]
    # )
    #     message = response['choices'][0]['message']['content']

    #     title_response = completion(
    #     model="gemini/gemini-2.5-flash-preview-04-17",  
    #     messages=[
    #         {"role": "system", "content": title_prompt},
    #         {"role": "user", "content": f"Content: {message}"}
    #     ],
    #     api_key=api_credentials["geminiApiKey"]
    # )
    #     title_message = title_response['choices'][0]['message']['content']

    except Exception as e:
        print(e)
        return jsonify({"message":"Error from OpenRouter!"})

    video_obj["video_title"] = title_message.replace('"', "")
    video_obj["video_prompt"] = message

    print("Got script from LLM...")
    print(video_obj["video_title"])
    print(video_obj["video_prompt"])

    speech = make_speech_friendly(message)

    # # Step 2: Convert response to voice using ElevenLabs
    # try:
    #     tts_headers = {
    #         "xi-api-key": elevenlabs_api_key,
    #         "Content-Type": "application/json",
    #         "Accept": "audio/mpeg"
    #     }
    #     tts_data = {
    #         "text": speech,
    #         "voice_settings": {"stability": 0.5, "similarity_boost": 0.5}
    #     }

    #     print("🔹 ELEVENLABS URL:", elevenlabs_url)
    #     print("🔹 API KEY:", api_credentials.get("elevenlabsApiKey"))
    #     print("🔹 HEADERS:", tts_headers)
    #     print("🔹 BODY:", tts_data)

    #     tts_response = requests.post(elevenlabs_url, headers=tts_headers, json=tts_data)

    #     # Log full response for debugging
    #     print("🔹 STATUS:", tts_response.status_code)
    #     print("🔹 RESPONSE:", tts_response.text)

    #     if tts_response.status_code == 401:
    #         return jsonify({"message": "Unauthorized - Invalid API Key"}), 401

    # except Exception as e:
    #     print("🔹 Exception:", e)
    #     return jsonify({"message": "Error from ElevenLabs!"}), 500
    
    # audio_content = tts_response.content
    # audio_base64 = base64.b64encode(audio_content).decode()

    # with open("output.mp3", "wb") as f:
    #     f.write(base64.b64decode(audio_base64))

    try:
        audio_name = generate_audio_sync(speech=speech)
        print("Audio generated from EdgeTTS!")
    except Exception as e:
        print(e)
        return jsonify({"message":"Error from EdgeTTS!"})

    #TODO Transribe the audio from edgeTTS

    # model = whisper.load_model("small")
    # result = model.transcribe(audio_name)

    # with open("subtitles.vtt", "w") as f:
    #     print(result["text"])
    #     f.write(result["text"])


    # Step 3: Save audio to Cloudinary

    try:
        upload_result = cloudinary.uploader.upload(
        audio_name,
        resource_type="video",  # audio is treated as video resource
        folder="naut-audios"
        )
    except Exception as e:
        print(e)
        return jsonify({"message":"Error from Cloudinary!"})

    print("Audio saved to cloudinary!")
    print("Audio URL:", upload_result["secure_url"])

    # Step 3: Generate talking avatar video with D-ID
    did_headers = {
        "Authorization": f"Basic {api_credentials["didApiKey"]}",
        "Content-Type": "application/json"
    }
   
    did_data =  {
  "script": {
    "type": "audio",
    "audio_url": upload_result["secure_url"]
  },
  "source_url": ayesha_img_url,
      "streaming": False
}
    try:
        did_response = requests.post(did_url, headers=did_headers, json=did_data)
        print("Status Code:", did_response.status_code)
        print("Response Text:", did_response.text)
        video = did_response.json()

        print("Got video from D-ID...")
        
        video_obj["metadata"] = video

        print(video_obj["metadata"])

        video_obj["video_id"] = video["id"]
        print(video_obj["video_id"])
    except Exception as e:
        print(e)
        return jsonify({"message":"DID API Crendentials expired!"})

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
    
    while True:
        response = requests.get(fetch_url, headers=headers)
        resdict = json.loads(response.text)
        print(resdict)
        state = resdict.get("status")
        print("Status:", state)
        video_url = resdict.get("result_url")
        if video_url:
            print("Video link: ", video_url)
            upload_result = cloudinary.uploader.upload(
                            video_url,
                            resource_type="video",  # audio is treated as video resource
                            folder="naut-videos"
            )
            video_obj["video_url"] = video_url
            video_obj["metadata"] = resdict
            break
        time.sleep(5)
    
    print("Fetched video successfully!")
    print(video_obj)

    return jsonify(video_obj)

if __name__ == '__main__':
    app.run(debug=True, port=8000)
