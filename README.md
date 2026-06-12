# Event & Media Management Platform (EMP)

A full-stack, AI-powered web application designed to solve fragmented digital media storage in student clubs and professional organizations. EMP centralizes media, automates AI-driven tagging and captioning, and provides facial recognition to personalize photo discovery.

---

## 🚀 Key Features

### 🤖 AI Image Intelligence

* Automated image captioning using BLIP.
* Facial recognition powered by DeepFace (ArcFace).
* Automatic metadata generation for uploaded media.

### 🔍 Smart Discovery

* Users can upload a selfie.
* The system automatically finds and displays all event photos containing that user.

### ⚡ Real-Time Interaction

* WebSocket-powered notifications.
* Instant updates for likes, comments, and facial tags.

### 🔐 Role-Based Access Control

Four-tier permission system:

* Admin
* Photographer
* Club Member
* Viewer

### 🖼 Automatic Watermarking

* Dynamic watermark generation on media downloads.
* Protects event and organization branding.

### ☁️ Cloud Integration

* Secure media storage and streaming using AWS S3.
* Scalable architecture for large media collections.

---

## 🛠 Technology Stack

### Backend

* FastAPI
* Uvicorn
* SQLAlchemy (SQLite)
* Pydantic

### Frontend

* HTML5
* CSS3
* Vanilla JavaScript

### AI / Machine Learning

* PyTorch
* BLIP
* DeepFace (ArcFace)

### Cloud Storage

* AWS S3
* Boto3

---

## 💻 How to Run in VS Code

### 1. Prerequisites

Make sure the following are installed:

* VS Code
* Python 3.10+
* AWS Account with an S3 bucket configured

---

### 2. Project Setup

Clone the repository and open the project folder in VS Code.

```bash
git clone <your-repository-url>
cd EMP
```

---

### 3. Configure Environment Variables

Create a `.env` file inside the `event-platform-backend/` directory.

```env
JWT_SECRET_KEY=your_secure_random_string
ADMIN_SECRET_KEY=EMP-ADMIN-2026

AWS_ACCESS_KEY_ID=your_aws_key
AWS_SECRET_ACCESS_KEY=your_aws_secret
AWS_BUCKET_NAME=your_bucket_name
AWS_REGION=your_aws_region
```

---

### 4. Run the Backend

Open a terminal in VS Code and execute:

```bash
cd event-platform-backend

pip install -r requirements.txt

uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

> **Note:** During the first startup, the AI models (BLIP and ArcFace) will be downloaded automatically (~1.2 GB). This may take 5–10 minutes depending on your internet connection.

Backend will be available at:

```text
http://localhost:8000
```

---

### 5. Run the Frontend

Open a second terminal and execute:

```bash
cd event-platform-frontend

python -m http.server 5500
```

Frontend will be available at:

```text
http://localhost:5500
```

---

### 6. Access the Platform

#### User Portal

```text
http://localhost:5500/login.html
```

Steps:

1. Register a new account.
2. Log in.
3. Create or join events.
4. Upload and discover media.

#### API Documentation

Swagger UI:

```text
http://localhost:8000/docs
```

---

## 📂 Project Structure

```text
EMP/
│
├── event-platform-backend/
│   ├── main.py              # FastAPI Entry Point
│   ├── models.py            # SQLAlchemy Database Models
│   ├── schemas.py           # Pydantic Schemas
│   ├── ai_utils.py          # BLIP Captioning & Face Recognition Logic
│   └── s3_utils.py          # AWS S3 Storage Utilities
│
└── event-platform-frontend/
    ├── index.html           # Event Dashboard
    ├── event.html           # Media Gallery
    └── profile.html         # Selfie Match Profile
```

---

## 🔥 Core Functionalities

* Event creation and management
* Media upload and organization
* AI-powered image captioning
* Facial recognition-based photo search
* Real-time notifications
* Dynamic watermarking
* Role-based access control
* AWS S3 cloud storage integration

---

## 📈 Future Enhancements

* Multi-club collaboration support
* Advanced analytics dashboard
* Video tagging and recognition
* Mobile application support
* Social media sharing integration
* Event recommendation engine

---

## 📜 License

This project is developed for educational and portfolio purposes. Feel free to modify and extend it according to your requirements.
