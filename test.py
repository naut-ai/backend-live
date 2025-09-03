import requests
import json
import time

def fetchVideo(talk_id:str, api_key):
    fetch_url = f"https://api.d-id.com/talks/{talk_id}"

    headers = {
        "Authorization": f"Basic {api_key}",
        "Content-Type": "application/json",
        "accept": "application/json"
    }

    # response = requests.get(fetch_url, headers=headers)

    # resdict = json.loads(response.text)
    # print(resdict)
    # return resdict["result_url"]

    while True:
        response = requests.get(fetch_url, headers=headers)
        resdict = json.loads(response.text)
        print(resdict)
        if resdict.get("status") is not None:
            state = resdict.get("status")
            print("Status:", state)
            if state == "done":
                video_url = resdict.get("result_url")
                return {"video_link":video_url}
        time.sleep(5)

print(fetchVideo("tlk_6ourxLeauPKFO0B1ou1Ms", 'YnJlbmRlbjQ0QHR1cmtleXRoLmNvbQ:x5bAr84Q_09EEFMxZV6V8'))