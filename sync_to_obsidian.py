import os
import json
import re
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# Scopes required to access YouTube account
SCOPES = ['https://www.googleapis.com/auth/youtube.readonly']
OUTPUT_DIR = '/Users/chrisweinhaupl/Library/Mobile Documents/iCloud~md~obsidian/Documents/dev_youtube/youtube'

def get_authenticated_service():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"Error refreshing token: {e}")
                if os.path.exists('token.json'):
                    os.remove('token.json')
                creds = None
        
        if not creds:
            if not os.path.exists('client_secret.json'):
                print("Error: 'client_secret.json' not found.")
                return None

            flow = InstalledAppFlow.from_client_secrets_file(
                'client_secret.json', SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    return build('youtube', 'v3', credentials=creds)

def sanitize_filename(name):
    # Replace invalid filename characters with underscores
    return re.sub(r'[<>:"/\\|?*]', '_', name)

def get_playlist_videos(youtube, playlist_id):
    videos = []
    next_page_token = None
    
    while True:
        request = youtube.playlistItems().list(
            part="snippet,contentDetails",
            playlistId=playlist_id,
            maxResults=50,
            pageToken=next_page_token
        )
        try:
            response = request.execute()
            
            for item in response.get('items', []):
                snippet = item['snippet']
                video_id = item['contentDetails']['videoId']
                videos.append({
                    'title': snippet.get('title', 'Unknown Title'),
                    'id': video_id,
                    'description': snippet.get('description', ''),
                    'publishedAt': snippet.get('publishedAt', ''),
                    'channelTitle': snippet.get('videoOwnerChannelTitle', 'Unknown')
                })

            next_page_token = response.get('nextPageToken')
            if not next_page_token:
                break
        except Exception as e:
            print(f"Error fetching videos for playlist {playlist_id}: {e}")
            break
            
    return videos

def save_to_markdown(playlist, videos, output_dir):
    title = playlist['title']
    safe_title = sanitize_filename(title)
    filename = f"{safe_title}.md"
    filepath = os.path.join(output_dir, filename)
    
    content = []
    content.append("---")
    content.append(f"id: {playlist['id']}")
    content.append(f"title: \"{title}\"")
    content.append(f"privacy: {playlist['privacy']}")
    content.append(f"video_count: {len(videos)}")
    content.append(f"url: https://www.youtube.com/playlist?list={playlist['id']}")
    content.append("type: youtube-playlist")
    content.append("---")
    content.append("")
    content.append(f"# {title}")
    content.append("")
    content.append(f"**Privacy:** {playlist['privacy']}")
    content.append(f"**Total Videos:** {len(videos)}")
    content.append("")
    content.append("## Videos")
    content.append("")
    
    for video in videos:
        vid_title = video['title'].replace('[', '(').replace(']', ')')
        vid_url = f"https://www.youtube.com/watch?v={video['id']}"
        content.append(f"- [{vid_title}]({vid_url})")
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(content))

def sync_playlists_to_obsidian():
    # Ensure output directory exists
    if not os.path.exists(OUTPUT_DIR):
        print(f"Creating directory: {OUTPUT_DIR}")
        os.makedirs(OUTPUT_DIR, exist_ok=True)

    youtube = get_authenticated_service()
    if not youtube:
        return

    # Identify channel
    try:
        channel_response = youtube.channels().list(part="snippet", mine=True).execute()
        if 'items' in channel_response:
            channel = channel_response['items'][0]
            print(f"Authenticated as: {channel['snippet']['title']}")
    except Exception:
        pass

    next_page_token = None
    processed_count = 0
    
    print(f"Syncing playlists to: {OUTPUT_DIR}")
    
    while True:
        request = youtube.playlists().list(
            part="snippet,contentDetails,status",
            mine=True,
            maxResults=50,
            pageToken=next_page_token
        )
        response = request.execute()

        for item in response.get('items', []):
            playlist = {
                'title': item['snippet']['title'],
                'id': item['id'],
                'privacy': item['status']['privacyStatus'],
                'count': item['contentDetails']['itemCount']
            }
            
            print(f"Processing: {playlist['title']} ({playlist['privacy']})")
            
            # Fetch videos for this playlist
            videos = get_playlist_videos(youtube, playlist['id'])
            
            # Save to Markdown
            save_to_markdown(playlist, videos, OUTPUT_DIR)
            processed_count += 1

        next_page_token = response.get('nextPageToken')
        if not next_page_token:
            break

    print(f"\nSuccessfully synced {processed_count} playlists to Obsidian.")

if __name__ == '__main__':
    sync_playlists_to_obsidian()
