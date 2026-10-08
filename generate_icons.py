from PIL import Image, ImageDraw, ImageFont
import os

def create_icon(size, output_path):
    """Create a square icon with 'RA' text"""
    # Create image with the primary color
    img = Image.new('RGB', (size, size), color='#447090')
    draw = ImageDraw.Draw(img)

    # Try to use a system font, fallback to default
    try:
        font_size = int(size * 0.4)
        font = ImageFont.truetype("arial.ttf", font_size)
    except:
        font = ImageFont.load_default()

    # Calculate text position (centered)
    text = "RA"
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
    except:
        text_width = draw.textlength(text, font=font)
        text_height = font_size

    x = (size - text_width) // 2
    y = (size - text_height) // 2

    # Draw white text
    draw.text((x, y), text, fill='white', font=font)

    # Save as PNG
    img.save(output_path, 'PNG')
    print(f"Created {output_path}")

if __name__ == "__main__":
    static_dir = os.path.join(os.path.dirname(__file__), 'app', 'static')
    os.makedirs(static_dir, exist_ok=True)

    create_icon(192, os.path.join(static_dir, 'icon-192.png'))
    create_icon(512, os.path.join(static_dir, 'icon-512.png'))
