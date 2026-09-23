import os
import random
import requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from moviepy.editor import VideoClip, ImageClip, CompositeVideoClip

# Claus configurades
UNSPLASH_ACCESS_KEY = "FXyqZB5bzwoFjCRUH041E11tPGU_jXundEp8mCyn87s"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# 1. GENERAR QUOTE AMB GEMINI PRO
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
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            q = response.text.strip().replace('"', '').replace("'", "")
            if 5 < len(q) <= 40:
                return q
        except Exception as e:
            print(f"[Avís Gemini] {e}. Fent servir frase de seguretat.")

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
            return img.resize((1080, 1920), Image.Resampling.LANCZOS)
    except Exception as e:
        print(f"[Avís Unsplash] {e}")

    return Image.new("RGB", (1080, 1920), color=(18, 24, 38))

# 3. CREACIÓ DEL VÍDEO
def create_short_video(output_filename="output_short.mp4"):
    quote = get_quote()
    if len(quote) > 40:
        quote = quote[:37] + "..."
    print(f"\n Frase: \"{quote}\" ({len(quote)} caràcters)")

    print(" Descarregant fons d'Unsplash...")
    bg_pil = get_background_image()
    bg_np = np.array(bg_pil)

    duration = 8  # 8 segons

    # Zoom suau (Ken Burns)
    clip_bg = ImageClip(bg_np).set_duration(duration)
    clip_bg_animated = clip_bg.resize(lambda t: 1.0 + 0.012 * t).set_position(('center', 'center'))

    # Filtre fosc per contrast
    def add_dark_filter(frame):
        return (frame * 0.65).astype(np.uint8)
    clip_bg_dark = clip_bg_animated.fl_image(add_dark_filter)

    # Animació de text (Typewriter)
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

        # Vora negra i text blanc
        for dx, dy in [(-3, -3), (3, -3), (-3, 3), (3, 3), (0, 4)]:
            draw.text((x + dx, y + dy), current_text, font=font, fill=(0, 0, 0, 230))
        draw.text((x, y), current_text, font=font, fill=(255, 255, 255, 255))
        return np.array(img)

    text_anim_clip = VideoClip(make_typewriter_frame, ismask=False).set_duration(duration)

    # Peu de pàgina fix amb branding
    def make_footer_frame():
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
        draw.text((x2 + 1, 1656), t2, font=font_s, fill=(0, 0, 0, 180))
        draw.text((x2, 1655), t2, font=font_s, fill=(120, 200, 255, 240))
        return np.array(img)

    footer_clip = ImageClip(make_footer_frame()).set_duration(duration)

    # Muntatge i exportació
    print(" Compilant vídeo MP4 H.264...")
    final_clip = CompositeVideoClip(
        [clip_bg_dark, text_anim_clip, footer_clip],
        size=(1080, 1920)
    ).set_duration(duration)

    final_clip.write_videofile(
        output_filename,
        fps=30,
        codec="libx264",
        audio=False,
        preset="ultrafast"
    )
    print(f" Vídeo creat a: {output_filename}")
    return output_filename

if __name__ == "__main__":
    create_short_video("sample_short.mp4")
