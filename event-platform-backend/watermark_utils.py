from PIL import Image, ImageDraw, ImageFont
import io
import requests

def apply_watermark(image_url: str, club_name: str, event_name: str, user_role: str) -> io.BytesIO:
    """Downloads an image from S3, applies dynamic text, and returns the byte stream."""
    try:
        # Download image from S3 URL
        response = requests.get(image_url)
        img = Image.open(io.BytesIO(response.content)).convert("RGBA")
        
        # Setup drawing context
        txt_layer = Image.new('RGBA', img.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(txt_layer)
        
        # Try to load a nice font, fallback to default
        try:
            font = ImageFont.truetype("arial.ttf", size=int(img.height * 0.03))
        except:
            font = ImageFont.load_default()
            
        watermark_text = f"© {club_name} | {event_name} | Downloaded by: {user_role}"
        
        # Position watermark at the bottom right
        margin = 15
        text_bbox = draw.textbbox((0, 0), watermark_text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        
        x = img.width - text_width - margin
        y = img.height - text_height - margin
        
        # Add shadow for visibility, then white text
        draw.text((x+2, y+2), watermark_text, fill=(0, 0, 0, 150), font=font)
        draw.text((x, y), watermark_text, fill=(255, 255, 255, 200), font=font)
        
        # Combine and prepare for download
        watermarked = Image.alpha_composite(img, txt_layer).convert("RGB")
        
        img_byte_arr = io.BytesIO()
        watermarked.save(img_byte_arr, format='JPEG', quality=90)
        img_byte_arr.seek(0)
        
        return img_byte_arr
    except Exception as e:
        print(f"Watermark error: {e}")
        return None