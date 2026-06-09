from transformers import pipeline
from PIL import Image
import io

# Initialize the Vision Transformer pipeline (Loads once when server starts)
try:
    image_classifier = pipeline("image-classification", model="google/vit-base-patch16-224")
except Exception as e:
    print(f"Warning: Could not load AI model. {e}")
    image_classifier = None

def generate_tags(file_bytes: bytes, num_tags: int = 3) -> list:
    """Analyzes image bytes and returns a list of string tags."""
    if not image_classifier:
        return ["auto-tag-failed"]
        
    try:
        image = Image.open(io.BytesIO(file_bytes)).convert("RGB")
        results = image_classifier(image)
        
        # Extract the top N labels
        tags = []
        for result in results[:num_tags]:
            # The model sometimes returns multiple words comma-separated (e.g. "sports car, car")
            clean_tag = result['label'].split(',')[0].strip().lower()
            tags.append(clean_tag)
            
        return tags
    except Exception as e:
        print(f"AI Tagging Error: {e}")
        return ["unclassified"]