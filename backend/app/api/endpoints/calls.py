from fastapi import APIRouter, HTTPException, WebSocket, Depends, Request, Body
import logging
from typing import Optional
from fastapi.responses import Response
import json
import os
import sys
from twilio.twiml.voice_response import VoiceResponse, Gather
import datetime
import uuid

# Import the central path setup module
from app.core.imports import APP_DIR, BACKEND_DIR

# Import services
from app.services.twilio_service import TwilioService
from app.services.gemini_service import GeminiService
from app.services.trading_service import TradingService
from app.db.supabase import get_supabase_client

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/calls", tags=["calls"])

# Initialize services
twilio_service = TwilioService()
gemini_service = GeminiService()
trading_service = TradingService()

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

@router.post("/schedule")
async def schedule_call(
    user_id: str, 
    phone_number: str, 
    call_time: str,
    call_type: str = "market_open"  # market_open, mid_day, market_close
):
    """
    Schedule a call to a user at a specific time.
    This would typically be implemented with a task queue or cron job.
    For the hackathon, we'll just return the scheduling info.
    """
    try:
        supabase = get_supabase_client()
        
        # Store the call schedule in Supabase
        schedule = {
            'user_id': user_id,
            'phone_number': phone_number,
            'call_time': call_time,
            'call_type': call_type,
            'status': 'scheduled'
        }
        
        result = supabase.table('call_schedules').insert(schedule).execute()
        
        return {
            "status": "scheduled",
            "schedule_id": result.data[0]['id'] if result.data else None,
            "message": f"Call scheduled for {call_time}"
        }
    except Exception as e:
        logger.error(f"Error scheduling call: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/initiate/{user_id}")
async def initiate_call(user_id: str):
    """
    Manually initiate a call to a user now.
    """
    try:
        supabase = get_supabase_client()
        
        # Get user's phone number
        user_info = supabase.table('users').select('phone_number').eq('id', user_id).execute()
        
        if not user_info.data:
            raise HTTPException(status_code=404, detail="User not found")
        
        phone_number = user_info.data[0]['phone_number']
        
        # Format the phone number to E.164 format required by Twilio
        formatted_phone = format_phone_number(phone_number)
        if not formatted_phone:
            raise HTTPException(status_code=400, detail="Invalid phone number")
        
        logger.info(f"Initiating call to user {user_id} with phone number {formatted_phone}")
        
        # Initiate the call using Twilio
        call_result = twilio_service.initiate_call(formatted_phone, user_id)
        
        # Check if call initiation failed
        if call_result.get('status') == 'error':
            logger.error(f"Twilio call initiation failed: {call_result.get('error')}")
            raise HTTPException(status_code=500, detail=f"Twilio error: {call_result.get('error')}")
        
        # Record the call in the database
        supabase.table('calls').insert({
            'user_id': user_id,
            'call_sid': call_result.get('call_sid'),
            'status': call_result.get('status'),
            'phone_number': formatted_phone
        }).execute()
        
        return call_result
    except Exception as e:
        logger.error(f"Error initiating call: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/connect/{user_id}")
async def connect_call(user_id: str, request: Request):
    """
    Generate TwiML for the initial call connection.
    This endpoint is called by Twilio when the call connects.
    """
    try:
        # Get market data
        market_data = await trading_service.get_market_summary()
        
        # Get user data
        user_data = await trading_service.get_user_summary(user_id)
        
        # Generate broker intro using Gemini
        broker_intro = await gemini_service.generate_broker_call_intro(user_data, market_data)
        
        # Generate TwiML response with the broker intro
        twiml = twilio_service.generate_welcome_twiml(broker_intro)
        
        # Log the broker's intro
        supabase = get_supabase_client()
        supabase.table('call_logs').insert({
            'user_id': user_id,
            'direction': 'outbound',
            'content': broker_intro,
            'timestamp': 'now()'
        }).execute()
        
        return Response(content=twiml, media_type="application/xml")
    except Exception as e:
        logger.error(f"Error connecting call: {e}")
        # Return a simple TwiML response in case of error
        response = VoiceResponse()
        response.say("Sorry, there was a problem connecting to your broker. Please try again later.", voice='Polly.Matthew')
        response.hangup()
        return Response(content=str(response), media_type="application/xml")

