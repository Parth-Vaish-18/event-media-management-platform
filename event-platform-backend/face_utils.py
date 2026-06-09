import cv2
import numpy as np
from deepface import DeepFace
import json

def extract_face_encoding(file_bytes: bytes) -> str:
    """Extracts the SINGLE main face (Used for the Profile Selfie)."""
    try:
        nparr = np.frombuffer(file_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        # enforce_detection=True ensures the user actually uploaded a face
        embedding_objs = DeepFace.represent(img_path=img, model_name="Facenet", enforce_detection=True)
        if embedding_objs and len(embedding_objs) > 0:
            return json.dumps(embedding_objs[0]["embedding"])
        return None
    except Exception as e:
        print(f"Selfie extraction error: {e}")
        return None

def extract_all_faces(file_bytes: bytes) -> list:
    """Extracts ALL faces in a photo (Used for Event Photos)."""
    try:
        nparr = np.frombuffer(file_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        # enforce_detection=False prevents crashing if a photo has no faces (like a landscape)
        embedding_objs = DeepFace.represent(img_path=img, model_name="Facenet", enforce_detection=False)
        
        encodings = []
        for obj in embedding_objs:
            if "embedding" in obj and len(obj["embedding"]) > 0:
                 encodings.append(json.dumps(obj["embedding"]))
        return encodings
    except Exception as e:
        print(f"Crowd extraction error: {e}")
        return []

def is_match(encoding_str1: str, encoding_str2: str, threshold: float = 0.55) -> bool:
    """Compares faces. Threshold increased to 0.55 for better matching across lighting/angles."""
    try:
        if not encoding_str1 or not encoding_str2:
            return False
            
        enc1 = np.array(json.loads(encoding_str1))
        enc2 = np.array(json.loads(encoding_str2))
        
        # Calculate Cosine Distance
        distance = 1 - np.dot(enc1, enc2) / (np.linalg.norm(enc1) * np.linalg.norm(enc2))
        return bool(distance < threshold)
    except Exception as e:
        print(f"Matching error: {e}")
        return False