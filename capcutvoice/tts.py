import requests
import base64
import os
import time
import re

BASE_URL = 'https://api16-normal-v6.tiktokv.com/media/api/text/speech/invoke'
DEFAULT_VOICE = 'vi_female_huong'
tiktok_session_id = "621bd837f095bc63f0473a36fdac4290"

def set_tiktok_session_id(session_id):
    global tiktok_session_id
    tiktok_session_id = session_id

def prepare_text(text):
    # Replace special characters that the API interprets differently
    # Order must match the C# implementation in CapCutTtsService.cs
    # 1) + → " cộng "
    text = text.replace('+', ' cộng ')
    # 2) space → "+" (API expects application/x-www-form-urlencoded style, NOT %20)
    text = text.replace(' ', '+')
    # 3) & → " và "
    text = text.replace('&', ' và ')
    return text

def handle_status_error(status_code):
    if status_code == 1:
        raise ValueError(f'Invalid or expired session ID. status_code: {status_code}')
    elif status_code == 2:
        raise ValueError(f'Text too long. status_code: {status_code}')
    elif status_code == 4:
        raise ValueError(f'Invalid speaker. status_code: {status_code}')
    elif status_code == 5:
        raise ValueError(f'No session ID found. status_code: {status_code}')

def create_tts(text, voice_id=DEFAULT_VOICE, index=1, temp_folder='temp', retries=3, delay=1):
    if not tiktok_session_id:
        raise ValueError("TikTok session ID is not set. Use set_tiktok_session_id() to set it.")

    stripped_text = text.strip()
    if not stripped_text or not re.search(r'[a-zA-Z0-9À-ỹ]', stripped_text) or stripped_text in ['"', ' ', '" ', ' "']:
        print(f"Skipping Segment_{index}: Empty or meaningless content")
        return (False, {"segment_id": index, "text": text, "error": "Empty or meaningless content"})

    req_text = prepare_text(text)
    url = f'{BASE_URL}/?text_speaker={voice_id}&req_text={req_text}&speaker_map_type=0&aid=1233'
    headers = {
        'User-Agent': 'com.zhiliaoapp.musically/2022600030 (Linux; U; Android 7.1.2; es_ES; SM-G988N; Build/NRD90M;tt-ok/3.12.13.1)',
        'Cookie': f'sessionid={tiktok_session_id}',
        'Accept-Encoding': 'gzip,deflate,compress'
    }

    start_time = time.time()
    for attempt in range(retries):
        try:
            print(f"Attempt {attempt + 1} for Segment_{index} at {time.time() - start_time:.2f}s")
            response = requests.post(url, headers=headers, timeout=5)
            os.makedirs(temp_folder, exist_ok=True)

            if response.status_code == 200:
                data = response.json()
                status_code = data.get('status_code')
                if status_code != 0:
                    handle_status_error(status_code)
                
                encoded_voice = data.get('data', {}).get('v_str')
                if encoded_voice:
                    file_name = os.path.join(temp_folder, f"{index}.mp3")
                    with open(file_name, 'wb') as f:
                        f.write(base64.b64decode(encoded_voice))
                    duration = time.time() - start_time
                    print(f"Segment_{index} completed in {duration:.2f}s")
                    return (True, None)
                else:
                    raise ValueError(f"No audio data returned")
            else:
                raise ValueError(f"Request failed with status code {response.status_code}")
        except (requests.Timeout, ValueError, Exception) as e:
            print(f"Error in Segment_{index}, attempt {attempt + 1}: {str(e)}")
            if attempt < retries - 1:
                print(f"Retrying ({attempt + 1}/{retries}) after {delay} seconds...")
                time.sleep(delay)
                continue
            duration = time.time() - start_time
            print(f"Failed Segment_{index} after {retries} attempts in {duration:.2f}s")
            return (False, {"segment_id": index, "text": text, "error": str(e)})