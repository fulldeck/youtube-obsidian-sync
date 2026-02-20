import os
import json
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# Scopes required to access YouTube account
SCOPES = ['https://www.googleapis.com/auth/youtube.readonly']

def get_authenticated_service():
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"Error refreshing token: {e}")
                print("Deleting expired token.json and re-authenticating...")
                os.remove('token.json')
                creds = None
        
        if not creds:
            if not os.path.exists('client_secret.json'):
                print("Error: 'client_secret.json' not found.")
                print("Please download your OAuth 2.0 Client ID JSON from Google Cloud Console")
                print("and save it as 'client_secret.json' in this directory.")
                return None

            flow = InstalledAppFlow.from_client_secrets_file(
                'client_secret.json', SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    return build('youtube', 'v3', credentials=creds)

def list_all_playlists():
    youtube = get_authenticated_service()
    if not youtube:
        return

    # Identify who we are logged in as
    try:
        channel_response = youtube.channels().list(
            part="snippet",
            mine=True
        ).execute()
        
        if 'items' in channel_response and len(channel_response['items']) > 0:
            channel = channel_response['items'][0]
            print(f"\n=== Authenticated as Channel: {channel['snippet']['title']} ===")
            print(f"Channel ID: {channel['id']}")
            print("==========================================\n")
        else:
            print("\nWarning: Could not identify authenticated channel (no channel found for this user).")
    except Exception as e:
        print(f"Error fetching channel info: {e}")

    playlists = []
    next_page_token = None
    
    print("Fetching playlists...")
    
    while True:
        # Request playlists
        request = youtube.playlists().list(
            part="snippet,contentDetails,status",
            mine=True,
            maxResults=50,  # Maximize results per page
            pageToken=next_page_token
        )
        response = request.execute()

        # Add items to our list
        for item in response.get('items', []):
            title = item['snippet']['title']
            privacy = item['status']['privacyStatus']
            playlist_id = item['id']
            item_count = item['contentDetails']['itemCount']
            
            playlists.append({
                'title': title,
                'id': playlist_id,
                'privacy': privacy,
                'count': item_count
            })
            
            # Print as we find them
            print(f"- [{privacy}] {title} ({item_count} videos)")

        # Check if there is another page
        next_page_token = response.get('nextPageToken')
        
        if not next_page_token:
            break

    print(f"\nTotal playlists found: {len(playlists)}")
    
    # Filter for unlisted if desired
    unlisted = [p for p in playlists if p['privacy'] == 'unlisted']
    print(f"Unlisted playlists: {len(unlisted)}")
    for p in unlisted:
        print(f"  - {p['title']} (ID: {p['id']})")

if __name__ == '__main__':
    list_all_playlists()
