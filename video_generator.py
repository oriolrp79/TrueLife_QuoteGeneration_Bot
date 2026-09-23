import os
import random
import requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import numpy as np

# Pedaç de compatibilitat perquè MoviePy no falli amb versions modernes de Pillow
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.Resampling.LANCZOS

from moviepy.editor import VideoClip, CompositeVideoClip

# Claus configurades
UNSPLASH_ACCESS_KEY = "FXyqZB5bzwoFjCRUH041E11tPGU_jXundEp8mCyn87s"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# 1. GENERAR QUOTE AMB GEMINI
def get_quote():
    if GEMINI_API_KEY:
        try:
            from google import genai
            client = genai.Client(api_key=GEMINI_API_KEY)
            topics = ["grit", "discipline", "self-confidence", "action", "resilience"]
            topic = random.choice(topics)
            prompt = (
                f"Write a short, impactful motivational quote in English about {topic}. "
                "STRICT CONSTRAINT: Total length MUST NOT EXCEED 40 characters in total. "
                "Do not use quotation marks, author names or emojis. Only the sentence."
            )
            
            # Utilitzem el model actiu segons l'especificació del servei
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            q = response.text.strip().replace('"', '').replace("'", "")
            if 5 < len(q) <= 40:
                return q
        except Exception as e:
            # Si falla, provem automàticament amb gemini-1.5-flash
            try:
                from google import genai
                client = genai.Client(api_key=GEMINI_API_KEY)
                response = client.models.generate_content(
                    model="gemini-1.5-flash",
                    contents="Write a short motivational quote under 40 characters in English."
                )
                q = response.text.strip().replace('"', '').replace("'", "")
                if 5 < len(q) <= 40:
                    return q
            except Exception as inner_e:
                print(f"[Avís Gemini] Error: {inner_e}. Fent servir frase de seguretat.")

    fallbacks = [
        "Small steps lead to massive gains.",
        "Your only limit is your mindset.",
        "Action cures fear and doubt.",
        "Fall seven times, stand up eight.",
        "Doubt kills more dreams than failure.",
        "Consistency beats talent every time.",
        "Silence the noise. Focus on growth."
    ]
    return random.choice(fallbacks)

# 2. DESCARREGAR FONS D'UNSPLASH
def get_background_image(query="nature,mountains,minimal"):
    url = f"https://api.unsplash.com/photos/random?query={query}&orientation=portrait&client_id={UNSPLASH_ACCESS_KEY}"
    try:
        res = requests.get(url, timeout=10).json()
        if "urls" in res and "regular" in res["urls"]:
            img_data = requests.get(res["urls"]["regular"], timeout=10).content
            img = Image.open(BytesIO(img_data)).convert("RGB")
            # Descarreguem a una mida lleugerament més gran per poder fer el zoom netament
            return img.resize((1200, 2133), Image.Resampling.LANCZOS)
    except Exception as e:
        print(f"[Avís Unsplash] {e}")

    return Image.new("RGB", (1200, 2133), color=(18, 24, 38))

# 3. CREACIÓ DEL VÍDEO
def create_short_video(output_filename="sample_short.mp4"):
    quote = get_quote()
    if len(quote) > 40:
        quote = quote[:37] + "..."
    print(f"\n Frase: \"{quote}\" ({len(quote)} caràcters)")

    print(" Descarregant fons d'Unsplash...")
    bg_pil = get_background_image()
    w_orig, h_orig = bg_pil.size

    duration = 8  # 8 segons

    # Animació del fons amb Pillow (elimina el problema de MoviePy amb ANTIALIAS)
    def make_background_frame(t):
        # Factor de zoom lent d'1.0 a 1.08
        zoom = 1.0 + (0.01 * t)
        crop_w = int(1080 / zoom)
        crop_h = int(1920 / zoom)
        
        left = (w_orig - crop_w) // 2
        top = (h_orig - crop_h) // 2
        
        cropped = bg_pil.crop((left, top, left + crop_w, top + crop_h))
        frame_img = cropped.resize((1080, 1920), Image.Resampling.BILINEAR)
        
        # Filtre fosc (65% brillantor)
        frame_np = (np.array(frame_img) * 0.65).astype(np.uint8)
        return frame_np

    bg_clip = VideoClip(make_background_frame, ismask=False).set_duration(duration)

    # Animació de text (Typewriter progressiu durant els primers 4.5 segons)
    def make_typewriter_frame(t):
        chars_to_show = int(len(quote) * min(1.0, t / 4.5))
        current_text = quote[:chars_to_show]

        img = Image.new('RGBA', (1080, 1920), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 60)
        except:
            font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), current_text, font=font)
        w = bbox[2] - bbox[0]
        x = (1080 - w) / 2
        y = 820

        # Vora negra i text blanc per màxim contrast
        for dx, dy in [(-3, -3), (3, -3), (-3, 3), (3, 3), (0, 4)]:
            draw.text((x + dx, y + dy), current_text, font=font, fill=(0, 0, 0, 230))
        draw.text((x, y), current_text, font=font, fill=(255, 255, 255, 255))
        return np.array(img)

    text_anim_clip = VideoClip(make_typewriter_frame, ismask=False).set_duration(duration)

    # Peu de pàgina amb la marca de TrueLife
    def make_footer_frame(t):
        img = Image.new('RGBA', (1080, 1920), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        try:
            font_b = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)
            font_s = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 30)
        except:
            font_b = font_s = ImageFont.load_default()

        t1 = "Personalized Quotes"
        w1 = draw.textbbox((0, 0), t1, font=font_b)[2] - draw.textbbox((0, 0), t1, font=font_b)[0]
        x1 = (1080 - w1) / 2
        draw.text((x1 + 1, 1601), t1, font=font_b, fill=(0, 0, 0, 180))
        draw.text((x1, 1600), t1, font=font_b, fill=(240, 240, 240, 240))

        t2 = "TrueLife on Google Play"
        w2 = draw.textbbox((0, 0), t2, font=font_s)[2] - draw.textbbox((0, 0), t2, font=font_s)[0]
        x2 = (1080 - w2) / 2
        draw.text((x2 + 1, 1656), t2, font=font_sub, fill=(0, 0, 0, 180))
        draw.text((x2, 1655), t2, font=font_s, fill=(120, 200, 255, 240))
        return np.array(img)

    footer_clip = VideoClip(make_footer_frame, ismask=False).set_duration(duration)

    # Renderitzat final
    print(" Compilant vídeo MP4 H.264 (8s, 1080x1920)...")
    final_clip = CompositeVideoClip(
        [bg_clip, text_anim_clip, footer_clip],
        size=(1080, 1920)
    ).set_duration(duration)

    final_clip.write_videofile(
        output_filename,
        fps=30,
        codec="libx264",
        audio=False,
        preset="ultrafast"
    )
    print(f" Vídeo generat a: {output_filename}")
    return output_filename

if __name__ == "__main__":
    create_short_video("sample_short.mp4")
