import os
import random
import math
import time
import requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageStat
import numpy as np

# Compatibilitat de MoviePy v1 i v2
try:
    from moviepy.editor import VideoClip
except ImportError:
    from moviepy import VideoClip

# --- CONFIGURACIÓ DE CLAUS ---
# --- CONFIGURACIÓ DE CLAUS ---
UNSPLASH_ACCESS_KEY = os.environ.get("UNSPLASH_ACCESS_KEY", "FXyqZB5bzwoFjCRUH041E11tPGU_jXundEp8mCyn87s")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FONTS_DIR = os.path.join(SCRIPT_DIR, "fonts")
os.makedirs(FONTS_DIR, exist_ok=True)

OFFICIAL_FONT_URLS = {
    "PlayfairDisplaySC": "https://github.com/google/fonts/raw/main/ofl/playfairdisplaysc/PlayfairDisplaySC-Bold.ttf",
    "OleoScriptSwashCaps": "https://github.com/google/fonts/raw/main/ofl/oleoscriptswashcaps/OleoScriptSwashCaps-Bold.ttf",
    "WorkSans": "https://github.com/google/fonts/raw/main/ofl/worksans/static/WorkSans-Bold.ttf",
    "WorkSans_Italic": "https://github.com/google/fonts/raw/main/ofl/worksans/static/WorkSans-MediumItalic.ttf"
}

def load_font(font_name, size, fallback_sys=None):
    """Carrega la font de la carpeta local /fonts o del sistema."""
    target_path = os.path.join(FONTS_DIR, f"{font_name}.ttf")
    if not os.path.exists(target_path):
        url = OFFICIAL_FONT_URLS.get(font_name)
        if url:
            try:
                print(f"Descarregant font {font_name}...")
                resp = requests.get(url, timeout=12, allow_redirects=True)
                if resp.status_code == 200 and len(resp.content) > 5000:
                    with open(target_path, "wb") as f:
                        f.write(resp.content)
            except Exception as e:
                print(f"[Avís Font] No s'ha pogut descarregar {font_name}: {e}")

    if os.path.exists(target_path):
        try:
            return ImageFont.truetype(target_path, size)
        except Exception:
            pass

    # Alternativa del sistema
    sys_candidates = fallback_sys or ["arialbd.ttf", "DejaVuSans-Bold.ttf", "segoeuib.ttf"]
    for sys_font in sys_candidates:
        try:
            return ImageFont.truetype(sys_font, size)
        except:
            continue
    return ImageFont.load_default()

# 1. GENERACIÓ DE LA QUOTE AMB GEMINI 3.6+ (Fins a 60 caràcters)
def get_quote():
    if GEMINI_API_KEY:
        from google import genai
        client = genai.Client(api_key=GEMINI_API_KEY)
        topics = ["grit", "discipline", "self-confidence", "action", "resilience", "inner strength", "perseverance", "clarity"]
        topic = random.choice(topics)
        prompt = (
            f"Write a deep, powerful motivational quote in English about {topic}. "
            "STRICT CONSTRAINT: Total length MUST NOT EXCEED 60 characters in total (including spaces and punctuation). "
            "Do not use quotation marks, author names or emojis. Only the sentence."
        )

        candidate_models = ["gemini-3.6-flash", "gemini-3.5-flash", "gemini-2.5-flash"]
        for model_name in candidate_models:
            for attempt in range(1, 3):
                try:
                    response = client.models.generate_content(model=model_name, contents=prompt)
                    q = response.text.strip().replace('"', '').replace("'", "")
                    if 5 < len(q) <= 60:
                        return q
                except Exception as e:
                    err = str(e)
                    if "503" in err or "429" in err:
                        time.sleep(attempt * 2)
                    else:
                        break

    fallbacks = [
        "Small daily habits create massive lifelong changes.",
        "Your only real limit is the story you tell yourself.",
        "Discipline will take you where motivation cannot.",
        "Do what is difficult today so tomorrow becomes easier.",
        "Doubt kills more dreams than failure ever will.",
        "Fall seven times and stand up eight with purpose.",
        "Silence the external noise and focus on daily growth."
    ]
    return random.choice(fallbacks)

# 2. FILTRE PER DESCARTAR FOTOS EN BLANC I NEGRE
def is_color_image(pil_img):
    stat = ImageStat.Stat(pil_img)
    r_mean, g_mean, b_mean = stat.mean[:3]
    diff = abs(r_mean - g_mean) + abs(g_mean - b_mean) + abs(b_mean - r_mean)
    return diff > 15.0

