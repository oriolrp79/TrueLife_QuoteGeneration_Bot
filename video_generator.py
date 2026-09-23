import os
import random
import requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from moviepy.editor import (
    VideoClip,
    ImageClip,
    CompositeVideoClip,
    TextClip
)
from openai import OpenAI

# 1. GENERACIÓ DE LA QUOTE (Màxim 40 caràcters)
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def get_short_quote():
    temes = ["grit", "motivation", "self-confidence", "self-learning", "assertive communication", "resilience"]
    tema = random.choice(temes)
    
    prompt = (
        f"Write an impactful, inspirational quote about {tema} in English. "
        "STRICT CONSTRAINT: Maximum 40 characters in total (including spaces and punctuation). "
        "Do not use quotation marks or author names, just the text."
    )
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=30,
        temperature=0.8
    )
    
    quote = response.choices[0].message.content.strip().replace('"', '')
    # Assegurar que compleix la restricció dels 40 caràcters
    if len(quote) > 40:
        quote = quote[:37] + "..."
    return quote

# 2. DESCARREGAR IMATGE D'UNSPLASH
def get_background_image(query="nature,inspiration"):
    UNSPLASH_ACCESS_KEY = os.environ.get("UNSPLASH_ACCESS_KEY")
    url = f"https://api.unsplash.com/photos/random?query={query}&orientation=portrait&client_id={UNSPLASH_ACCESS_KEY}"
    res = requests.get(url).json()
    img_url = res["urls"]["regular"]
    
    img_data = requests.get(img_url).content
    img = Image.open(BytesIO(img_data)).convert("RGB")
    # Redimensionar a format estàndard vertical 1080x1920
    img = img.resize((1080, 1920))
    return img

# 3. CONSTRUIR EL VÍDEO AMB ANIMACIÓ I TEXT
def create_short_video(output_path="output_short.mp4"):
    quote = get_short_quote()
    print(f"Frase generada: '{quote}' ({len(quote)} caràcters)")
    
    # Descarregar o carregar imatge
    bg_pil = get_background_image()
    bg_np = np.array(bg_pil)
    
    duration = 8  # 8 segons de durada
    
    # 2) Moviment suau a la imatge de fons (efecte Zoom-in suau)
    clip_bg = ImageClip(bg_np).set_duration(duration)
    # Factor de zoom lent: comença a escala 1.0 i acaba a 1.08 en 8 segons
    clip_bg_animated = clip_bg.resize(lambda t: 1 + 0.01 * t).set_position(('center', 'center'))

    # Capa de foscor suau (overlay negre al 30%) perquè el text blanc destaqui
    def add_dark_overlay(image):
        return (image * 0.75).astype(np.uint8)
    
    clip_bg_dark = clip_bg_animated.fl_image(add_dark_overlay)

    # 4) Animació de text progressiu (Typewriter effect)
    # Imprimeix caràcters de t=0 fins a t=5 segons, i manté el text sencer fins a t=8 segons
    def make_typewriter_frame(t):
        chars_to_show = int(len(quote) * min(1.0, t / 4.5))
        current_text = quote[:chars_to_show]
        
        # Crear imatge transparent
        img = Image.new('RGBA', (1080, 1920), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Utilitzar font estàndard gran i llegible
        try:
            font = ImageFont.truetype("DejaVuSans-Bold.ttf", 64)
        except:
            font = ImageFont.load_default()
            
        # Dibuixar text centrat verticalment
        bbox = draw.textbbox((0, 0), current_text, font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        x = (1080 - w) / 2
        y = 800  # Posició central
        
        # Petit contorn negre per assegurar la llegibilitat
        for offset in [(-2, -2), (2, -2), (-2, 2), (2, 2)]:
            draw.text((x + offset[0], y + offset[1]), current_text, font=font, fill=(0, 0, 0, 200))
        draw.text((x, y), current_text, font=font, fill=(255, 255, 255, 255))
        
        return np.array(img)

    text_anim_clip = VideoClip(make_typewriter_frame, ismask=False).set_duration(duration)

    # 5) Text fix a la part inferior central
    def make_footer_frame():
        img = Image.new('RGBA', (1080, 1920), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        try:
            font_title = ImageFont.truetype("DejaVuSans-Bold.ttf", 36)
            font_sub = ImageFont.truetype("DejaVuSans.ttf", 30)
        except:
            font_title = font_sub = ImageFont.load_default()

        # Text 1: Personalized Quotes
        t1 = "Personalized Quotes"
        w1 = draw.textbbox((0,0), t1, font=font_title)[2]
        draw.text(((1080 - w1)/2, 1620), t1, font=font_title, fill=(240, 240, 240, 230))

        # Text 2: TrueLife on Google Play
        t2 = "TrueLife on Google Play"
        w2 = draw.textbbox((0,0), t2, font=font_sub)[2]
        draw.text(((1080 - w2)/2, 1675), t2, font=font_sub, fill=(200, 220, 255, 230))

        return np.array(img)

    footer_clip = ImageClip(make_footer_frame()).set_duration(duration)

    # Composició final
    final_video = CompositeVideoClip(
        [clip_bg_dark, text_anim_clip, footer_clip],
        size=(1080, 1920)
    ).set_duration(duration)

    # Renderitzar fitxer a 30fps en MP4 H.264
    final_video.write_videofile(
        output_path,
        fps=30,
        codec="libx264",
        audio=False,
        preset="ultrafast"
    )
    return output_path, quote

if __name__ == "__main__":
    create_short_video("sample_8s_short.mp4")
