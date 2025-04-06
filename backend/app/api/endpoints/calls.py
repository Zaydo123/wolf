from fastapi import APIRouter, HTTPException, WebSocket, Depends, Request, Body
import logging
from typing import Optional, Dict, Any
from fastapi.responses import Response, JSONResponse
import json
import os
import sys
from twilio.twiml.voice_response import VoiceResponse, Gather
import datetime
import uuid
from pydantic import BaseModel

# Import the central path setup module
from app.core.imports import APP_DIR, BACKEND_DIR

# Import services and config
from app.services.twilio_service import TwilioService
from app.services.gemini_service import GeminiService
from app.services.trading_service import TradingService
from app.services.elevenlabs_service import ElevenLabsService
from app.services.elevenlabs_twilio_service import ElevenLabsTwilioService
from app.db.supabase import get_supabase_client
from app.api.endpoints.users import get_user
from app.core.config import BACKEND_URL

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/calls", tags=["calls"])

# Initialize services
twilio_service = TwilioService()
gemini_service = GeminiService()
trading_service = TradingService()
elevenlabs_service = ElevenLabsService()
elevenlabs_twilio_service = ElevenLabsTwilioService()

def format_phone_number(phone_number):
    """
    Format a phone number to E.164 format as required by Twilio.
    E.164 format: +[country code][phone number without leading 0]
    e.g., +14155552671
    
    Args:
        phone_number (str): The phone number to format
        
    Returns:
        str: The E.164 formatted phone number
    """
    if not phone_number:
        return None
        
    # Remove any non-digit characters
    digits_only = ''.join(filter(str.isdigit, phone_number))
    
    # If the number already has the international format with +, return it
    if phone_number.startswith('+'):
        return phone_number
        
    # If US/Canada number (10 digits), add +1
    if len(digits_only) == 10:
        return f"+1{digits_only}"
        
    # If it includes country code (>10 digits), add +
    if len(digits_only) > 10:
        return f"+{digits_only}"
        
    # Otherwise, return as is with + prefix (may not work with Twilio)
    logger.warning(f"Phone number {phone_number} may not be in a valid format for Twilio")
    return f"+{digits_only}"

class CallScheduleRequest(BaseModel):
    user_id: str
    phone_number: str
    call_time: str
    call_type: str = "market_open"  # market_open, mid_day, market_close

@router.post("/schedule")
async def schedule_call(schedule_request: CallScheduleRequest):
    """
    Schedule a call to a user at a specific time.
    This would typically be implemented with a task queue or cron job.
    For the hackathon, we'll just return the scheduling info.
    """
    try:
        supabase = get_supabase_client()
        
        # Store the call schedule in Supabase
        schedule = {
            'user_id': schedule_request.user_id,
            'phone_number': schedule_request.phone_number,
            'call_time': schedule_request.call_time,
            'call_type': schedule_request.call_type,
            'status': 'scheduled'
        }
        
        result = supabase.table('call_schedules').insert(schedule).execute()
        
        return {
            "status": "scheduled",
            "schedule_id": result.data[0]['id'] if result.data else None,
            "message": f"Call scheduled for {schedule_request.call_time}"
        }
    except Exception as e:
        logger.error(f"Error scheduling call: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/schedules/{user_id}")
async def get_call_schedules(user_id: str):
    """
    Get all scheduled calls for a user.
    
    Parameters:
        user_id: User ID
    """
    try:
        supabase = get_supabase_client()
        
        # Get the user's call schedules
        schedules = supabase.table('call_schedules').select('*')\
            .eq('user_id', user_id)\
            .order('call_time')\
            .execute()
        
        return {"schedules": schedules.data if schedules.data else []}
    except Exception as e:
        logger.error(f"Error getting call schedules: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/initiate/{user_id}")
