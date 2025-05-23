from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Gather, Play
import logging
import os
import uuid

# Try both import approaches
try:
    # Absolute imports (when running from backend/)
    from app.core.config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER, BACKEND_URL
    from app.services.elevenlabs_service import ElevenLabsService
except ImportError:
    # Relative imports (when running from app/)
    from ..core.config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER, BACKEND_URL
    from ..services.elevenlabs_service import ElevenLabsService

# Check if we should use mock mode (for development without a Twilio account)
MOCK_TWILIO = os.getenv('MOCK_TWILIO', 'false').lower() == 'true'
# Check if we should use ElevenLabs for TTS
USE_ELEVENLABS = os.getenv('USE_ELEVENLABS', 'true').lower() == 'true'

logger = logging.getLogger(__name__)

class TwilioService:
    def __init__(self):
        # Initialize ElevenLabs service if enabled
        self.elevenlabs = ElevenLabsService() if USE_ELEVENLABS else None
        
        # Check if we should use mock mode
        if MOCK_TWILIO:
            logger.info("Using Twilio in mock mode - no actual calls will be made")
            self.client = None
            self.from_number = "+15555555555"  # Fake number
            self.enabled = True
            self.mock_mode = True
            return
        
        # Check if Twilio credentials are set
        if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN or not TWILIO_PHONE_NUMBER:
            logger.warning("Twilio credentials not fully configured. Some features will be disabled.")
            self.client = None
            self.from_number = None
            self.enabled = False
            self.mock_mode = False
        else:
            try:
                self.client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
                self.from_number = TWILIO_PHONE_NUMBER
                self.enabled = True
                self.mock_mode = False
                logger.info("Twilio service initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Twilio client: {e}")
                self.client = None
                self.from_number = None
                self.enabled = False
                self.mock_mode = False
    
    def initiate_call(self, to_number, user_id, connect_url=None, status_url=None):
        """
        Initiate a call to the user.
        
        Parameters:
            to_number (str): The user's phone number
            user_id (str): The user's ID for tracking the call in the system
            connect_url (str): Optional URL for Twilio to call when the call connects
            status_url (str): Optional URL for Twilio to call for status updates
            
        Returns:
            dict: Call status information
        """
        # Check if Twilio is enabled
        if not self.enabled:
            logger.warning("Cannot initiate call: Twilio service is not enabled")
            return {
                "status": "error",
                "error": "Twilio service is not properly configured",
                "user_id": user_id
            }
            
        # Validate phone number format
        if not to_number or not to_number.startswith('+'):
            logger.warning(f"Invalid phone number format: {to_number}")
            return {
                "status": "error",
                "error": "Phone number must be in E.164 format (e.g., +1234567890)",
                "user_id": user_id
            }
        
        # If in mock mode, return a successful mock response
        if self.mock_mode:
            mock_call_sid = f"MOCK_CALL_{uuid.uuid4()}"
            logger.info(f"MOCK MODE: Simulating call to {to_number}, SID: {mock_call_sid}")
            return {
                "status": "initiated",
                "call_sid": mock_call_sid,
                "user_id": user_id,
                "mock": True
            }
            
        try:
            # Use provided callback URLs or fall back to BACKEND_URL
            if not connect_url:
                connect_url = f"{BACKEND_URL}/api/calls/connect/{user_id}"
            if not status_url:
                status_url = f"{BACKEND_URL}/api/calls/status/{user_id}"
            
            logger.info(f"Using connect URL: {connect_url}")
            logger.info(f"Using status URL: {status_url}")
            
            call = self.client.calls.create(
                to=to_number,
                from_=self.from_number,
                url=connect_url,
                status_callback=status_url,
                status_callback_event=['initiated', 'ringing', 'answered', 'completed'],
                status_callback_method='POST',
                record=True,  # Enable call recording
                recording_status_callback=f"{status_url}/recording",  # Callback for recording status
                recording_status_callback_method='POST'
            )
            
            logger.info(f"Call initiated to {to_number}, SID: {call.sid}")
            return {
                "status": "initiated",
                "call_sid": call.sid,
                "user_id": user_id
            }
            
        except Exception as e:
            logger.error(f"Error initiating call: {e}")
            return {
                "status": "error",
                "error": str(e),
                "user_id": user_id
            }
    
    async def generate_welcome_twiml(self, broker_intro):
        """
        Generate TwiML for the welcome message and to gather user speech.
        Uses ElevenLabs for speech synthesis if enabled.
        
        Parameters:
            broker_intro (str): The broker's introduction script
            
        Returns:
            str: TwiML response as a string
        """
        response = VoiceResponse()
        
        # Add the broker's introduction
        # For now, always use Twilio's TTS since we have issues with the audio format
        response.say(broker_intro, voice='Polly.Matthew')
        
        # Gather the user's speech input 
        # Make sure we have the right URL path format
        backend_url = BACKEND_URL.rstrip('/')
        gather = Gather(
            input='speech',
            action=f"{backend_url}/api/calls/process_speech",
            method='POST',
            timeout=5,
            speechTimeout='auto',
            language='en-US'
        )
        
        # Add the prompt to gather
        prompt_text = "What would you like to do today?"
        gather.say(prompt_text, voice='Polly.Matthew')
        
        response.append(gather)
        
        # If the user doesn't say anything, prompt again
        backend_url = BACKEND_URL.rstrip('/')
        response.redirect(f"{backend_url}/api/calls/retry")
        
        return str(response)
    
    async def generate_response_twiml(self, broker_response, gather_again=True):
        """
        Generate TwiML for the broker's response after processing a trade.
        Uses ElevenLabs for speech synthesis if enabled.
        
        Parameters:
            broker_response (str): The broker's response script
            gather_again (bool): Whether to gather more speech after the response
            
        Returns:
            str: TwiML response as a string
        """
        response = VoiceResponse()
        
        # Add the broker's response
        # For now, always use Twilio's TTS since we have issues with the audio format
        response.say(broker_response, voice='Polly.Matthew')
        
        if gather_again:
            # Gather more speech if needed
            # Make sure we have the right URL path format
            backend_url = BACKEND_URL.rstrip('/')
            gather = Gather(
                input='speech',
                action=f"{backend_url}/api/calls/process_speech",
                method='POST',
                timeout=5,
                speechTimeout='auto',
                language='en-US'
            )
            
            # Add the prompt to gather
            prompt_text = "Anything else you'd like to do?"
            gather.say(prompt_text, voice='Polly.Matthew')
            
            response.append(gather)
            
            # If the user doesn't say anything, prompt again
            backend_url = BACKEND_URL.rstrip('/')
            response.redirect(f"{backend_url}/api/calls/retry")
        else:
            # End the call with a goodbye
            goodbye_text = "Thanks for trading with us today. Wolf out!"
            response.say(goodbye_text, voice='Polly.Matthew')
            response.hangup()
        
        return str(response)