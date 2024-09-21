# config.py

import os

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'your_default_secret_key')  # Replace with a strong secret key
    GOOGLE_OAUTH_CLIENT_ID = os.getenv('GOOGLE_OAUTH_CLIENT_ID')
    GOOGLE_OAUTH_CLIENT_SECRET = os.getenv('GOOGLE_OAUTH_CLIENT_SECRET')