async def initiate_call(
    request: Request,
    user_id: str
):
    """
    Initiate a call to the user's phone number.
    """
    try:
        logger.info(f"Initiating call for user_id: {user_id}")
        # Get the user's phone number using the user_id from path
        user = await get_user(user_id)
        if not user or not user.phone_number:
            raise HTTPException(
                status_code=400,
                detail="User not found or phone number not set"
            )
        
        # Format the phone number to E.164 format
        phone_number = user.phone_number
        if not phone_number.startswith('+'):
            phone_number = f"+{phone_number}"
        
        # Use PUBLIC_BACKEND_URL env var for callbacks, fallback to request base_url
        public_callback_base = os.getenv('PUBLIC_BACKEND_URL')
        if not public_callback_base:
            logger.warning("PUBLIC_BACKEND_URL environment variable not set. Falling back to request base_url for Twilio callbacks. This might not work if the backend is not publicly accessible.")
            public_callback_base = str(request.base_url)
            
        # Ensure base URL doesn't have a trailing slash
        if public_callback_base.endswith('/'):
            public_callback_base = public_callback_base[:-1]
        
        # Use the regular connect endpoint
        connect_url = f"{public_callback_base}/api/calls/connect/{user_id}"
        status_url = f"{public_callback_base}/api/calls/status/{user_id}"
        
        logger.info(f"Using connect URL: {connect_url}")
        logger.info(f"Using status URL: {status_url}")
        
        # Initialize Twilio service
        twilio_service = TwilioService()
        
        # Initialize Supabase client with service role
        supabase = get_supabase_client(use_service_role=True)
        
        try:
            # Initiate the call
            result = twilio_service.initiate_call(
                to_number=phone_number,
                user_id=user_id,
                connect_url=connect_url,
                status_url=status_url
            )
            
            if result["status"] == "error":
                # Create a failed call record
                call_data = {
                    "user_id": user_id,
                    "phone_number": phone_number,
                    "status": "failed",
                    "call_sid": None,  # No call SID for failed initiation
                    "started_at": datetime.datetime.utcnow().isoformat(),
                    "ended_at": datetime.datetime.utcnow().isoformat(),
                    "direction": "outbound",
                    "duration": 0
                }
                
                response = supabase.table("calls").insert(call_data).execute()
                if not response.data:
                    logger.error("Failed to create call record for failed initiation")
                
                raise HTTPException(
                    status_code=500,
                    detail=result["error"]
                )
            
            # Create a call record in the database
            call_data = {
                "user_id": user_id,
                "phone_number": phone_number,
                "status": "initiated", 
                "call_sid": result["call_sid"],
                "started_at": datetime.datetime.utcnow().isoformat(),
                "direction": "outbound"
            }
            
            response = supabase.table("calls").insert(call_data).execute()
            
            # Check for None data instead of error attribute
            if not response.data:
                logger.error("Error creating call record: No data returned")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to create call record"
                )
            
            return {
                "status": "success",
                "message": "Call initiated successfully",
                "call_sid": result["call_sid"]
            }
            
        except Exception as e:
            # Create a failed call record for any exception during initiation
            call_data = {
                "user_id": user_id,
                "phone_number": phone_number,
                "status": "failed",
                "call_sid": None,
                "started_at": datetime.datetime.utcnow().isoformat(),
                "ended_at": datetime.datetime.utcnow().isoformat(),
                "direction": "outbound",
                "duration": 0
            }
            
            try:
                response = supabase.table("calls").insert(call_data).execute()
                if not response.data:
                    logger.error("Failed to create call record for failed initiation")
            except Exception as db_error:
                logger.error(f"Database error creating failed call record: {db_error}")
            
            raise HTTPException(
                status_code=500,
                detail=str(e)
            )
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error initiating call: {e}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@router.post("/connect/{user_id}")
async def connect_call(user_id: str, request: Request):
    """
    Generate TwiML for the initial call connection.
    This endpoint is called by Twilio when the call connects.
    """
    try:
        # Get market data
        market_data = await trading_service.get_market_summary()
        if not market_data:
            raise HTTPException(status_code=500, detail="Failed to get market data")
        
        # Get user data
        user_data = await trading_service.get_user_summary(user_id)
        if not user_data:
            raise HTTPException(status_code=404, detail="User data not found")
        
        # Generate broker intro using Gemini
        broker_intro = await gemini_service.generate_broker_call_intro(user_data, market_data)
        if not broker_intro:
            raise HTTPException(status_code=500, detail="Failed to generate broker intro")
        
        # Generate TwiML response with the broker intro
        twiml = await twilio_service.generate_welcome_twiml(broker_intro)
        
        # Get the call SID from the request
        form_data = await request.form()
        call_sid = form_data.get('CallSid')
        
        # Log the broker's intro with service role client
        supabase = get_supabase_client(use_service_role=True)
        supabase.table('call_logs').insert({
            'user_id': user_id,
            'call_sid': call_sid,  # Use actual call SID
            'direction': 'outbound',
            'content': broker_intro,
            'timestamp': datetime.datetime.utcnow().isoformat()
        }).execute()
        
        return Response(content=twiml, media_type="application/xml")
    except Exception as e:
        logger.error(f"Error connecting call: {e}")
        raise HTTPException(status_code=500, detail=f"Error connecting call: {str(e)}")