# 3. DESCARREGAR FONS LLUMINÓS I EN COLOR REAL D'UNSPLASH
def get_background_image():
    bright_queries = [
        "bright turquoise tropical beach sunny",
        "vivid green alpine mountain valley sunny",
        "majestic golden sunrise landscape vivid colorful",
        "bright sunny river waterfall lush nature",
        "spectacular blue sky fjords reflection colorful"
    ]

    for _ in range(3):
        query = random.choice(bright_queries)
        url = f"https://api.unsplash.com/photos/random?query={query}&orientation=portrait&color_filter=color&client_id={UNSPLASH_ACCESS_KEY}"
        try:
            res = requests.get(url, timeout=10).json()
            if "urls" in res and "regular" in res["urls"]:
                img_data = requests.get(res["urls"]["regular"], timeout=10).content
                img = Image.open(BytesIO(img_data)).convert("RGB")
                if is_color_image(img):
                    return img.resize((1500, 2600), Image.Resampling.LANCZOS)
                else:
                    print("[Filtre] Imatge en blanc i negre detectada i rebutjada. Reintentant...")
        except Exception as e:
            print(f"[Avís Unsplash] {e}")

    return Image.new("RGB", (1500, 2600), color=(30, 85, 130))

def wrap_text(draw, text, font, max_width=880):
    words = text.split()
    lines = []
    current_line = []
    for word in words:
        test_line = " ".join(current_line + [word])
        bbox = draw.textbbox((0, 0), test_line, font=font)
        w = bbox[2] - bbox[0]
        if w <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(" ".join(current_line))
            current_line = [word]
    if current_line:
        lines.append(" ".join(current_line))
    return lines

