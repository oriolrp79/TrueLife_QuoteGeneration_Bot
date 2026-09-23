from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

def upload_to_youtube(youtube_service, video_file, quote):
    body = {
        'snippet': {
            'title': f"{quote} #Shorts #Motivation",
            'description': f"{quote}\n\nGet daily inspiration with TrueLife on Google Play.",
            'tags': ['Shorts', 'Motivation', 'TrueLife'],
            'categoryId': '22'
        },
        'status': {
            'privacyStatus': 'public',
            'selfDeclaredMadeForKids': False
        }
    }
    media = MediaFileUpload(video_file, chunksize=-1, resumable=True, mimetype='video/mp4')
    request = youtube_service.videos().insert(part=','.join(body.keys()), body=body, media_body=media)
    response = request.execute()
    print("Short publicat a YouTube:", response['id'])