@router.post("/process_speech", status_code=200)
@router.post("/api/calls/process_speech", status_code=200)  # Add an alias to handle both URL patterns
async def process_speech(request: Request):
    """
    Process the user's speech from a Twilio call.
    This endpoint is called by Twilio after speech is gathered.
    """
    try:
        # Parse the form data from Twilio
        form_data = await request.form()
        
        # Get the speech transcription
        transcription = form_data.get('SpeechResult')
        phone_number = form_data.get('From')  # This is the caller's phone number
        call_sid = form_data.get('CallSid')
        
        # Skip Twilio numbers (they start with +1888)
        if phone_number and phone_number.startswith('+1888'):
            logger.info(f"Skipping Twilio number: {phone_number}")
            # Get the actual user's phone number from the To field
            phone_number = form_data.get('To')
            if not phone_number:
                logger.error("No user phone number found in To field")
                response = VoiceResponse()
                response.say("Sorry, there was a problem identifying your account. Please try again later.", voice='Polly.Matthew')
                response.hangup()
                return Response(content=str(response), media_type="application/xml")
        
        # Look up the user by phone number instead of using it as ID
        supabase = get_supabase_client(use_service_role=True)
        
        # Find user by phone number - try multiple formats
        user_result = None
        if phone_number:
            # Try formatted phone number
            user_result = supabase.table('users').select('id').eq('phone_number', phone_number).execute()
            
            # If that fails, try with additional formatting variations
            if not user_result.data:
                # Try a version without the leading +
                if phone_number.startswith('+'):
                    user_result = supabase.table('users').select('id').eq('phone_number', phone_number[1:]).execute()
        
        # If we still couldn't find the user, return error
        if not user_result or not user_result.data:
            logger.error(f"Could not find user by phone number: {phone_number}")
            response = VoiceResponse()
            response.say("Sorry, I couldn't find your account. Please register on our website first.", voice='Polly.Matthew')
            response.hangup()
            return Response(content=str(response), media_type="application/xml")
            
        user_id = user_result.data[0]['id']
            
        logger.info(f"Processing speech for user: {user_id}, from phone: {phone_number}")
        
        if not transcription:
            # If no transcription, prompt user to speak again
            twiml = await twilio_service.generate_response_twiml(
                "I didn't catch that. Could you please repeat?", 
                gather_again=True
            )
            return Response(content=twiml, media_type="application/xml")
        
        # Log the user's speech with service role
        supabase.table('call_logs').insert({
            'user_id': user_id,
            'call_sid': call_sid,
            'direction': 'inbound',
            'content': transcription,
            'timestamp': datetime.datetime.utcnow().isoformat()
        }).execute()
        
        # STEP 1: Check if this is a price check query
        is_price_check, ticker = await gemini_service._check_for_price_query(transcription)
        
        # Get the full call transcript so far to provide context
        call_transcript = []
        if call_sid:
            previous_logs = supabase.table('call_logs').select('*')\
                .eq('call_sid', call_sid)\
                .order('timestamp')\
                .execute()
                
            if previous_logs.data:
                for log in previous_logs.data:
                    speaker = "Broker" if log['direction'] == 'outbound' else "User"
                    timestamp = datetime.datetime.fromisoformat(log['timestamp'].replace('Z', '+00:00')).strftime('%H:%M:%S')
                    call_transcript.append({
                        'speaker': speaker,
                        'content': log['content'],
                        'timestamp': timestamp
                    })
                logger.info(f"Retrieved {len(call_transcript)} messages from current conversation")
        
        # Get previous call history (last 3 calls)
        previous_calls = []
        try:
            # Get the user's previous calls (exclude current call)
            past_calls = supabase.table('calls').select('id,call_sid,started_at,status')\
                .eq('user_id', user_id)\
                .neq('call_sid', call_sid)\
                .order('started_at', desc=True)\
                .limit(3)\
                .execute()
                
            if past_calls.data:
                for call in past_calls.data:
                    # For each call, get a sample of the logs
                    call_summary = {
                        'date': datetime.datetime.fromisoformat(call['started_at'].replace('Z', '+00:00')).strftime('%Y-%m-%d'),
                        'highlights': []
                    }
                    
                    # Get important logs from this call (e.g., trades, recommendations)
                    call_logs = supabase.table('call_logs').select('*')\
                        .eq('call_sid', call['call_sid'])\
                        .order('timestamp')\
                        .execute()
                    
                    if call_logs.data:
                        # Find any trade actions or recommendations
                        for log in call_logs.data:
                            content = log['content'].upper()
                            if 'BUY' in content or 'SELL' in content or 'RECOMMEND' in content:
                                call_summary['highlights'].append({
                                    'speaker': 'Broker' if log['direction'] == 'outbound' else 'User',
                                    'content': log['content']
                                })
                                
                        # Get at least one exchange (first broker message and user response)
                        if not call_summary['highlights'] and len(call_logs.data) >= 2:
                            for i, log in enumerate(call_logs.data):
                                if log['direction'] == 'outbound' and i < len(call_logs.data) - 1:
                                    call_summary['highlights'].append({
                                        'speaker': 'Broker',
                                        'content': log['content']
                                    })
                                    # Get next user response
                                    next_log = call_logs.data[i+1]
                                    if next_log['direction'] == 'inbound':
                                        call_summary['highlights'].append({
                                            'speaker': 'User',
                                            'content': next_log['content']
                                        })
                                    break
                                    
                    if call_summary['highlights']:
                        previous_calls.append(call_summary)
                
                logger.info(f"Retrieved highlights from {len(previous_calls)} previous calls")
        except Exception as e:
            logger.error(f"Error retrieving previous call history: {e}")
            # Continue without previous calls if there's an error
        
        # Get user data with full context
        user_data = await trading_service.get_user_summary(user_id)
        # Add call transcript to user data
        user_data['call_transcript'] = call_transcript
        # Add previous calls to user data
        user_data['previous_calls'] = previous_calls
        
        if is_price_check and ticker:
            logger.info(f"Detected price check query for ticker: {ticker}")
            
            # Generate price check response
            broker_response = await gemini_service._generate_price_check_response(ticker, user_data)
            logger.info(f"Generated price check response: {broker_response}")
            
        else:
            # STEP 2: If not a price check, generate trading intent
            trading_intent = await gemini_service.generate_trading_order(transcription)
            logger.info(f"Generated trading intent: {trading_intent}")
            
            # Check for positive responses to recommendations
            positive_responses = ["yes", "yeah", "sure", "okay", "ok", "let's do it", "sounds good", "i agree", "go ahead"]
            is_agreement = any(phrase in transcription.lower() for phrase in positive_responses)
            
            # STEP 3: Handle based on intent type
            if trading_intent.get('is_conversation', False):
                # CASE A: Conversational query
                if is_agreement:
                    # If agreement, check for recent recommendation
                    logger.info(f"User appears to agree with recommendation: {transcription}")
                    
                    # Find most recent broker message
                    recent_logs = supabase.table('call_logs').select('*')\
                        .eq('call_sid', call_sid)\
                        .eq('direction', 'outbound')\
                        .order('timestamp', desc=True)\
                        .limit(1)\
                        .execute()
                    
                    recommendation_found = False
                    if recent_logs.data:
                        broker_message = recent_logs.data[0]['content']
                        # Extract stock symbols
                        import re
                        potential_tickers = re.findall(r'\b[A-Z]{1,5}\b', broker_message)
                        
                        # Look for buy/sell actions
                        buy_phrases = ["buy", "purchase", "get", "picking up"]
                        sell_phrases = ["sell", "dump", "get rid of"]
                        
                        # Default action is buy
                        action = "buy"
                        for phrase in sell_phrases:
                            if phrase in broker_message.lower():
                                action = "sell"
                                break
                        
                        # Find quantity
                        quantity_match = re.search(r'(\d+)\s+shares', broker_message)
                        quantity = 10  # Default
                        if quantity_match:
                            quantity = int(quantity_match.group(1))
                        
                        # Use first ticker found
                        if potential_tickers:
                            ticker = potential_tickers[0]
                            recommendation_found = True
                            
                            logger.info(f"Extracted recommendation: {action} {quantity} shares of {ticker}")
                            
                            # Execute the trade
                            trade_result = await trading_service.execute_paper_trade(user_id, action, ticker, quantity)
                            logger.info(f"Trade result: {trade_result}")
                            
                            # Generate broker response
                            recommendation_intent = {
                                'action': action,
                                'ticker': ticker,
                                'quantity': quantity,
                                'is_conversation': False
                            }
                            broker_response = await gemini_service.generate_broker_response(recommendation_intent, trade_result, user_data)
                            logger.info(f"Generated broker response: {broker_response}")
                    
                    # If no recommendation found, handle as conversation
                    if not recommendation_found:
                        logger.info(f"Handling as regular conversation: {transcription}")
                        market_data = await trading_service.get_market_summary()
                        user_data = await trading_service.get_user_summary(user_id)
                        broker_response = await gemini_service.generate_conversation_response(
                            trading_intent.get('query', transcription), 
                            user_data, 
                            market_data
                        )
                else:
                    # Regular conversation
                    logger.info(f"Handling conversation: {trading_intent.get('query')}")
                    market_data = await trading_service.get_market_summary()
                    user_data = await trading_service.get_user_summary(user_id)
                    broker_response = await gemini_service.generate_conversation_response(
                        trading_intent.get('query', transcription), 
                        user_data, 
                        market_data
                    )
            else:
                # CASE B: Trading intent
                logger.info(f"Executing trade: {trading_intent['action']} {trading_intent['quantity']} {trading_intent['ticker']}")
                
                # Validate that ticker and quantity are not None before executing the trade
                if not trading_intent.get('ticker') or not trading_intent.get('quantity'):
                    logger.error(f"Invalid trading intent - missing required parameters: {trading_intent}")
                    broker_response = "I couldn't process that trade request because some required information is missing. Please provide a stock ticker symbol and quantity."
                else:
                    # Execute the trade only if we have valid parameters
                    trade_result = await trading_service.execute_paper_trade(user_id, trading_intent['action'], trading_intent['ticker'], trading_intent['quantity'])
                    logger.info(f"Trade result: {trade_result}")
                    
                    broker_response = await gemini_service.generate_broker_response(trading_intent, trade_result, user_data)
                    logger.info(f"Broker response: {broker_response}")
        
        # STEP 4: Generate response and log it
        twiml = await twilio_service.generate_response_twiml(broker_response, gather_again=True)
        
        supabase.table('call_logs').insert({
            'user_id': user_id,
            'call_sid': call_sid,
            'direction': 'outbound',
            'content': broker_response,
            'timestamp': datetime.datetime.utcnow().isoformat()
        }).execute()
        
        return Response(content=twiml, media_type="application/xml")
    except Exception as e:
        logger.error(f"Error processing speech: {e}")
        response = VoiceResponse()
        response.say("Sorry, there was a problem processing your request. Please try again.", voice='Polly.Matthew')
        
        backend_url = BACKEND_URL.rstrip('/')
        gather = Gather(
            input='speech',
            action=f"{backend_url}/api/calls/process_speech",
            method='POST',
            timeout=5,
            speechTimeout='auto'
        )
        gather.say("What would you like to do?", voice='Polly.Matthew')
        response.append(gather)
        return Response(content=str(response), media_type="application/xml")