# 4. CREACIÓ DEL VÍDEO
def create_short_video(output_filename="sample_short.mp4"):
    quote = get_quote()
    if len(quote) > 60:
        quote = quote[:57] + "..."
    print(f"\n Frase: \"{quote}\" ({len(quote)} caràcters)")

    print(" Descarregant fons en color radiant...")
    bg_pil = get_background_image()
    w_orig, h_orig = bg_pil.size

    duration = 8  # 8 segons de durada

    # Selecció aleatòria per a la quote
    font_choice = random.choice(["PlayfairDisplaySC", "OleoScriptSwashCaps", "WorkSans"])
    print(f" Estil tipogràfic seleccionat per a la quote: {font_choice}")
    
    if font_choice == "OleoScriptSwashCaps":
        font_size = 92
    elif font_choice == "PlayfairDisplaySC":
        font_size = 82
    else:
        font_size = 86

    font_quote = load_font(font_choice, font_size)

    # El peu de pàgina SEMPRE en Sans Serif neta
    # 1. "Personalized Quotes" -> Sans Serif bold
    font_title = load_font("WorkSans", 66, fallback_sys=["arialbd.ttf", "DejaVuSans-Bold.ttf"])
    # 2. "TrueLife on Google Play" -> Sans Serif cursiva (Italic)
    font_italic = load_font("WorkSans_Italic", 52, fallback_sys=["ariali.ttf", "DejaVuSans-Oblique.ttf"])

    # Carregar i redimensionar el logotip de Google Play (googlelogo.png)
    logo_path = os.path.join(SCRIPT_DIR, "googlelogo.png")
    google_logo_img = None
    if os.path.exists(logo_path):
        try:
            raw_logo = Image.open(logo_path).convert("RGBA")
            target_h = 75  # Alçada proporcionada
            aspect = raw_logo.width / raw_logo.height
            target_w = int(target_h * aspect)
            google_logo_img = raw_logo.resize((target_w, target_h), Image.Resampling.LANCZOS)
            print(f" Logo carregat correctament ({target_w}x{target_h}px)")
        except Exception as e:
            print(f"[Avís Logo] No s'ha pogut carregar googlelogo.png: {e}")
    else:
        print(f"[Avís Logo] No s'ha trobat googlelogo.png a {logo_path}")

    # Maquetació estàtica de la quote
    dummy_img = Image.new('RGB', (1080, 1920))
    dummy_draw = ImageDraw.Draw(dummy_img)
    lines = wrap_text(dummy_draw, quote, font_quote, max_width=880)

    line_height = int(font_size * 1.25)
    total_text_h = len(lines) * line_height
    start_y = 620 - (total_text_h // 2)

    layout_lines = []
    current_y = start_y
    for l in lines:
        bbox = dummy_draw.textbbox((0, 0), l, font=font_quote)
        w_l = bbox[2] - bbox[0]
        x_l = (1080 - w_l) // 2
        layout_lines.append({
            "text": l,
            "x": x_l,
            "y": current_y
        })
        current_y += line_height

    total_chars = len(quote)

    def make_frame(t):
        theta = 2.0 * math.pi * (t / duration)

        # Moviment circular tancat (comença i acaba exactament al mateix punt)
        shift_x = int(35 * math.sin(theta))
        shift_y = int(22 * (math.cos(theta) - 1.0))
        zoom = 1.18 + 0.07 * (1.0 - math.cos(theta)) / 2.0
        angle = 1.3 * math.sin(theta)

        crop_w = int(1080 / zoom)
        crop_h = int(1920 / zoom)

        center_x = (w_orig // 2) + shift_x
        center_y = (h_orig // 2) + shift_y

        left = max(0, min(w_orig - crop_w, center_x - (crop_w // 2)))
        top = max(0, min(h_orig - crop_h, center_y - (crop_h // 2)))

        cropped = bg_pil.crop((left, top, left + crop_w, top + crop_h))

        margin_w = int(1080 * 1.06)
        margin_h = int(1920 * 1.06)
        frame_scaled = cropped.resize((margin_w, margin_h), Image.Resampling.BILINEAR)
        rotated_frame = frame_scaled.rotate(angle, resample=Image.Resampling.BICUBIC)

        cut_x = (margin_w - 1080) // 2
        cut_y = (margin_h - 1920) // 2
        frame_img = rotated_frame.crop((cut_x, cut_y, cut_x + 1080, cut_y + 1920))

        # 80% de llum natural viva
        frame_np = (np.array(frame_img) * 0.80).astype(np.uint8)
        frame_pil = Image.fromarray(frame_np, 'RGB')
        draw = ImageDraw.Draw(frame_pil)

        # CÀLCUL D'APARICIÓ ADAPTATIVA (Acaba exactament al segon 7.0)
        typing_duration = 7.0
        typing_progress = min(1.0, t / typing_duration)
        chars_revealed = int(total_chars * typing_progress)
        chars_count = 0

        for line_data in layout_lines:
            line_str = line_data["text"]
            x = line_data["x"]
            y = line_data["y"]

            if chars_revealed > chars_count:
                visible_len = min(len(line_str), chars_revealed - chars_count)
                part_to_show = line_str[:visible_len]

                draw.text(
                    (x, y),
                    part_to_show,
                    font=font_quote,
                    fill=(255, 255, 255),
                    stroke_width=6,
                    stroke_fill=(0, 0, 0)
                )

            chars_count += len(line_str) + 1

        # PEU DE PÀGINA ELEVAT (ZONA SEGURA) EN SANS SERIF
        # 1. "Personalized Quotes" a Y=1240
        t1 = "Personalized Quotes"
        w1 = draw.textbbox((0, 0), t1, font=font_title)[2] - draw.textbbox((0, 0), t1, font=font_title)[0]
        x1 = (1080 - w1) // 2
        y1 = 1240
        draw.text((x1, y1), t1, font=font_title, fill=(255, 255, 255), stroke_width=4, stroke_fill=(0, 0, 0))

        # 2. "TrueLife on Google Play" a Y=1315 (Cursiva)
        t2 = "TrueLife on Google Play"
        w2 = draw.textbbox((0, 0), t2, font=font_italic)[2] - draw.textbbox((0, 0), t2, font=font_italic)[0]
        x2 = (1080 - w2) // 2
        y2 = 1315
        draw.text((x2, y2), t2, font=font_italic, fill=(255, 255, 255), stroke_width=4, stroke_fill=(0, 0, 0))

        # 3. Logotip de Google Play sota del text (Y=1380) amb canal alfa
        if google_logo_img:
            logo_x = (1080 - google_logo_img.width) // 2
            logo_y = 1380
            frame_pil.paste(google_logo_img, (logo_x, logo_y), mask=google_logo_img.split()[3])

        return np.array(frame_pil)

    print(" Compilant vídeo MP4 H.264 (8s, 1080x1920)...")
    final_clip = VideoClip(make_frame, duration=duration)

    final_clip.write_videofile(
        output_filename,
        fps=30,
        codec="libx264",
        audio=False,
        preset="ultrafast"
    )
    print(f"\n Vídeo generat amb èxit a: {output_filename}")
    return output_filename

if __name__ == "__main__":
    create_short_video("sample_short.mp4")