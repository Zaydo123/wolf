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
            # Try different model names to handle version differences
            self.model = None
            model_options = ['gemini-2.0-flash', 'gemini-pro', 'gemini-1.0-pro', 'gemini-1.5-pro']
            
            for model_name in model_options:
                try:
                    logger.info(f"Attempting to initialize Gemini with model: {model_name}")
                    self.model = genai.GenerativeModel(model_name)
                    logger.info(f"Successfully initialized Gemini with model: {model_name}")
                    break
                except Exception as model_error:
                    logger.warning(f"Failed to initialize model {model_name}: {model_error}")
            
            if not self.model:
                logger.error("Failed to initialize any Gemini model")
                raise ValueError("No available Gemini model could be initialized")
                
        except Exception as e:
            logger.error(f"Error initializing Gemini service: {e}")
            # Instead of raising, create a fallback model that can handle generation without errors
            logger.info("Creating fallback Gemini service that returns predefined responses")
            self.model = None

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
            # If model is None, return a default response
            if self.model is None:
                logger.info("Using fallback intro response since Gemini model is not available")
                client_name = user_data.get('name', 'buddy')
                return f"Hey {client_name}! Wolf here. The market's lookin' hot today. Your portfolio is holding steady. What stocks are you eyeing today?"
            
            prompt = f"""
            You are WOLF, an AI stock broker with the personality of a 1980s Wall Street broker - confident, sharp, and a bit aggressive but professional. You use period-appropriate slang, speak with energy, and have a flair for the dramatic.

            BROKER CHARACTER TRAITS:
            - Confident and direct, but not arrogant
            - Uses occasional 80s Wall Street slang like "bull market", "making a killing", "bullish", etc.
            - Speaks in short, punchy sentences
            - Always addresses the client by name (use their actual name from the data below)
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
            1. Generate a personalized greeting that addresses the client by their actual name from CLIENT INFO
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
            client_name = user_data.get('name', 'buddy')
            return f"Hey {client_name}! Wolf here. The market's lookin' hot today. Your portfolio is holding steady. What stocks are you eyeing today?"
    
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
        Determines if it's a trading action or a conversational query.
        
        Parameters:
            transcription (str): The transcribed user speech
            
        Returns:
            dict: Either trading intent with action/ticker/quantity OR conversation intent with is_conversation=True and query
        """
        try:
            # If model is None, try basic keyword parsing as fallback
            if self.model is None:
                logger.info("Using fallback intent parsing since Gemini model is not available")
                return self._basic_intent_parsing(transcription)
                
            # First, determine if this is a trade order or just conversation
            classification_prompt = f"""
            Classify the following statement from a client as either:
            1. A TRADE order (intent to buy or sell stocks)
            2. A CONVERSATION about markets, portfolio, advice, etc.
            
            Client statement: "{transcription}"
            
            Output only "TRADE" or "CONVERSATION" based on your classification.
            """
            
            classification_response = await self.model.generate_content_async(classification_prompt)
            result_type = classification_response.text.strip().upper()
            
            # If it's conversation, handle differently than trade
            if "CONVERSATION" in result_type:
                logger.info(f"Detected conversational query: {transcription}")
                return {
                    "is_conversation": True,
                    "query": transcription,
                    "action": None,
                    "ticker": None,
                    "quantity": None
                }
            
            # Otherwise, it's a trading intent, so parse it
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
            
            try:
                # Extract the values using a simple approach
                import json
                clean_json = result.strip().strip('`').strip('json').strip()
                parsed_intent = json.loads(clean_json)
                parsed_intent["is_conversation"] = False
                return parsed_intent
            except Exception as json_err:
                logger.warning(f"Failed to parse trading intent from: {transcription}")
                fallback = self._basic_intent_parsing(transcription)
                fallback["is_conversation"] = False
                return fallback
                
        except Exception as e:
            logger.error(f"Error parsing trading intent: {e}")
            fallback = self._basic_intent_parsing(transcription)
            fallback["is_conversation"] = False
            return fallback
            
    def _basic_intent_parsing(self, transcription):
        """Basic keyword-based parsing as fallback"""
        text = transcription.lower()
        
        # First check if this seems like a conversation rather than a trade
        conversation_keywords = ["what", "how", "when", "why", "tell me", "explain", 
                                "market", "opinion", "thoughts", "think", "advice",
                                "suggest", "recommend", "prediction", "forecast"]
        
        for keyword in conversation_keywords:
            if keyword in text:
                logger.info(f"Basic parsing detected conversation: {transcription}")
                return {
                    "is_conversation": True,
                    "query": transcription,
                    "action": None,
                    "ticker": None,
                    "quantity": None
                }
        
        # Default values for trade intent
        action = None
        ticker = None
        quantity = None
        
        # Find action
        if "buy" in text:
            action = "buy"
        elif "sell" in text or "sale" in text:
            action = "sell"
            
        # Common stock tickers (simplified)
        common_tickers = ["aapl", "msft", "goog", "amzn", "tsla", "fb", "meta", "nvda", "nflx", "dis"]
        words = text.split()
        
        # Find ticker - look for any word that matches a common ticker or is all caps
        for word in words:
            word = word.strip(",.!?")
            if word.lower() in common_tickers or (len(word) <= 5 and word.upper() == word and word.isalpha()):
                ticker = word.upper()
                break
                
        # Find quantity - look for numbers
        import re
        numbers = re.findall(r'\b\d+\b', text)
        if numbers:
            try:
                quantity = int(numbers[0])
            except ValueError:
                pass
                
        logger.info(f"Basic parsing found: action={action}, ticker={ticker}, quantity={quantity}")
        return {"action": action, "ticker": ticker, "quantity": quantity, "is_conversation": False}
        
    async def generate_conversation_response(self, query, user_data, market_data):
        """
        Generate a conversational response to the user's question about markets or portfolio.
        
        Parameters:
            query (str): The user's question or statement
            user_data (dict): User portfolio and preferences
            market_data (dict): Current market data and news
            
        Returns:
            str: The broker's conversational response
        """
        try:
            # If model is None, return a default response
            if self.model is None:
                logger.info("Using fallback conversation response since Gemini model is not available")
                return "The markets have been quite volatile lately. I'd recommend diversifying your portfolio. Anything specific you'd like to know?"
            
            prompt = f"""
            You are WOLF, an AI stock broker with the personality of a 1980s Wall Street broker - confident, sharp, and a bit aggressive but professional. You use period-appropriate slang, speak with energy, and have a flair for the dramatic.

            BROKER CHARACTER TRAITS:
            - Confident and direct, but not arrogant
            - Uses 80s Wall Street slang
            - Speaks in short, punchy sentences
            - Addresses the client by name
            - Is knowledgeable about markets and trading

            CLIENT INFO:
            Name: {user_data.get('name', 'buddy')}
            Portfolio value: ${user_data.get('portfolio_value', '0')}
            Cash balance: ${user_data.get('cash_balance', '0')}
            
            PORTFOLIO POSITIONS:
            {self._format_positions(user_data.get('positions', []))}
            
            CURRENT MARKET DATA:
            S&P 500: {market_data.get('sp500', 'Unknown')}
            Dow Jones: {market_data.get('dow', 'Unknown')}
            Nasdaq: {market_data.get('nasdaq', 'Unknown')}
            
            NEWS:
            {market_data.get('top_news', 'No major news today.')}
            
            Your client has asked: "{query}"
            
            Respond in your broker character with market insight, investment advice, or commentary on the question. Address them by name from the CLIENT INFO.
            Keep it concise (2-3 sentences), conversational, and engaging - like a real 1980s broker would talk on the phone.
            """
            
            response = await self.model.generate_content_async(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Error generating conversation response: {e}")
            return "Look, the markets are always changing, but your strategy shouldn't. Let's focus on building a solid portfolio with good fundamentals. What are you thinking about investing in?"
    
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
            # If model is None, use template-based response
            if self.model is None:
                logger.info("Using fallback broker response since Gemini model is not available")
                return self._template_broker_response(user_intent, trade_result)
                
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
            return self._template_broker_response(user_intent, trade_result)
            
    def _template_broker_response(self, user_intent, trade_result):
        """Generate a template-based broker response as fallback"""
        action = user_intent.get('action', 'trade')
        ticker = user_intent.get('ticker', 'that stock')
        quantity = user_intent.get('quantity', 'those shares')
        status = trade_result.get('status', 'unknown')
        
        if status == 'success':
            price = trade_result.get('price', 0)
            return f"Boom! Just {action}ed {quantity} shares of {ticker} at ${price}. You've got the Midas touch, baby!"
        else:
            error = trade_result.get('message', 'market conditions')
            return f"No dice on that {ticker} {action} due to {error}. Let's pivot and find you another killer opportunity!" 