@router.post("/retry")
@router.post("/api/calls/retry")  # Add an alias to handle both URL patterns
async def retry_prompt(request: Request):
    """
    Handle retry when user doesn't respond to the initial prompt.
    """
    try:
        # Get the form data from Twilio
        form_data = await request.form()
        call_sid = form_data.get('CallSid')
        phone_number = form_data.get('From')
        
        # Skip Twilio numbers (they start with +1888)
        if phone_number and phone_number.startswith('+1888'):
            logger.info(f"Skipping Twilio number: {phone_number}")
            # Get the actual user's phone number from the To field
            phone_number = form_data.get('To')
            if not phone_number:
                logger.error("No user phone number found in To field")
                response = VoiceResponse()
                response.say("Sorry, there was a problem identifying your account. Please try again later.", voice='Polly.Matthew')
                response.hangup()
                return Response(content=str(response), media_type="application/xml")
        
        # Look up the user by phone number
        supabase = get_supabase_client(use_service_role=True)
        
        # Get user by phone number - try looking up the current call first
        call_result = supabase.table('calls').select('user_id').eq('call_sid', call_sid).execute()
        
        user_id = None
        if call_result.data and call_result.data[0]:
            user_id = call_result.data[0]['user_id']
            logger.info(f"Found user ID {user_id} from call record")
        else:
            # Fall back to looking up by phone number
            user_result = supabase.table('users').select('id').eq('phone_number', phone_number).execute()
            
            # If that fails, try with additional formatting variations
            if not user_result.data:
                # Try a version without the leading +
                if phone_number.startswith('+'):
                    user_result = supabase.table('users').select('id').eq('phone_number', phone_number[1:]).execute()
                    
            if user_result.data:
                user_id = user_result.data[0]['id']
            else:
                logger.error(f"Could not find user by phone number: {phone_number}")
                response = VoiceResponse()
                response.say("Sorry, I couldn't find your account. Please register on our website first.", voice='Polly.Matthew')
                response.hangup()
                return Response(content=str(response), media_type="application/xml")
        
        # Get market and user data for context
        market_data = await trading_service.get_market_summary()
        user_data = await trading_service.get_user_summary(user_id)
        
        # Generate a stock recommendation
        recommendation = await gemini_service.generate_stock_recommendation(user_data, market_data)
        
        # Generate a retry prompt with a stock recommendation
        retry_prompt = f"Hey, you still there? I've got a hot tip for you - I'm recommending {recommendation['quantity']} shares of {recommendation['ticker']}. {recommendation['rationale']} By the way, you can ask me for the latest price on any stock. Just say something like 'What's AAPL trading at?' So, what do you think? Want to {recommendation['action']} some {recommendation['ticker']} today or check prices on something else?"
        
        # Generate TwiML with the retry prompt
        twiml = await twilio_service.generate_response_twiml(retry_prompt, gather_again=True)
        
        # Log the retry prompt
        supabase.table('call_logs').insert({
            'user_id': user_id,
            'call_sid': call_sid,
            'direction': 'outbound',
            'content': retry_prompt,
            'timestamp': datetime.datetime.utcnow().isoformat()
        }).execute()
        
        return Response(content=twiml, media_type="application/xml")
    except Exception as e:
        logger.error(f"Error in retry endpoint: {e}")
        # Return a simple TwiML response in case of error
        response = VoiceResponse()
        response.say("Sorry, there was a problem. Please try again.", voice='Polly.Matthew')
        response.hangup()
        return Response(content=str(response), media_type="application/xml")