@router.post("/process_speech")
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
        user_id = form_data.get('From')  # Using the caller's phone number as a proxy for user_id
        call_sid = form_data.get('CallSid')
        
        if not transcription:
            # If no transcription, prompt user to speak again
            twiml = twilio_service.generate_response_twiml(
                "I didn't catch that. Could you please repeat?", 
                gather_again=True
            )
            return Response(content=twiml, media_type="application/xml")
        
        # Log the user's speech
        supabase = get_supabase_client()
        supabase.table('call_logs').insert({
            'user_id': user_id,
            'call_sid': call_sid,
            'direction': 'inbound',
            'content': transcription,
            'timestamp': 'now()'
        }).execute()
        
        # Parse the trading intent using Gemini
        intent = await gemini_service.parse_trading_intent(transcription)
        
        # If we couldn't parse the intent, ask for clarification
        if not all([intent.get('action'), intent.get('ticker'), intent.get('quantity')]):
            clarification_response = "I'm not sure I understood that correctly. Could you specify if you want to buy or sell, which stock, and how many shares?"
            twiml = twilio_service.generate_response_twiml(clarification_response, gather_again=True)
            return Response(content=twiml, media_type="application/xml")
        
        # Execute the paper trade
        trade_result = await trading_service.execute_paper_trade(
            user_id, 
            intent['action'], 
            intent['ticker'], 
            intent['quantity']
        )
        
        # Generate broker response using Gemini
        broker_response = await gemini_service.generate_broker_response(intent, trade_result)
        
        # Generate TwiML with the broker response
        twiml = twilio_service.generate_response_twiml(broker_response, gather_again=True)
        
        # Log the broker's response
        supabase.table('call_logs').insert({
            'user_id': user_id,
            'call_sid': call_sid,
            'direction': 'outbound',
            'content': broker_response,
            'timestamp': 'now()'
        }).execute()
        
        # Broadcast the trade result to WebSocket clients
        # In a real app, you'd use a message queue for this
        # For hackathon purposes, we'll just return the TwiML
        
        return Response(content=twiml, media_type="application/xml")
    except Exception as e:
        logger.error(f"Error processing speech: {e}")
        # Return a simple TwiML response in case of error
        response = VoiceResponse()
        response.say("Sorry, there was a problem processing your request. Please try again.", voice='Polly.Matthew')
        gather = Gather(
            input='speech',
            action=f"{BACKEND_URL}/api/calls/process_speech",
            method='POST',
            timeout=5,
            speechTimeout='auto'
        )
        gather.say("What would you like to do?", voice='Polly.Matthew')
        response.append(gather)
        return Response(content=str(response), media_type="application/xml")

@router.post("/retry")
async def retry_speech(request: Request):
    """
    Handle the case when the user doesn't speak or the speech isn't recognized.
    """
    try:
        twiml = twilio_service.generate_response_twiml(
            "I didn't catch that. Let me know if you want to buy or sell any stocks today.", 
            gather_again=True
        )
        return Response(content=twiml, media_type="application/xml")
    except Exception as e:
        logger.error(f"Error in retry speech: {e}")
        response = VoiceResponse()
        response.say("Sorry, there was a problem. Goodbye for now.", voice='Polly.Matthew')
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
        
        # Update call status in the database
        supabase = get_supabase_client()
        supabase.table('calls').update({
            'status': call_status
        }).eq('call_sid', call_sid).execute()
        
        # If the call completed, you might want to generate a call summary
        # and send it to the user via email or store it for the dashboard
        
        return {"status": "success", "call_status": call_status}
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
        
        # Format the phone number for database lookup
        formatted_phone = format_phone_number(caller_number)
        
        # Get user by phone number
        supabase = get_supabase_client()
        user_result = supabase.table('users').select('*').eq('phone_number', formatted_phone).execute()
        
        # If user not found, try without formatting
        if not user_result.data:
            user_result = supabase.table('users').select('*').eq('phone_number', caller_number).execute()
            
        # If user still not found, create a temporary user for demo purposes
        if not user_result.data:
            logger.info(f"User not found for number {caller_number}. Creating temporary demo user.")
            
            user_id = str(uuid.uuid4())
            demo_user = {
                'id': user_id,
                'email': f"demo_{user_id[:8]}@example.com",
                'name': 'Demo User',
                'phone_number': formatted_phone,  # Store the formatted number
                'cash_balance': 25000.0,
                'created_at': datetime.datetime.now().isoformat(),
                'updated_at': datetime.datetime.now().isoformat()
            }
            
            try:
                # Insert demo user into the custom users table
                supabase.table('users').insert(demo_user).execute()
                user = demo_user
                user_id = user['id']
                logger.info(f"Created demo user with ID: {user_id}")
            except Exception as user_error:
                logger.error(f"Failed to create demo user: {user_error}")
                # If we can't create a user, return a helpful message
                response = VoiceResponse()
                response.say("I'm having trouble creating a demo account for your number. The database might have Row Level Security restrictions. Please register on our website first.", voice='Polly.Matthew')
                response.hangup()
                return Response(content=str(response), media_type="application/xml")
        else:
            user = user_result.data[0]
            user_id = user['id']
        
        # Record the inbound call
        supabase.table('calls').insert({
            'user_id': user_id,
            'call_sid': call_sid,
            'status': 'in-progress',
            'phone_number': formatted_phone,
            'direction': 'inbound'
        }).execute()
        
        # Get market data and user data
        market_data = await trading_service.get_market_summary()
        user_data = await trading_service.get_user_summary(user_id)
        
        # Generate broker intro
        broker_intro = await gemini_service.generate_broker_call_intro(user_data, market_data)
        
        # Generate TwiML response
        twiml = twilio_service.generate_welcome_twiml(broker_intro)
        
        # Log the broker's intro
        supabase.table('call_logs').insert({
            'user_id': user_id,
            'call_sid': call_sid,
            'direction': 'outbound',
            'content': broker_intro,
            'timestamp': 'now()'
        }).execute()
        
        return Response(content=twiml, media_type="application/xml")
        
    except Exception as e:
        logger.error(f"Error handling inbound call: {e}")
        # Return a simple TwiML response in case of error
        response = VoiceResponse()
        response.say("Sorry, there was a problem connecting to your broker. Please try again later.", voice='Polly.Matthew')
        response.hangup()
        return Response(content=str(response), media_type="application/xml") 