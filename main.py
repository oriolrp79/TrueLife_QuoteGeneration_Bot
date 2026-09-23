import os
from video_generator import create_short_video
# Importem els mòduls de pujada
try:
    from uploader_youtube import upload_to_youtube
except ImportError:
    upload_to_youtube = None

try:
    from uploader_twitter import upload_to_twitter
except ImportError:
    upload_to_twitter = None

def run():
    output_filename = "short_to_publish.mp4"
    print("Generant vídeo...")
    video_path, quote = create_short_video(output_filename)
    
    caption = f"{quote}\n\nGet daily personalized quotes with TrueLife on Google Play.\n#TrueLife #Quotes #Motivation #Shorts"
    
    # 1. Pujar a Twitter / X
    if upload_to_twitter:
        try:
            print("Pujant a Twitter...")
            upload_to_twitter(video_path, caption)
        except Exception as e:
            print(f"Error a Twitter: {e}")

    # 2. Pujar a YouTube Shorts
    if upload_to_youtube:
        try:
            print("Pujant a YouTube...")
            upload_to_youtube(video_path, quote, caption)
        except Exception as e:
            print(f"Error a YouTube: {e}")

    # 3. Netejar fitxer local
    if os.path.exists(output_filename):
        os.remove(output_filename)
    print("Procés finalitzat amb èxit!")

if __name__ == "__main__":
    run()
