import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'  
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0' 

import json
from fastapi import FastAPI, Depends, HTTPException, File, UploadFile, Form, WebSocket, WebSocketDisconnect, status
from fastapi.responses import StreamingResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from jose import JWTError, jwt

import models, schemas, auth_utils, s3_utils, ai_utils, face_utils, watermark_utils
from database import engine, SessionLocal

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Event & Media Management API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"],
    expose_headers=["Content-Disposition"]
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- AUTHENTICATION DEPENDENCIES ---
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")
    try:
        payload = jwt.decode(token, auth_utils.SECRET_KEY, algorithms=[auth_utils.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db.query(models.User).filter(models.User.email == email).first()
    if user is None:
        raise credentials_exception
    return user

# --- REAL-TIME WEBSOCKETS ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                pass

manager = ConnectionManager()

@app.websocket("/ws/notifications")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.post("/register", response_model=schemas.UserResponse)
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    if db.query(models.User).filter(models.User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    safe_role = user.role
    
    # --- ADMIN SECRET KEY CHECK ---
    if safe_role == models.UserRole.ADMIN:
        import os
        # Set your master password here (or in your .env file)
        correct_secret = os.getenv("ADMIN_SECRET_KEY","EMP-ADMIN-2026")
        if user.admin_secret != correct_secret:
            raise HTTPException(status_code=403, detail="Invalid Admin Secret Key!")

    hashed_password = auth_utils.get_password_hash(user.password)
    new_user = models.User(
        name=user.name, 
        email=user.email, 
        password_hash=hashed_password, 
        role=safe_role
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not auth_utils.verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    
    access_token = auth_utils.create_access_token(data={"sub": user.email, "role": user.role})
    return {"access_token": access_token, "token_type": "bearer", "user_id": user.id, "role": user.role, "name": user.name}

# --- EVENT ROUTES ---
@app.post("/events/", response_model=schemas.EventResponse)
def create_event(event: schemas.EventCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if current_user.role not in [models.UserRole.ADMIN, models.UserRole.PHOTOGRAPHER]:
        raise HTTPException(status_code=403, detail="Not authorized to create events")
    # PATCH: Updated to model_dump()
    new_event = models.Event(**event.model_dump())
    db.add(new_event)
    db.commit()
    db.refresh(new_event)
    return new_event

@app.get("/events/")
def get_events(sort_by: str = "date", db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    query = db.query(models.Event)
    
    if sort_by == "name":
        query = query.order_by(models.Event.name)
    elif sort_by == "category":
        query = query.order_by(models.Event.category)
    else:
        query = query.order_by(models.Event.date.desc())
    
    events = query.all()
    
    result = []
    for ev in events:
        # 1. Start the base query for media in this specific event
        media_query = db.query(models.Media).filter(models.Media.event_id == ev.id)
        
        # 2. PRIVACY GUARD: If they aren't an Admin or Member, force the query to only count public media!
        if current_user.role not in [models.UserRole.ADMIN, models.UserRole.MEMBER]:
            media_query = media_query.filter(models.Media.is_public == True)
            
        # 3. Execute the safe count
        media_count = media_query.count()
        
        result.append({
            "id": ev.id,
            "name": ev.name,
            "description": ev.description,
            "category": ev.category,
            "date": ev.date,
            "created_at": ev.created_at,
            "media_count": media_count      
        })
    
    return result

@app.delete("/events/{event_id}")
def delete_event(event_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    # 1. Strict Admin Guard
    if current_user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only Admins can delete events.")

    event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found.")

    # 2. Safe Cascade Delete (Cleans up all connected data so the DB doesn't break)
    media_items = db.query(models.Media).filter(models.Media.event_id == event_id).all()
    for m in media_items:
        db.query(models.Like).filter(models.Like.media_id == m.id).delete()
        db.query(models.Favorite).filter(models.Favorite.media_id == m.id).delete()
        db.query(models.Comment).filter(models.Comment.media_id == m.id).delete()
        db.delete(m)

    # 3. Delete the actual event
    db.delete(event)
    db.commit()
    
    return {"message": "Event permanently deleted."}

# --- BULK MEDIA UPLOAD (NOW WITH MULTI-FACE CROWD SCANNER) ---
@app.post("/media/upload/")
async def upload_media(
    event_id: int = Form(...),
    is_public: bool = Form(True),
    files: List[UploadFile] = File(...), 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role == models.UserRole.VIEWER:
        raise HTTPException(status_code=403, detail="Viewers cannot upload media")

    if not files or len(files) == 0:
        raise HTTPException(status_code=400, detail="No files received by server.")

    uploaded_count = 0
    failed_count = 0

    for file in files:
        try:
            file_bytes = await file.read()
            is_video = file.content_type.startswith('video/')
            tags = []
            matched_user = None

            if is_video:
                tags = ["Video"] 
            else:
                tags = ai_utils.generate_tags(file_bytes)
                
                # --- NEW: Extract every single face in the crowd ---
                all_faces_in_photo = face_utils.extract_all_faces(file_bytes)
                matched_users_list = []
                
                if all_faces_in_photo:
                    all_users = db.query(models.User).filter(models.User.face_encoding.isnot(None)).all()
                    
                    # Compare every face in the photo against every registered user
                    for photo_face in all_faces_in_photo:
                        for u in all_users:
                            if face_utils.is_match(photo_face, u.face_encoding):
                                if u.name not in matched_users_list:
                                    matched_users_list.append(u.name)
                                    await manager.broadcast(json.dumps({"type": "tag", "message": f"{u.name} was tagged in a new photo!"}))
                                    
                # Save as a comma-separated string (e.g., "Elon Musk, Bill Gates")
                matched_user = ", ".join(matched_users_list) if matched_users_list else None
                        
            file.file.seek(0)
            s3_url = s3_utils.upload_file_to_s3(file.file, file.filename, file.content_type)
            
            if not s3_url:
                failed_count += 1
                continue 
                
            new_media = models.Media(
                event_id=event_id,
                uploader_id=current_user.id,
                s3_url=s3_url,
                is_public=is_public,
                ai_tags=json.dumps(tags), 
                person_detected=matched_user
            )
            db.add(new_media)
            db.commit()
            uploaded_count += 1
            
        except Exception as e:
            print(f"CRITICAL ERROR processing {file.filename}: {str(e)}")
            failed_count += 1
    
    if uploaded_count == 0:
        raise HTTPException(status_code=500, detail=f"All {failed_count} files failed to upload.")
        
    return {"message": f"Success! Uploaded {uploaded_count} files. ({failed_count} failed)."}

# ---------------------------------------------------------------------------
# FETCH EVENT MEDIA
# ---------------------------------------------------------------------------
@app.get("/events/{event_id}/media/", tags=["Media"])
def get_event_media(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Returns all media for an event, filtered by access control."""
    video_extensions = ('.mp4', '.mov', '.avi', '.webm', '.mkv')
    media_list = (
        db.query(models.Media)
        .filter(models.Media.event_id == event_id)
        .order_by(models.Media.id.desc())
        .all()
    )

    results = []
    for m in media_list:
        # Access control: private media visible only to Admins and Club Members
        if not m.is_public and current_user.role not in [
            models.UserRole.ADMIN, models.UserRole.MEMBER
        ]:
            continue

        is_liked = (
            db.query(models.Like)
            .filter(models.Like.media_id == m.id, models.Like.user_id == current_user.id)
            .first()
        ) is not None
        is_fav = (
            db.query(models.Favorite)
            .filter(models.Favorite.media_id == m.id, models.Favorite.user_id == current_user.id)
            .first()
        ) is not None

        comments = db.query(models.Comment).filter(models.Comment.media_id == m.id).all()
        like_count = db.query(models.Like).filter(models.Like.media_id == m.id).count()
        clean_tags = json.loads(m.ai_tags) if m.ai_tags else []
        media_type = "video" if m.s3_url.lower().endswith(video_extensions) else "image"

        results.append({
            "id": m.id,
            "url": m.s3_url,
            "type": media_type,
            "uploader_name": m.uploader.name,
            "ai_tags": clean_tags,
            "person_detected": m.person_detected,
            "is_public": m.is_public,
            "is_liked": is_liked,
            "is_favorited": is_fav,
            "like_count": like_count,
            "views_count": m.views_count or 0,
            "is_highlight": m.is_highlight,
            "comments": [
                {"id": c.id, "user": c.user.name, "user_id": c.user_id, "text": c.text}
                for c in comments
            ],
            "uploaded_at": m.uploaded_at.isoformat() if m.uploaded_at else None,
        })

    return results

@app.post("/media/{media_id}/view/", tags=["Media"])
def track_view(
    media_id: int, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(get_current_user)
):
    """Tracks a genuine view when a user scrolls the photo into their screen."""
    media = db.query(models.Media).filter(models.Media.id == media_id).first()
    if media:
        media.views_count = (media.views_count or 0) + 1
        db.commit()
    return {"message": "View tracked"}

# --- SOCIAL ACTIONS ---
@app.post("/media/{media_id}/like/")
async def toggle_like(media_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    existing = db.query(models.Like).filter(models.Like.media_id == media_id, models.Like.user_id == current_user.id).first()
    if existing:
        db.delete(existing)
        db.commit()
        return {"message": "Unliked"}
    
    db.add(models.Like(media_id=media_id, user_id=current_user.id))
    db.commit()
    await manager.broadcast(json.dumps({"type": "like", "message": f"{current_user.name} liked a post!"}))
    return {"message": "Liked"}

@app.patch("/media/{media_id}/highlight/")
async def toggle_highlight(media_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if current_user.role not in [models.UserRole.ADMIN, models.UserRole.PHOTOGRAPHER]:
        raise HTTPException(status_code=403, detail="Only Admins and Photographers can feature media.")
    media = db.query(models.Media).filter(models.Media.id == media_id).first()
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")
        
    media.is_highlight = not media.is_highlight
    db.commit()
    
    # FIX: Broadcast the highlight event to all other users looking at the gallery
    await manager.broadcast(json.dumps({"type": "highlight", "message": "An event photo was featured!"}))
    
    return {"is_highlight": media.is_highlight}

@app.post("/media/{media_id}/favorite/")
def toggle_favorite(media_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    existing = db.query(models.Favorite).filter(models.Favorite.media_id == media_id, models.Favorite.user_id == current_user.id).first()
    if existing:
        db.delete(existing)
        db.commit()
        return {"message": "Removed from favorites"}
    
    db.add(models.Favorite(media_id=media_id, user_id=current_user.id))
    db.commit()
    return {"message": "Added to favorites"}

@app.post("/media/{media_id}/comment/")
async def add_comment(media_id: int, comment: schemas.CommentCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    new_comment = models.Comment(media_id=media_id, user_id=current_user.id, text=comment.text)
    db.add(new_comment)
    db.commit()
    db.refresh(new_comment)
    await manager.broadcast(json.dumps({"type": "comment", "message": f"{current_user.name} commented: {comment.text}"}))
    return {
        "message": "Comment posted",
        "comment": {
            "id": new_comment.id,
            "user": current_user.name,
            "user_id": current_user.id,
            "text": new_comment.text
        }
    }

# --- SAFE DOWNLOAD ROUTE ---
@app.get("/media/{media_id}/download/")
def download_media(media_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    media = db.query(models.Media).filter(models.Media.id == media_id).first()
    
    # PATCH: Added 404 Guard
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")
        
    media.downloads += 1
    db.commit()
    event = db.query(models.Event).filter(models.Event.id == media.event_id).first()
    
    is_video = media.s3_url.lower().endswith(('.mp4', '.mov', '.avi', '.webm', '.mkv'))
    
    if is_video:
        return RedirectResponse(url=media.s3_url)
    
    watermarked_bytes = watermark_utils.apply_watermark(
        image_url=media.s3_url,
        club_name="Tech Innovators Club",
        event_name=event.name if event else "Event",
        user_role=current_user.role.value
    )
    
    filename = f"watermarked_{media.s3_url.split('/')[-1].split('_', 1)[-1].rsplit('.', 1)[0]}.jpg"
    return StreamingResponse(watermarked_bytes, media_type="image/jpeg", headers={"Content-Disposition": f"attachment; filename={filename}"})

# --- PERSONALIZED AI PROFILE ROUTES ---
@app.post("/profile/selfie/")
async def register_selfie(file: UploadFile = File(...), db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    file_bytes = await file.read()
    encoding = face_utils.extract_face_encoding(file_bytes)
    
    if not encoding:
        raise HTTPException(status_code=400, detail="No face detected. Please try a clearer photo.")
        
    current_user.face_encoding = encoding
    db.commit()
    
    return {"message": "Face registered successfully! The AI will now auto-match you."}

@app.get("/profile/matches/")
def get_my_matches(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """Fetches every single photo across all events where the AI detected this user."""
    # CHANGED TO .contains(): Allows finding "Elon Musk" even if he is in a group photo tagged "Bill Gates, Elon Musk"
    matched_media = db.query(models.Media).filter(
        models.Media.person_detected.isnot(None),
        models.Media.person_detected.contains(current_user.name)
    ).order_by(models.Media.id.desc()).all()
    
    results = []
    for m in matched_media:
        clean_tags = json.loads(m.ai_tags) if m.ai_tags else []
        is_video = m.s3_url.lower().endswith(('.mp4', '.mov', '.avi', '.webm'))
        results.append({
            "id": m.id,
            "url": m.s3_url,
            "type": "video" if is_video else "image",
            "ai_tags": clean_tags,
            "event_id": m.event_id
        })
    return results

# --- ANALYTICS & TRACKING ROUTES ---

@app.post("/media/{media_id}/share/")
# PATCH: Added current_user dependency to protect the route
def track_share(media_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """Silent route that increments the share counter when someone clicks Share."""
    media = db.query(models.Media).filter(models.Media.id == media_id).first()
    if media:
        media.shares += 1
        db.commit()
    return {"message": "Share tracked"}

@app.get("/analytics/dashboard/")
def get_analytics(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """Returns platform-wide metrics (Admins Only)."""
    if current_user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Unauthorized. Admins only.")
        
    total_users = db.query(models.User).count()
    
    # 🚀 FIX 1: Only count media that is strictly attached to an existing Event.
    # This automatically filters out any "ghost" data from early testing.
    total_media = db.query(models.Media).join(models.Event).count()
    
    # 🚀 FIX 2: Apply the same strict rule to likes
    total_likes = db.query(models.Like).join(models.Media).join(models.Event).count()
    
    # 🚀 FIX 3: Sum downloads and shares only from valid, active media
    valid_media = db.query(models.Media).join(models.Event).all()
    total_downloads = sum(m.downloads for m in valid_media)
    total_shares = sum(m.shares for m in valid_media)

    return {
        "users": total_users,
        "media": total_media,
        "likes": total_likes,
        "downloads": total_downloads,
        "shares": total_shares
    }
    
@app.delete("/media/{media_id}/")
def delete_media(media_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if current_user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only Admins can delete media.")
    
    media = db.query(models.Media).filter(models.Media.id == media_id).first()
    if not media:
        raise HTTPException(status_code=404, detail="Media not found.")
    
    db.query(models.Like).filter(models.Like.media_id == media_id).delete()
    db.query(models.Favorite).filter(models.Favorite.media_id == media_id).delete()
    db.query(models.Comment).filter(models.Comment.media_id == media_id).delete()
    db.delete(media)
    db.commit()
    
    return {"message": "Media deleted successfully."}

# ---------------------------------------------------------------------------
# AI CAPTION GENERATOR (Bonus Feature)
# ---------------------------------------------------------------------------
from transformers import pipeline as hf_pipeline

print("Warming up HuggingFace GPT model for captions...")
try:
    caption_generator = hf_pipeline("text-generation", model="distilgpt2")
except Exception as e:
    print(f"Failed to load AI Model: {e}")
    caption_generator = None

@app.get("/media/{media_id}/caption/", tags=["AI"])
def get_ai_caption(
    media_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Generates an Instagram-style caption using HuggingFace GPT model."""
    media = db.query(models.Media).filter(models.Media.id == media_id).first()
    if not media:
        raise HTTPException(status_code=404, detail="Media not found.")

    tags = json.loads(media.ai_tags) if media.ai_tags else []
    if not tags:
        return {"caption": "Making incredible memories! ✨📸 #Event"}

    if caption_generator is None:
         return {"caption": "Incredible moments! ✨📸 " + " ".join([f"#{t.replace(' ', '')}" for t in tags[:3]])}

    prompt = f"Wow! The {tags[0]} is looking great. It looks very "
    try:
        output = caption_generator(
            prompt,
            max_new_tokens=10,
            num_return_sequences=1,
            pad_token_id=50256,
            temperature=0.7,
            do_sample=True,
        )[0]["generated_text"]

        clean_text = output.split("\n")[0].strip()
        if len(clean_text) > 120:
            clean_text = f"Amazing moments captured! ✨"

        hashtags = " ".join([f"#{t.replace(' ', '')}" for t in tags[:3]])
        return {"caption": f"{clean_text} 📸 {hashtags}"}

    except Exception:
        hashtags = " ".join([f"#{t.replace(' ', '')}" for t in tags[:3]])
        return {"caption": f"Incredible moments! ✨📸 {hashtags}"}