@router.post("/status/{user_id}")
async def call_status(user_id: str, request: Request):
    """
    Handle Twilio call status callbacks.
    """
    try:
        form_data = await request.form()
        call_sid = form_data.get('CallSid')
        call_status = form_data.get('CallStatus')
        
        logger.info(f"Call status update for call {call_sid}: {call_status}")
        
        # Initialize Supabase client with service role
        supabase = get_supabase_client(use_service_role=True)
        
        # Get the current call record
        call_result = supabase.table('calls').select('*').eq('call_sid', call_sid).execute()
        
        # If no call record exists, create one for failed calls
        if not call_result.data and call_status in ['failed', 'busy', 'no-answer', 'canceled']:
            logger.info(f"Creating call record for failed call: {call_sid}")
            # Get the phone number from the form data
            phone_number = form_data.get('To')
            if not phone_number:
                phone_number = form_data.get('From')
                
            # Create a new call record
            call_data = {
                "user_id": user_id,
                "phone_number": phone_number,
                "status": call_status,
                "call_sid": call_sid,
                "started_at": datetime.datetime.utcnow().isoformat(),
                "ended_at": datetime.datetime.utcnow().isoformat(),
                "direction": "outbound",
                "duration": 0
            }
            
            response = supabase.table("calls").insert(call_data).execute()
            if not response.data:
                logger.error(f"Failed to create call record for failed call: {call_sid}")
                return {"status": "error", "message": "Failed to create call record"}
                
            return {"status": "success", "call_status": call_status}
            
        elif not call_result.data:
            logger.error(f"Call record not found for SID: {call_sid}")
            return {"status": "error", "message": "Call record not found"}
            
        call = call_result.data[0]
        
        # Update call status and other fields based on the status
        update_data = {
            'status': call_status
        }
        
        # Handle different call statuses
        if call_status in ['completed', 'failed', 'busy', 'no-answer', 'canceled']:
            # Call has ended, update ended_at
            update_data['ended_at'] = datetime.datetime.utcnow().isoformat()
            
            # Calculate duration if we have start time
            if call.get('started_at'):
                start_time = datetime.datetime.fromisoformat(call['started_at'].replace('Z', '+00:00'))
                end_time = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
                duration = int((end_time - start_time).total_seconds())
                if duration > 0:  # Only update if duration is positive
                    update_data['duration'] = duration
                else:
                    update_data['duration'] = 0
                    
            # Check for recording URL in the form data
            recording_url = form_data.get('RecordingUrl')
            if recording_url:
                update_data['recording_url'] = recording_url
                logger.info(f"Recording URL received for call {call_sid}: {recording_url}")
                
        elif call_status == 'in-progress':
            # Call has started, ensure started_at is set
            if not call.get('started_at'):
                update_data['started_at'] = datetime.datetime.utcnow().isoformat()
                
        # Update the call record
        try:
            update_result = supabase.table('calls').update(update_data).eq('call_sid', call_sid).execute()
            
            if not update_result.data:
                logger.error(f"Failed to update call record for SID: {call_sid}")
                return {"status": "error", "message": "Failed to update call record"}
                
            logger.info(f"Successfully updated call {call_sid} to status {call_status}")
            return {"status": "success", "call_status": call_status}
            
        except Exception as update_error:
            logger.error(f"Database error updating call status: {update_error}")
            return {"status": "error", "message": f"Database error: {str(update_error)}"}
        
    except Exception as e:
        logger.error(f"Error updating call status: {e}")
        return {"status": "error", "message": str(e)}

