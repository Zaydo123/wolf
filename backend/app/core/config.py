import os
from dotenv import load_dotenv
from pathlib import Path

# Load .env file
env_path = Path(__file__).parents[2] / '.env'
load_dotenv(dotenv_path=env_path)

# Supabase settings
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY')

# Twilio settings
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER')

# Google Gemini settings
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')

# ElevenLabs settings
ELEVENLABS_API_KEY = os.getenv('ELEVENLABS_API_KEY')
ELEVENLABS_VOICE_ID = os.getenv('ELEVENLABS_VOICE_ID', 'dY9fWBb7TNkZB7UPeFK1')  # Default voice (Matthew)
ELEVENLABS_MODEL = os.getenv('ELEVENLABS_MODEL', 'eleven_multilingual_v2')  # Default model

# Application settings
BACKEND_URL = os.getenv('BACKEND_URL', 'http://localhost:8000')
FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:3000')

# Broker personality settings
BROKER_PERSONALITY = os.getenv('BROKER_PERSONALITY', 'retro_new_yorker')  # Default personality 