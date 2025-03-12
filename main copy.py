import uuid
import sqlitecloud
import redis
import bcrypt
import smtplib
import random
import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import List

# 🚀 Initialize FastAPI App
app = FastAPI()

# ✅ Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

AVAILABLE_TOPICS = ["sports", "technology", "health", "business", "entertainment"]

# 📌 SQLiteCloud Database Connection
sqlite_db = sqlitecloud.connect("YOUR_DATABASE_API_KEY")

# ✅ **Create Tables**
sqlite_db.execute("""
CREATE TABLE IF NOT EXISTS users (
    email TEXT PRIMARY KEY,
    password TEXT NOT NULL
);
""")

sqlite_db.execute("""
CREATE TABLE IF NOT EXISTS preferences (
    email TEXT PRIMARY KEY,
    topics TEXT,
    FOREIGN KEY (email) REFERENCES users(email)
);
""")

sqlite_db.execute("""
CREATE TABLE IF NOT EXISTS daily_digest (
    email TEXT PRIMARY KEY,
    digest TEXT,
    FOREIGN KEY (email) REFERENCES users(email)
);
""")

# 📌 Redis for Caching News & OTP
redis_client = redis.Redis(host="localhost", port=6379, decode_responses=True)

# 📌 Session Expiry Time (Seconds)
SESSION_EXPIRE_TIME = 86400  

# 📌 News API
NEWS_API_KEY = "NEWDATA_API_KEY"

# 📌 SMTP Configuration
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_EMAIL = "your_email@gmail.com"
SMTP_PASSWORD = "your_app_password"

# 📌 User Models
class OTPRequest(BaseModel):
    email: EmailStr

class OTPVerify(BaseModel):
    email: EmailStr
    otp: str
    password: str  # User sets password after OTP verification

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class PreferencesUpdate(BaseModel):
    session_id: str
    topics: List[str] = AVAILABLE_TOPICS

# ✅ **Send OTP via Email**
def send_otp(email):
    otp = str(random.randint(100000, 999999))
    redis_client.setex(f"otp_{email}", 300, otp)  # OTP expires in 5 minutes

    message = f"Subject: Your OTP Code\n\nYour OTP is: {otp}"
    
    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_EMAIL, SMTP_PASSWORD)
        server.sendmail(SMTP_EMAIL, email, message)
        server.quit()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error sending email: {str(e)}")

# ✅ **Request OTP for Signup**
@app.post("/signup/request-otp")
def signup_request_otp(data: OTPRequest):
    result = sqlite_db.execute("SELECT email FROM users WHERE email = ?", (data.email,))
    if result.fetchall():
        raise HTTPException(status_code=400, detail="User already exists")
    
    send_otp(data.email)
    return {"message": "OTP sent successfully"}

# ✅ **Signup Route with OTP Verification**
@app.post("/signup/verify-otp")
def signup_with_otp(data: OTPVerify):
    stored_otp = redis_client.get(f"otp_{data.email}")
    
    if not stored_otp or stored_otp != data.otp:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")
    
    redis_client.delete(f"otp_{data.email}")  # Remove OTP after verification

    hashed_password = bcrypt.hashpw(data.password.encode(), bcrypt.gensalt())
    sqlite_db.execute("INSERT INTO users (email, password) VALUES (?, ?)", (data.email, hashed_password.decode()))
    topics_str = ", ".join(AVAILABLE_TOPICS)
    sqlite_db.execute("INSERT INTO preferences (email, topics) VALUES (?, ?)", (data.email, topics_str))
    return {"message": "User registered successfully"}

# ✅ **Login Route**
@app.post("/login")
def login(user: UserLogin):
    result = sqlite_db.execute("SELECT password FROM users WHERE email = ?", (user.email,))
    db_user = result.fetchone()
    
    if not db_user or not bcrypt.checkpw(user.password.encode(), db_user[0].encode()):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    session_id = str(uuid.uuid4())
    redis_client.setex(session_id, SESSION_EXPIRE_TIME, user.email)
    
    return {"message": "Login successful", "session_id": session_id}

# ✅ **Logout Route**
@app.post("/logout")
def logout(session_id: str):
    if not session_id or not redis_client.get(session_id):
        raise HTTPException(status_code=401, detail="Invalid session or already logged out")

    redis_client.delete(session_id)
    return {"message": "Logged out successfully"}

# ✅ **Validate Session**
def get_user_from_session(session_id: str):
    email = redis_client.get(session_id)
    if not email:
        raise HTTPException(status_code=401, detail="Invalid session ID")
    return email

# ✅ **Update Preferences**
@app.post("/update-preferences")
def update_preferences(request_data: PreferencesUpdate):
    user = get_user_from_session(request_data.session_id)

    # Check if user already has preferences
    result = sqlite_db.execute("SELECT topics FROM preferences WHERE email = ?", (user,))
    existing_record = result.fetchone()

    topics_str = ", ".join(request_data.topics)

    if existing_record:
        sqlite_db.execute("UPDATE preferences SET topics = ? WHERE email = ?", (topics_str, user))
    else:
        sqlite_db.execute("INSERT INTO preferences (email, topics) VALUES (?, ?)", (user, topics_str))

    fetch_news(request_data.session_id)  
    return {"message": "Preferences updated successfully"}

# ✅ **Fetch News (Using NewsData.io API)**
@app.get("/fetch-news")
def fetch_news(session_id: str):
    user = get_user_from_session(session_id)

    result = sqlite_db.execute("SELECT topics FROM preferences WHERE email = ?", (user,))
    user_data = result.fetchone()

    if not user_data:
        raise HTTPException(status_code=404, detail="No preferences found")

    topics = user_data[0].split(", ")
    news_list = []

    for topic in topics:
        news_response = requests.get(f"https://newsdata.io/api/1/news?apikey={NEWS_API_KEY}&q={topic}&language=en").json()
        
        if "results" in news_response:
            for article in news_response["results"][:3]:  
                news_list.append({
                    "title": article.get("title", "No title"),
                    "description": article.get("description", "No description available"),
                    "image_url": article.get("image_url", ""),
                    "url": article.get("link", "#")
                })

    digest = str({"news": news_list})  # Convert to string

    # Store in Database
    result = sqlite_db.execute("SELECT digest FROM daily_digest WHERE email = ?", (user,))
    existing_record = result.fetchone()

    if existing_record:
        sqlite_db.execute("UPDATE daily_digest SET digest = ? WHERE email = ?", (digest, user))
    else:
        sqlite_db.execute("INSERT INTO daily_digest (email, digest) VALUES (?, ?)", (user, digest))

    return eval(digest)  # Convert back to dict for response

# ✅ **View Daily Digest**
@app.get("/daily-digest")
def view_daily_digest(session_id: str):
    user = get_user_from_session(session_id)

    result = sqlite_db.execute("SELECT digest FROM daily_digest WHERE email = ?", (user,))
    user_data = result.fetchone()
    
    if not user_data:
        raise HTTPException(status_code=404, detail="No digest found")

    return eval(user_data[0])  # Convert stored string to dict

# ✅ **Run the Server**
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