@router.post("/inbound")
async def handle_inbound_call(request: Request):
    """
    Handle incoming calls from users.
    This endpoint is called by Twilio when a user calls our number.
    """
    try:
        # Parse the form data from Twilio
        form_data = await request.form()
        caller_number = form_data.get('From')
        call_sid = form_data.get('CallSid')
        
        logger.info(f"Inbound call received from {caller_number}, SID: {call_sid}")
        
        # Format the phone number consistently
        digits_only = ''.join(filter(str.isdigit, caller_number))
        if len(digits_only) == 10:
            formatted_phone = f"+1{digits_only}"
        elif not digits_only.startswith('+'):
            formatted_phone = f"+{digits_only}"
        else:
            formatted_phone = caller_number
        
        # Get user by phone number
        supabase = get_supabase_client()
        user_result = supabase.table('users').select('*').eq('phone_number', formatted_phone).execute()
        
        # If user not found, return error message
        if not user_result.data:
            logger.warning(f"User not found for number {formatted_phone}")
            response = VoiceResponse()
            response.say("Sorry, we couldn't find your account. Please register on our website first.", voice='Polly.Matthew')
            response.hangup()
            return Response(content=str(response), media_type="application/xml")
            
        user = user_result.data[0]
        user_id = user['id']
        
        # Record the inbound call
        supabase.table('calls').insert({
            'user_id': user_id,
            'call_sid': call_sid,
            'status': 'in-progress',
            'phone_number': formatted_phone,
            'direction': 'inbound',
            'started_at': datetime.datetime.utcnow().isoformat()
        }).execute()
        
        # Get market data and user data
        market_data = await trading_service.get_market_summary()
        user_data = await trading_service.get_user_summary(user_id)
        
        # Generate broker intro
        broker_intro = await gemini_service.generate_broker_call_intro(user_data, market_data)
        
        # Generate TwiML response
        twiml = await twilio_service.generate_welcome_twiml(broker_intro)
        
        # Log the broker's intro - continue using service role client from above
        supabase.table('call_logs').insert({
            'user_id': user_id,
            'call_sid': call_sid,
            'direction': 'outbound',
            'content': broker_intro,
            'timestamp': datetime.datetime.utcnow().isoformat()
        }).execute()
        
        return Response(content=twiml, media_type="application/xml")
        
    except Exception as e:
        logger.error(f"Error handling inbound call: {e}")
        # Return a simple TwiML response in case of error
        response = VoiceResponse()
        response.say("Sorry, there was a problem connecting to your broker. Please try again later.", voice='Polly.Matthew')
        response.hangup()
        return Response(content=str(response), media_type="application/xml") 

