import logging
import os
import aiohttp
import asyncio
import base64
from typing import Optional

# Try both import approaches
try:
    # Absolute imports (when running from backend/)
    from app.core.config import ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID, ELEVENLABS_MODEL
except ImportError:
    # Relative imports (when running from app/)
    from ..core.config import ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID, ELEVENLABS_MODEL

logger = logging.getLogger(__name__)

class ElevenLabsService:
    def __init__(self):
        self.api_key = ELEVENLABS_API_KEY
        self.voice_id = ELEVENLABS_VOICE_ID
        self.model = ELEVENLABS_MODEL
        self.base_url = "https://api.elevenlabs.io/v1"
        self.enabled = bool(self.api_key)
        
        if not self.enabled:
            logger.warning("ElevenLabs API key not configured. Voice synthesis will use fallback.")
        else:
            logger.info(f"ElevenLabs service initialized successfully with voice ID: {self.voice_id}")
            # Schedule a task to list available voices
            loop = asyncio.get_event_loop()
            loop.create_task(self._check_voices_on_init())
    
    async def text_to_speech(self, text: str, output_format: str = None) -> Optional[bytes]:
        """
        Convert text to speech using ElevenLabs API
        
        Parameters:
            text (str): Text to convert to speech
            output_format (str): Optional format for the audio output (mp3, pcm_mulaw, etc.)
            
        Returns:
            bytes: Audio data if successful, None if failed
        """
        if not self.enabled:
            logger.warning("ElevenLabs service is not enabled. Cannot generate speech.")
            return None
            
        try:
            # First, verify the voice is available
            voices_url = f"{self.base_url}/voices"
            
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "xi-api-key": self.api_key
            }
            
            # Log the request we're about to make
            logger.info(f"Using ElevenLabs voice ID: {self.voice_id}")
            
            url = f"{self.base_url}/text-to-speech/{self.voice_id}"
            
            # Set correct Accept header based on output format
            content_type = "audio/mpeg"
            if output_format == "pcm_mulaw":
                content_type = "audio/mulaw"
            elif output_format == "pcm_16000":
                content_type = "audio/pcm"
                
            headers = {
                "Accept": content_type,
                "Content-Type": "application/json",
                "xi-api-key": self.api_key
            }
            
            data = {
                "text": text,
                "model_id": self.model,
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.75
                }
            }
            
            # Add output format if specified
            if output_format:
                data["output_format"] = output_format
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data, headers=headers) as response:
                    if response.status == 200:
                        logger.info(f"ElevenLabs speech generated successfully (format: {output_format or 'default'})")
                        return await response.read()
                    else:
                        error_text = await response.text()
                        logger.error(f"ElevenLabs API error: {response.status} - {error_text}")
                        
                        # Get available voices for debugging
                        try:
                            async with session.get(f"{self.base_url}/voices", headers=headers) as voices_response:
                                if voices_response.status == 200:
                                    voices_data = await voices_response.json()
                                    available_voices = [f"{v.get('name', 'Unknown')} ({v.get('voice_id', 'Unknown')})" for v in voices_data.get('voices', [])]
                                    logger.info(f"Available ElevenLabs voices: {', '.join(available_voices)}")
                        except Exception as e:
                            logger.error(f"Failed to fetch available voices: {e}")
                            
                        return None
                        
        except Exception as e:
            logger.error(f"Error generating speech with ElevenLabs: {e}")
            return None
    
    async def text_to_speech_base64(self, text: str, output_format: str = None) -> Optional[str]:
        """
        Convert text to speech and return as base64 encoded string for use with Twilio
        
        Parameters:
            text (str): Text to convert to speech
            output_format (str): Optional format for the audio output (mp3, pcm_mulaw, etc.)
            
        Returns:
            str: Base64 encoded audio data if successful, None if failed
        """
        audio_data = await self.text_to_speech(text, output_format)
        if audio_data:
            return base64.b64encode(audio_data).decode('utf-8')
        return None
        
    async def list_available_voices(self) -> list:
        """
        List all available voices for the current API key
        
        Returns:
            list: List of voice dictionaries with name, ID and whether they're free
        """
        if not self.enabled:
            logger.warning("ElevenLabs service is not enabled. Cannot list voices.")
            return []
            
        try:
            url = f"{self.base_url}/voices"
            
            headers = {
                "Accept": "application/json",
                "xi-api-key": self.api_key
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        voices = data.get('voices', [])
                        logger.info(f"Found {len(voices)} voices on ElevenLabs account")
                        for voice in voices:
                            logger.info(f"Voice: {voice.get('name')} (ID: {voice.get('voice_id')}, Category: {voice.get('category', 'Unknown')})")
                        return voices
                    else:
                        error_text = await response.text()
                        logger.error(f"ElevenLabs API error listing voices: {response.status} - {error_text}")
                        return []
                        
        except Exception as e:
            logger.error(f"Error listing ElevenLabs voices: {e}")
            return []
            
    async def _check_voices_on_init(self):
        """
        Check available voices at initialization and verify if the configured voice is available
        """
        try:
            voices = await self.list_available_voices()
            # Check if the configured voice ID is in the available voices
            voice_ids = [v.get('voice_id') for v in voices]
            if self.voice_id in voice_ids:
                # Find the name of this voice
                for voice in voices:
                    if voice.get('voice_id') == self.voice_id:
                        logger.info(f"Using ElevenLabs voice: {voice.get('name')} (ID: {self.voice_id})")
                        break
            else:
                logger.warning(f"Configured voice ID {self.voice_id} not found in available voices. Using fallback voice.")
                # Find the first available voice that's free (cloning or premade)
                default_voice = None
                for voice in voices:
                    category = voice.get('category', '')
                    if category in ['premade', 'cloned']:
                        default_voice = voice
                        break
                        
                if default_voice:
                    self.voice_id = default_voice.get('voice_id')
                    logger.info(f"Using default voice: {default_voice.get('name')} (ID: {self.voice_id})")
        except Exception as e:
            logger.error(f"Error checking available voices: {e}")
            # Continue with the configured voice, errors will be handled in text_to_speech