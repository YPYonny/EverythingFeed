#!/usr/bin/env python3
import os
import json
import base64
import requests
from pathlib import Path
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials

# --- CONFIG ---
CACHE_FILE = "posted_cache.json"
FACEBOOK_PAGE_ID = os.getenv("FACEBOOK_PAGE_ID")
FACEBOOK_PAGE_ACCESS_TOKEN = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")
DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
B64_SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")

CAPTION = (
    "Don't forget to subscribe for more!\n\n"
    "#EverythingFeed #clips #fyp #fypシ゚viralシ #viral #facebookvideo"
)

if not all([FACEBOOK_PAGE_ID, FACEBOOK_PAGE_ACCESS_TOKEN, DRIVE_FOLDER_ID, B64_SERVICE_ACCOUNT_JSON]):
    raise RuntimeError("Missing one of the required environment variables.")

# --- DECODE GOOGLE SERVICE ACCOUNT ---
service_account_json = base64.b64decode(B64_SERVICE_ACCOUNT_JSON).decode("utf-8")
creds = Credentials.from_service_account_info(
    json.loads(service_account_json),
    scopes=["https://www.googleapis.com/auth/drive.readonly"]
)

# --- CACHE UTILITIES ---
def load_cache():
    if Path(CACHE_FILE).exists():
        try:
            with open(CACHE_FILE, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            pass
    return {"posted_ids": []}

def save_cache(cache):
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)

# --- FETCH VIDEOS FROM DRIVE ---
def fetch_videos_from_drive():
    service = build("drive", "v3", credentials=creds)
    query = f"'{DRIVE_FOLDER_ID}' in parents and mimeType contains 'video/' and trashed=false"
    results = (
        service.files()
        .list(q=query, orderBy="createdTime asc", fields="files(id, name)")
        .execute()
    )
    return results.get("files", [])

# --- GET NEXT VIDEO ---
def get_next_video():
    cache = load_cache()
    posted_ids = cache.get("posted_ids", [])
    
    videos = fetch_videos_from_drive()
    if not videos:
        raise RuntimeError("⚠️ No videos found in Drive folder!")

    # Filter out already posted
    unposted_videos = [v for v in videos if v["id"] not in posted_ids]

    if not unposted_videos:
        # All videos posted → start over
        next_video = videos[0]
        posted_ids = []  # reset cache
    else:
        next_video = unposted_videos[0]

    # Update cache
    posted_ids.append(next_video["id"])
    cache["posted_ids"] = posted_ids
    save_cache(cache)

    return next_video

# --- POST VIDEO TO FACEBOOK ---
def post_video_to_facebook(video_id, video_name):
    video_url = f"https://drive.google.com/uc?id={video_id}&export=download"
    url = f"https://graph.facebook.com/v18.0/{FACEBOOK_PAGE_ID}/videos"

    data = {
        "access_token": FACEBOOK_PAGE_ACCESS_TOKEN,
        "file_url": video_url,
        "description": CAPTION,
        "published": "true"
    }

    response = requests.post(url, data=data)
    if not response.ok:
        raise RuntimeError(f"Facebook API error: {response.text}")
    print(f"[SUCCESS] Posted Video: {video_name}")

# --- MAIN ---
def main():
    video = get_next_video()
    print(f"[DEBUG] Selected video: {video['name']} ({video['id']})")
    post_video_to_facebook(video["id"], video["name"])

if __name__ == "__main__":
    main()
