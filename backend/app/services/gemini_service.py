import google.generativeai as genai
import logging

# Try both import approaches
try:
    # Absolute imports (when running from backend/)
    from app.core.config import GOOGLE_API_KEY
except ImportError:
    # Relative imports (when running from app/)
    from ..core.config import GOOGLE_API_KEY

logger = logging.getLogger(__name__)

# Configure the Gemini API
genai.configure(api_key=GOOGLE_API_KEY)

class GeminiService:
    def __init__(self):
        try:
            self.model = genai.GenerativeModel('gemini-pro')
        except Exception as e:
            logger.error(f"Error initializing Gemini model: {e}")
            raise

    async def generate_broker_call_intro(self, user_data, market_data):
        """
        Generate a broker intro for a call based on market data and user portfolio.
        
        Parameters:
            user_data (dict): User portfolio and preferences
            market_data (dict): Current market data and news
            
        Returns:
            str: The broker's introduction script
        """
        try:
            prompt = f"""
            You are WOLF, an AI stock broker with the personality of a 1980s Wall Street broker - confident, sharp, and a bit aggressive but professional. You use period-appropriate slang, speak with energy, and have a flair for the dramatic.

            BROKER CHARACTER TRAITS:
            - Confident and direct, but not arrogant
            - Uses occasional 80s Wall Street slang like "bull market", "making a killing", "bullish", etc.
            - Speaks in short, punchy sentences
            - Addresses the client by name and builds rapport
            - Is knowledgeable about markets and trading

            CURRENT MARKET DATA:
            S&P 500: {market_data.get('sp500', 'Unknown')}
            Dow Jones: {market_data.get('dow', 'Unknown')}
            Nasdaq: {market_data.get('nasdaq', 'Unknown')}
            
            BREAKING NEWS:
            {market_data.get('top_news', 'No major news today.')}
            
            CLIENT INFO:
            Name: {user_data.get('name', 'buddy')}
            Portfolio value: ${user_data.get('portfolio_value', '0')}
            Cash balance: ${user_data.get('cash_balance', '0')}
            
            PORTFOLIO POSITIONS:
            {self._format_positions(user_data.get('positions', []))}
            
            RECENT TRADES:
            {user_data.get('recent_trades', 'No recent trades.')}
            
            INSTRUCTIONS:
            1. Generate a personalized greeting that addresses the client by name
            2. Give a quick, punchy summary of the market's current state using one key index
            3. Mention one relevant news item if available
            4. Comment briefly on the client's portfolio or recent trades
            5. Ask how you can help them today
            
            Your response should be conversational, energetic, and sound like a real 1980s Wall Street broker on the phone. Keep it to 4-6 sentences maximum.
            """
            
            response = await self.model.generate_content_async(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Error generating broker intro: {e}")
            return "Hey there! The market's been wild today. What can I do for you?"
    
    def _format_positions(self, positions):
        """Format portfolio positions for the prompt"""
        if not positions:
            return "No current positions."
        
        formatted = []
        for pos in positions:
            profit_loss = pos.get('profit_loss', 0)
            status = "profitable" if profit_loss > 0 else "at a loss"
            formatted.append(
                f"{pos.get('ticker')}: {pos.get('quantity')} shares worth ${pos.get('value', 0):.2f} ({profit_loss:.2f}% {status})"
            )
        
        return "\n".join(formatted)
    
    async def parse_trading_intent(self, transcription):
        """
        Parse the user's spoken intent from a transcription.
        
        Parameters:
            transcription (str): The transcribed user speech
            
        Returns:
            dict: Parsed trading intent with action, ticker, and quantity
        """
        try:
            prompt = f"""
            Parse the following statement from a client into a trading action. Extract the following fields:
            - action: buy or sell
            - ticker: the stock symbol
            - quantity: the number of shares
            
            Client statement: "{transcription}"
            
            Output the result as a JSON object with the fields: action, ticker, quantity
            If any field is missing or unclear, mark it as null.
            """
            
            response = await self.model.generate_content_async(prompt)
            
            # Basic error checking - in production you'd want more robust parsing
            result = response.text
            
            # We'd need proper JSON parsing here, this is simplified
            # In a real app, you might want to use a regex or proper JSON parsing
            if "action" in result and "ticker" in result and "quantity" in result:
                # Extract the values using a simple approach
                # In production, you'd use proper JSON parsing
                import json
                clean_json = result.strip().strip('`').strip('json').strip()
                return json.loads(clean_json)
            else:
                logger.warning(f"Failed to parse trading intent from: {transcription}")
                return {"action": None, "ticker": None, "quantity": None}
        except Exception as e:
            logger.error(f"Error parsing trading intent: {e}")
            return {"action": None, "ticker": None, "quantity": None}
    
    async def generate_broker_response(self, user_intent, trade_result):
        """
        Generate the broker's response after a trade is executed or rejected.
        
        Parameters:
            user_intent (dict): The parsed user intent
            trade_result (dict): The result of the trade execution
            
        Returns:
            str: The broker's response
        """
        try:
            status = trade_result.get('status', 'unknown')
            
            prompt = f"""
            You are a retro 1980s Wall Street stockbroker named Wolf. Generate a brief, energetic response to your client after:
            
            - They wanted to {user_intent.get('action')} {user_intent.get('quantity')} shares of {user_intent.get('ticker')}
            - The trade status was: {status}
            
            If the trade was successful, mention the new price (${trade_result.get('price', 'unknown')}) and be congratulatory.
            If it failed, explain briefly why in a sympathetic but upbeat way.
            
            Keep it to 1-2 short sentences and make it sound like a 1980s Wall Street broker (casual, slang, energetic).
            """
            
            response = await self.model.generate_content_async(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Error generating broker response: {e}")
            if trade_result.get('status') == 'success':
                return "Trade executed! You're all set, buddy."
            else:
                return "Couldn't make that trade right now. Let's try something else!" 