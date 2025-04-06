import logging
import base64
import asyncio
import json
from typing import Optional, Dict, Any

from fastapi import WebSocket, WebSocketDisconnect

# Try both import approaches
try:
    # Absolute imports (when running from backend/)
    from app.core.config import ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID, ELEVENLABS_MODEL
    from app.services.elevenlabs_service import ElevenLabsService
except ImportError:
    # Relative imports (when running from app/)
    from ..core.config import ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID, ELEVENLABS_MODEL
    from ..services.elevenlabs_service import ElevenLabsService

logger = logging.getLogger(__name__)

class ElevenLabsTwilioService:
    """
    Service for handling real-time TTS using ElevenLabs through Twilio Media Streams
    """
    def __init__(self):
        self.elevenlabs = ElevenLabsService()
        self.active_calls = {}
        # Note: ElevenLabs supports "pcm_22050", "pcm_16000", "ulaw_8000", "mulaw_8000" for Twilio
        self.output_format = "mulaw_8000"  # Use mu-law encoding for Twilio
        logger.info(f"ElevenLabs Twilio media stream service initialized with output format: {self.output_format}")
    
    async def handle_websocket(self, websocket: WebSocket, call_id: str = None):
        """
        Handle a WebSocket connection from Twilio's Media Streams API
        """
        await websocket.accept()
        logger.info(f"Websocket connection accepted for call {call_id}")
        
        try:
            while True:
                # Receive message from Twilio
                message = await websocket.receive_text()
                logger.info(f"Received WebSocket message: {message}")
                data = json.loads(message)
                
                # Handle the different event types
                event = data.get('event')
                
                if event == 'start':
                    logger.info(f"Call started: {data}")
                    # Handle different possible formats for start event
                    stream_sid = None
                    if 'start' in data and isinstance(data['start'], dict):
                        stream_sid = data['start'].get('streamSid')
                    elif 'streamSid' in data:
                        stream_sid = data['streamSid']
                        
                    if not stream_sid:
                        logger.error("No stream SID found in start event")
                        continue
                        
                    call_sid = data.get('start', {}).get('callSid') or data.get('callSid')
                    self.active_calls[stream_sid] = {
                        'stream_sid': stream_sid,
                        'call_sid': call_sid,
                        'websocket': websocket
                    }
                    
                    # Get user data and market data for the greeting
                    try:
                        # Import trading service here to avoid circular imports
                        from app.services.trading_service import TradingService
                        from app.services.gemini_service import GeminiService
                        
                        trading_service = TradingService()
                        gemini_service = GeminiService()
                        
                        # Get user ID from call ID if provided
                        user_id = call_id if call_id else 'ab15bf54-8b43-4891-a5ad-65c1c8fd54fe'
                        
                        # Get data asynchronously
                        market_data = await trading_service.get_market_summary()
                        user_data = await trading_service.get_user_summary(user_id)
                        
                        # Generate broker greeting
                        broker_intro = await gemini_service.generate_broker_call_intro(user_data, market_data)
                        
                        # Play the greeting
                        await self.play_text(stream_sid, broker_intro)
                    except Exception as e:
                        logger.error(f"Error sending welcome message: {e}")
                        # Send a fallback message
                        await self.play_text(stream_sid, "Hello! I'm your AI stock broker. How can I help you today?")
                
                elif event == 'media':
                    # Handle incoming audio from Twilio if needed
                    # This would be used if we wanted to process user speech
                    pass
                
                elif event == 'stop':
                    logger.info(f"Call stopped: {data}")
                    stream_sid = data.get('streamSid')
                    if stream_sid in self.active_calls:
                        del self.active_calls[stream_sid]
                    break
                    
        except WebSocketDisconnect:
            logger.info(f"Websocket disconnected for call {call_id}")
        except Exception as e:
            logger.error(f"Error in websocket connection: {e}")
        finally:
            # Clean up the connection
            for stream_sid, call_data in list(self.active_calls.items()):
                if call_data.get('websocket') == websocket:
                    del self.active_calls[stream_sid]
    
    async def play_text(self, stream_sid: str, text: str) -> bool:
        """
        Sends text to be spoken via ElevenLabs TTS to a specific stream
        
        Parameters:
            stream_sid (str): The Twilio stream SID to send audio to
            text (str): The text to convert to speech
            
        Returns:
            bool: True if successful, False otherwise
        """
        if stream_sid not in self.active_calls:
            logger.error(f"No active call found for stream SID: {stream_sid}")
            return False
            
        try:
            # Get the websocket connection for this stream
            websocket = self.active_calls[stream_sid]['websocket']
            
            # Generate speech with ElevenLabs in the correct format for Twilio
            logger.info(f"Generating ElevenLabs speech for text: '{text[:50]}...' with format: {self.output_format}")
            audio_data = await self.elevenlabs.text_to_speech(text, output_format=self.output_format)
            if not audio_data:
                logger.error("Failed to generate speech with ElevenLabs")
                return False
                
            # Convert to base64
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            
            # Send audio to Twilio via the websocket
            await websocket.send_text(json.dumps({
                'streamSid': stream_sid,
                'event': 'media',
                'media': {
                    'payload': audio_base64
                }
            }))
            
            logger.info(f"Sent audio to stream {stream_sid} successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error sending audio to stream {stream_sid}: {e}")
            return False
    
    def get_connection_twiml(self, websocket_url: str) -> str:
        """
        Generate TwiML to establish a Media Streams connection
        
        Parameters:
            websocket_url (str): The WebSocket URL for Twilio to connect to
            
        Returns:
            str: TwiML XML string
        """
        return f"""
        <?xml version="1.0" encoding="UTF-8"?>
        <Response>
            <Connect>
                <Stream url="{websocket_url}" track="both_tracks">
                    <Parameter name="format" value="mulaw"/>
                </Stream>
            </Connect>
            <Pause length="60"/>
        </Response>
        """