@router.websocket("/stream/{call_id}")
async def websocket_endpoint(websocket: WebSocket, call_id: str):
    """
    Websocket endpoint for Twilio Media Streams
    """
    logger.info(f"Incoming WebSocket connection for call: {call_id}")
    await elevenlabs_twilio_service.handle_websocket(websocket, call_id)
    
@router.post("/stream/test")
async def test_stream():
    """
    Test endpoint for trying the ElevenLabs Twilio integration
    """
    # Generate the test message TwiML
    base_url = BACKEND_URL.rstrip('/')
    connect_url = f"{base_url}/api/calls/stream/connect"
    
    twiml = f"""
    <?xml version="1.0" encoding="UTF-8"?>
    <Response>
        <Say voice="Polly.Matthew">Connecting to your broker using premium ElevenLabs voice.</Say>
        <Redirect method="POST">{connect_url}</Redirect>
    </Response>
    """
    
    return Response(content=twiml, media_type="application/xml")

@router.post("/stream/connect")
async def connect_stream(request: Request):
    """
    Endpoint for Twilio to connect to our WebSocket for streaming
    """
    try:
        # Get the base URL from the request or fallback to BACKEND_URL
        base_url = os.getenv('PUBLIC_BACKEND_URL')
        if not base_url:
            logger.warning("PUBLIC_BACKEND_URL not set, using BACKEND_URL as fallback")
            base_url = BACKEND_URL
            
        # Strip trailing slash if present
        base_url = base_url.rstrip('/')
        
        # Get the call SID from the form data
        form_data = await request.form()
        call_sid = form_data.get('CallSid')
        
        # Generate the WebSocket URL
        if base_url.startswith('http://'):
            websocket_url = f"ws://{base_url.split('://')[1]}/api/calls/stream/{call_sid}"
        else:
            websocket_url = f"wss://{base_url.split('://')[1]}/api/calls/stream/{call_sid}"
        logger.info(f"Using WebSocket URL: {websocket_url}")
        
        # Return TwiML with the Connect->Stream instruction
        twiml = elevenlabs_twilio_service.get_connection_twiml(websocket_url)
        return Response(content=twiml, media_type="application/xml")
    except Exception as e:
        logger.error(f"Error in stream connect: {e}")
        # Return a simple TwiML response in case of error
        response = VoiceResponse()
        response.say("Sorry, there was a problem connecting to the AI voice service.", voice='Polly.Matthew')
        response.hangup()
        return Response(content=str(response), media_type="application/xml")

