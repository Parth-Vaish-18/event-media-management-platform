from PIL import Image
import io
from transformers import BlipProcessor, BlipForConditionalGeneration
import torch

print("Loading BLIP captioning model (one-time, please wait)...")
processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")
model.eval()

def process_image_via_ai(image_bytes: bytes) -> dict:
    try:
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        inputs = processor(image, return_tensors="pt")
        with torch.no_grad():
            out = model.generate(**inputs, max_new_tokens=50)
        caption = processor.decode(out[0], skip_special_tokens=True)
        return {"status": "success", "caption": caption}
    except Exception as e:
        return {"status": "error", "caption": "event photo", "message": str(e)}

def generate_tags(image_bytes: bytes, num_tags: int = 5) -> list:
    stop_words = {
        "a","an","the","in","on","at","of","with","and","is","are",
        "sitting","standing","playing","looking","posing","holding",
        "man","woman","people","person","group","some","there","two","three"
    }
    result = process_image_via_ai(image_bytes)
    caption = result.get("caption", "event photo")
    clean = caption.lower().replace(".", "").replace(",", "").replace("-", " ")
    words = clean.split()
    tags = [w for w in words if w not in stop_words and len(w) > 2]
    return tags[:num_tags] if tags else ["event"]