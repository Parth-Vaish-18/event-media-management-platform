import json
import numpy as np
from deepface import DeepFace
import tempfile
import os

MODEL_NAME = "ArcFace"

def extract_face_encoding(image_bytes: bytes) -> str:
    try:
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp.write(image_bytes)
            tmp_path = tmp.name
        result = DeepFace.represent(img_path=tmp_path, model_name=MODEL_NAME, enforce_detection=True)
        os.unlink(tmp_path)
        if result:
            return json.dumps(result[0]["embedding"])
        return None
    except Exception as e:
        print(f"Selfie extraction error: {e}")
        return None

def extract_all_faces(image_bytes: bytes) -> list:
    try:
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp.write(image_bytes)
            tmp_path = tmp.name
        results = DeepFace.represent(img_path=tmp_path, model_name=MODEL_NAME, enforce_detection=False)
        os.unlink(tmp_path)
        return [json.dumps(r["embedding"]) for r in results]
    except Exception as e:
        print(f"Crowd extraction error: {e}")
        return []

def is_match(encoding_str1: str, encoding_str2: str, threshold: float = 0.55) -> bool:
    try:
        if not encoding_str1 or not encoding_str2:
            return False
        enc1 = np.array(json.loads(encoding_str1))
        enc2 = np.array(json.loads(encoding_str2))
        distance = 1 - np.dot(enc1, enc2) / (np.linalg.norm(enc1) * np.linalg.norm(enc2))
        return bool(distance < threshold)
    except Exception as e:
        print(f"Matching error: {e}")
        return False