@router.post("/initiate-elevenlabs/{user_id}")
async def initiate_elevenlabs_call(
    request: Request,
    user_id: str
):
    """
    Initiate a call using ElevenLabs voice service via Twilio Media Streams
    """
    try:
        logger.info(f"Initiating ElevenLabs call for user_id: {user_id}")
        # Get the user's phone number using the user_id from path
        user = await get_user(user_id)
        if not user or not user.phone_number:
            raise HTTPException(
                status_code=400,
                detail="User not found or phone number not set"
            )
        
        # Format the phone number to E.164 format
        phone_number = user.phone_number
        if not phone_number.startswith('+'):
            phone_number = f"+{phone_number}"
        
        # Use PUBLIC_BACKEND_URL env var for callbacks, fallback to request base_url
        public_callback_base = os.getenv('PUBLIC_BACKEND_URL')
        if not public_callback_base:
            logger.warning("PUBLIC_BACKEND_URL environment variable not set. Falling back to request base_url for Twilio callbacks.")
            public_callback_base = str(request.base_url)
            
        # Ensure base URL doesn't have a trailing slash
        if public_callback_base.endswith('/'):
            public_callback_base = public_callback_base[:-1]
        
        # Create the stream test URL
        stream_url = f"{public_callback_base}/api/calls/stream/test"
        
        # Initialize Twilio service
        twilio_service = TwilioService()
        
        # Initiate the call with the stream test URL
        result = twilio_service.initiate_call(
            to_number=phone_number,
            user_id=user_id,
            connect_url=stream_url
        )
        
        if result["status"] == "error":
            raise HTTPException(
                status_code=500,
                detail=result["error"]
            )
        
        # Initialize Supabase client with service role
        supabase = get_supabase_client(use_service_role=True)
        
        # Create a call record in the database
        call_data = {
            "user_id": user_id,
            "phone_number": phone_number,
            "status": "initiated", 
            "call_sid": result["call_sid"],
            "started_at": datetime.datetime.utcnow().isoformat(),
            "direction": "outbound",
            "notes": "ElevenLabs streaming call"
        }
        
        response = supabase.table("calls").insert(call_data).execute()
        
        return {
            "status": "success",
            "message": "ElevenLabs call initiated successfully",
            "call_sid": result["call_sid"]
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error initiating ElevenLabs call: {e}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@router.get("/history/{user_id}")
async def get_call_history(user_id: str, limit: int = 20):
    """
    Get the call history for a user.
    
    Parameters:
        user_id: User ID
        limit: Maximum number of calls to return
    """
    try:
        # Initialize Supabase client with service role for full access
        supabase = get_supabase_client(use_service_role=True)
        
        # Get the user's call history
        calls_data = supabase.table('calls').select('*')\
            .eq('user_id', user_id)\
            .order('started_at', desc=True)\
            .limit(limit)\
            .execute()
            
        if not calls_data.data:
            logger.info(f"No call history found for user {user_id}")
            return {"calls": []}
            
        calls = calls_data.data
        
        # For each call, get the call logs if call_sid exists
        for call in calls:
            if call.get('call_sid'):
                try:
                    call_logs = supabase.table('call_logs').select('*')\
                        .eq('call_sid', call['call_sid'])\
                        .order('timestamp')\
                        .execute()
                        
                    # Extract a summary from the call logs
                    summary = ""
                    actions = []
                    transcript = []
                    
                    if call_logs.data:
                        # Find at least one outbound message as summary
                        for log in call_logs.data:
                            if log['direction'] == 'outbound' and log['content']:
                                # Use the first few characters of the first outbound message as summary
                                summary = log['content'].strip()
                                if len(summary) > 150:
                                    summary = summary[:150] + "..."
                                break
                        
                        # Extract trading actions from logs and build transcript
                        for log in call_logs.data:
                            if log['content']:
                                # Add to transcript with speaker and timestamp
                                speaker = "Broker" if log['direction'] == 'outbound' else "User"
                                timestamp = datetime.datetime.fromisoformat(log['timestamp'].replace('Z', '+00:00')).strftime('%H:%M:%S')
                                transcript.append({
                                    'speaker': speaker,
                                    'content': log['content'],
                                    'timestamp': timestamp
                                })
                                
                                # Extract trading actions
                                if log['direction'] == 'inbound':
                                    content = log['content'].upper()
                                    if 'BUY' in content or 'SELL' in content:
                                        words = content.split()
                                        for i, word in enumerate(words):
                                            if word in ['BUY', 'SELL'] and i + 2 < len(words):
                                                # Look for ticker and quantity pattern
                                                ticker = words[i+1]
                                                try:
                                                    quantity = int(words[i+2])
                                                    actions.append(f"{word} {ticker} {quantity}")
                                                except ValueError:
                                                    # If not a number, just include the ticker
                                                    actions.append(f"{word} {ticker}")
                    
                    # Add the enriched information to the call
                    call['summary'] = summary
                    call['actions'] = actions
                    call['transcript'] = transcript
                except Exception as e:
                    logger.error(f"Error getting call logs for call {call.get('call_sid')}: {e}")
                    # Continue with empty summary, actions, and transcript
                    call['summary'] = ""
                    call['actions'] = []
                    call['transcript'] = []
            else:
                # For calls without call_sid (e.g., failed calls), set empty summary, actions, and transcript
                call['summary'] = ""
                call['actions'] = []
                call['transcript'] = []
            
            # Calculate duration if available
            duration = None
            if call.get('started_at') and call.get('ended_at'):
                try:
                    start_time = datetime.datetime.fromisoformat(call['started_at'].replace('Z', '+00:00'))
                    end_time = datetime.datetime.fromisoformat(call['ended_at'].replace('Z', '+00:00'))
                    duration = int((end_time - start_time).total_seconds())
                except Exception as e:
                    logger.error(f"Error calculating duration for call {call.get('id')}: {e}")
                    duration = 0
            
            call['duration'] = duration
        
        logger.info(f"Retrieved {len(calls)} calls for user {user_id}")
        return {"calls": calls}
    except Exception as e:
        logger.error(f"Error getting call history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/status/{user_id}/recording")
async def recording_status(user_id: str, request: Request):
    """
    Handle Twilio recording status callbacks.
    """
    try:
        form_data = await request.form()
        call_sid = form_data.get('CallSid')
        recording_url = form_data.get('RecordingUrl')
        recording_status = form_data.get('RecordingStatus')
        
        logger.info(f"Recording status update for call {call_sid}: {recording_status}")
        
        if not recording_url:
            logger.warning(f"No recording URL provided for call {call_sid}")
            return {"status": "error", "message": "No recording URL provided"}
            
        # Initialize Supabase client with service role
        supabase = get_supabase_client(use_service_role=True)
        
        # Update the call record with the recording URL
        update_result = supabase.table('calls').update({
            'recording_url': recording_url
        }).eq('call_sid', call_sid).execute()
        
        if not update_result.data:
            logger.error(f"Failed to update recording URL for call {call_sid}")
            return {"status": "error", "message": "Failed to update recording URL"}
            
        logger.info(f"Successfully updated recording URL for call {call_sid}")
        return {"status": "success", "recording_status": recording_status}
        
    except Exception as e:
        logger.error(f"Error handling recording status: {e}")
        return {"status": "error", "message": str(e)} 