import tweepy

def upload_to_twitter(video_file, quote):
    client = tweepy.Client(
        consumer_key="...", consumer_secret="...",
        access_token="...", access_token_secret="..."
    )
    auth = tweepy.OAuth1UserHandler("...", "...", "...", "...")
    api = tweepy.API(auth)
    
    media = api.media_upload(filename=video_file, media_category='tweet_video')
    tweet_text = f"{quote}\n\nDownload TrueLife on Google Play."
    client.create_tweet(text=tweet_text, media_ids=[media.media_id])
