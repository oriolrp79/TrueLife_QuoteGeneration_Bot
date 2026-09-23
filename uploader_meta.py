import os
import time
import requests

def upload_to_instagram_and_fb(video_url, caption):
    ig_user_id = os.environ.get("INSTAGRAM_ACCOUNT_ID")
    access_token = os.environ.get("META_ACCESS_TOKEN")
    
    if not ig_user_id or not access_token:
        print("Meta credentials missing, skipping...")
        return

    # 1. Crear el contenidor del Reel a Instagram
    # share_to_feed=true i també replica a Facebook si està vinculat a nivell de pàgina
    init_url = f"https://graph.facebook.com/v19.0/{ig_user_id}/media"
    payload = {
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption,
        "share_to_feed": True,
        "access_token": access_token
    }
    res = requests.post(init_url, data=payload).json()
    creation_id = res.get("id")
    if not creation_id:
        print("Error creant contenidor Meta:", res)
        return

    # 2. Esperar que Meta processi el vídeo
    print("Processant vídeo a Meta...")
    status_url = f"https://graph.facebook.com/v19.0/{creation_id}?fields=status_code&access_token={access_token}"
    for _ in range(15):
        time.sleep(5)
        status_res = requests.get(status_url).json()
        status = status_res.get("status_code")
        if status == "FINISHED":
            break
        elif status == "ERROR":
            print("Error en el processament de Meta")
            return

    # 3. Publicar el Reel
    publish_url = f"https://graph.facebook.com/v19.0/{ig_user_id}/media_publish"
    pub_res = requests.post(publish_url, data={
        "creation_id": creation_id,
        "access_token": access_token
    }).json()
    print("Reel publicat amb èxit:", pub_res)
