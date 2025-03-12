# Personalized News Digest API

This project is a **FastAPI-based Personalized News Digest API** that allows users to sign up, select their preferred news topics, and receive daily news updates. It uses **SQLiteCloud** for database storage, **Redis** for caching and OTP management, and integrates with **NewsData.io API** for fetching news articles.

## 🚀 Features

- **User Authentication**: OTP-based signup & secure login using bcrypt.
- **Preference Management**: Users can select news topics of interest.
- **News Fetching**: Fetches news articles using the NewsData.io API.
- **Daily Digest**: Stores and retrieves user-specific news digests.
- **Session Management**: Uses Redis to manage user sessions.
- **SMTP Email Support**: Sends OTP for verification.

## 🛠 Tech Stack

- **Backend**: FastAPI, SQLiteCloud, Redis
- **Database**: SQLiteCloud
- **Caching**: Redis
- **API Integration**: NewsData.io API
- **Authentication**: Bcrypt, OTP-based signup

## 📌 Setup Instructions

1. **Clone the Repository**

   ```sh
   git clone https://github.com/your-username/personalized-news-digest.git
   cd personalized-news-digest
   ```

2. **Install Dependencies**

   ```sh
   pip install -r requirements.txt
   ```

3. **Set Up Redis (For Caching & OTPs)**

   - Install Redis:
     ```sh
     sudo apt install redis
     ```
   - Start Redis:
     ```sh
     redis-server
     ```

4. **Run the FastAPI Server**

   ```sh
   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

5. **API Endpoints**

   - `POST /signup/request-otp` - Request OTP for signup.
   - `POST /signup/verify-otp` - Verify OTP and create an account.
   - `POST /login` - Login and get session ID.
   - `POST /logout` - Logout user.
   - `POST /update-preferences` - Update user's news preferences.
   - `GET /fetch-news` - Fetch personalized news.
   - `GET /daily-digest` - View stored news digest.

## 🔑 Environment Variables

Create a `.env` file and set:

```
SMTP_EMAIL="your-email@gmail.com"
SMTP_PASSWORD="your-email-password"
NEWS_API_KEY="your-newsdata.io-api-key"
REDIS_HOST="localhost"
REDIS_PORT=6379
SQLITECLOUD_URL="your-sqlitecloud-url"
```


---

Made with ❤️ by [Labdh Purohit](https://github.com/labdhpurohit)
