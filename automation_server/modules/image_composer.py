# modules/image_composer.py
import os
from PIL import Image, ImageDraw, ImageFont
from modules.badge_shapes import draw_shape

# ---------------------------
# USER CONTROLLED OPTIONS
# ---------------------------
BADGE_SIZE = 200
FONT_SIZE = 70
TWO_LINE_FONT_SIZE = 50
LINE_SPACING = 4
LINK_BADGE_PATH = "images/link.png"

DISCLAIMER_TEXT = "*Prices are subject to change at any time."
CANVAS_SIZE = (1080, 1080)
BACKGROUND_COLOR = (255, 255, 255)
MARGIN = 40


# ---------------------------
# Contrast text color
# ---------------------------
def get_contrast_color(hex_color):
    hex_color = hex_color.replace("#", "")
    if len(hex_color) != 6:
        return "white"

    try:
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
    except:
        return "white"

    brightness = (r*299 + g*587 + b*114) / 1000
    return "black" if brightness > 160 else "white"


# ---------------------------
# Split into two lines max
# ---------------------------
def split_two_lines(draw, text, font, max_width):
    words = text.split(" ")
    lines = []
    current = ""

    for w in words:
        test = (current + " " + w).strip()
        if draw.textlength(test, font=font) <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = w
        if len(lines) == 2:
            break

    if current and len(lines) < 2:
        lines.append(current)

    return lines[:2]


# ---------------------------
# MAIN FUNCTION
# ---------------------------
def compose_image(
    image_path: str,
    price_text: str,
    badge_type: str = "circle",
    badge_color: str = "#FF0000",
    include_link: bool = True,   # <-- KEY
    output_path: str = None
):

    # 1. Base canvas
    canvas = Image.new("RGB", CANVAS_SIZE, BACKGROUND_COLOR)

    # 2. Product image
    product = Image.open(image_path).convert("RGB")
    product.thumbnail((CANVAS_SIZE[0] * 0.7, CANVAS_SIZE[1] * 0.7))
    px = (CANVAS_SIZE[0] - product.width) // 2
    py = (CANVAS_SIZE[1] - product.height) // 2
    canvas.paste(product, (px, py))

    draw = ImageDraw.Draw(canvas)

    # 3. Badge
    badge_size = BADGE_SIZE
    bx = CANVAS_SIZE[0] - badge_size - MARGIN
    by = MARGIN

    draw_shape(draw, badge_type.lower(), badge_color, bx, by, badge_size)
    text_color = get_contrast_color(badge_color)

    # 4. Price text
    try:
        font_main = ImageFont.truetype("arialbd.ttf", FONT_SIZE)
        font_small = ImageFont.truetype("arialbd.ttf", TWO_LINE_FONT_SIZE)
    except:
        font_main = ImageFont.load_default()
        font_small = ImageFont.load_default()

    max_w = badge_size * 0.75

    # Decide font
    lines = split_two_lines(draw, price_text, font_main, max_w)
    use_font = font_small if len(lines) == 2 else font_main
    lines = split_two_lines(draw, price_text, use_font, max_w)

    # center vertically
    total_h = sum(use_font.getbbox(line)[3] - use_font.getbbox(line)[1] for line in lines)
    total_h += (len(lines)-1) * LINE_SPACING

    start_y = by + (badge_size - total_h) / 2

    for line in lines:
        w = draw.textlength(line, font=use_font)
        draw.text(
            (bx + (badge_size - w) / 2, start_y),
            line,
            fill=text_color,
            font=use_font
        )
        start_y += (use_font.getbbox(line)[3] - use_font.getbbox(line)[1]) + LINE_SPACING

    # 5. Disclaimer
    try:
        small_font = ImageFont.truetype("arial.ttf", 24)
    except:
        small_font = ImageFont.load_default()

    dw = draw.textlength(DISCLAIMER_TEXT, font=small_font)
    draw.text(
        (CANVAS_SIZE[0] - dw - MARGIN, CANVAS_SIZE[1] - 50),
        DISCLAIMER_TEXT,
        fill="#777",
        font=small_font
    )

    # 6. link.png (ONLY IF include_link = True)
    if include_link and os.path.exists(LINK_BADGE_PATH):
        link_img = Image.open(LINK_BADGE_PATH).convert("RGBA")
        scale = 1.6
        new_w = int(link_img.width * scale)
        new_h = int(link_img.height * scale)
        link_img = link_img.resize((new_w, new_h), Image.LANCZOS)

        lx = 20
        ly = CANVAS_SIZE[1] - new_h - 20
        canvas.paste(link_img, (lx, ly), link_img)

    # 7. OUTPUT FILE
    if output_path is None:
        base, ext = os.path.splitext(image_path)
        output_path = f"{base}_final.jpg"

    canvas.save(output_path)
    return os.path.abspath(output_path)
