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
            model_options = ['gemini-2.0-flash']
            
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
            # Generate a stock recommendation
            recommendation = await self.generate_stock_recommendation(user_data, market_data)
            
            # If model is None, return a default response
            if self.model is None:
                logger.info("Using fallback intro response since Gemini model is not available")
                client_name = user_data.get('name', 'buddy')
                return f"Hey {client_name}! Wolf here. The market's lookin' hot today. Your portfolio is holding steady. Listen, I've got a hot tip for you - {recommendation['action']} {recommendation['quantity']} shares of {recommendation['ticker']}. {recommendation['rationale']} What do you think? Want to pull the trigger on this deal?"
            
            # Check if we have previous call history for this user
            has_previous_calls = False
            if 'previous_calls' in user_data and user_data['previous_calls']:
                has_previous_calls = True
            
            prompt = f"""
            You are WOLF, an AI stock broker with the personality of a 1980s Wall Street broker - confident, sharp, and a bit aggressive but professional. You use period-appropriate slang, speak with energy, and have a flair for the dramatic.

            BROKER CHARACTER TRAITS:
            - Confident and direct, but not arrogant
            - Uses occasional 80s Wall Street slang like "bull market", "making a killing", "bullish", etc.
            - Speaks in short, punchy sentences
            - Always addresses the client by name (use their actual name from the data below)
            - Is knowledgeable about markets and trading
            - PROACTIVELY suggests investment opportunities
            - Mentions that client can ask for REAL-TIME STOCK PRICES anytime
            - Has perfect memory of all conversations with this client
            
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
            Has previous calls: {'Yes' if has_previous_calls else 'No'}
            
            PORTFOLIO POSITIONS:
            {self._format_positions(user_data.get('positions', []))}
            
            RECENT TRADES:
            {user_data.get('recent_trades', 'No recent trades.')}
            
            STOCK RECOMMENDATION:
            Ticker: {recommendation['ticker']}
            Action: {recommendation['action']}
            Quantity: {recommendation['quantity']}
            Rationale: {recommendation['rationale']}
            
            INSTRUCTIONS:
            1. Generate a personalized greeting that addresses the client by name
            2. Give a quick summary of the market's current state
            3. Mention one relevant news item if available
            4. Comment briefly on the client's portfolio or recent trades
            5. IMMEDIATELY pitch them the stock recommendation with excitement and confidence
            6. Mention they can ask for real-time price quotes for any stock anytime during the call
            7. Casually mention that you remember all your conversations, so they can refer to previous discussions
            8. Ask if they want to execute the trade directly (make this pushy like a real broker)
            
            Your response should be conversational, energetic, and sound like a real 1980s Wall Street broker on the phone. Keep it to 6-8 sentences maximum with a focus on selling the stock recommendation.
            """
            
            response = await self.model.generate_content_async(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Error generating broker intro: {e}")
            client_name = user_data.get('name', 'buddy')
            recommendation = await self.generate_stock_recommendation(user_data, market_data)
            return f"Hey {client_name}! Wolf here. The market's lookin' hot today. Your portfolio is holding steady. Listen, I've got a hot tip for you - {recommendation['action']} {recommendation['quantity']} shares of {recommendation['ticker']}. {recommendation['rationale']} What do you think? Want to pull the trigger on this deal?"
    
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
        Parse a user's transcription to determine if it's a trading intent or conversation.
        
        Parameters:
            transcription (str): The user's speech transcription
            
        Returns:
            dict: The parsed intent with action, ticker, quantity, and is_conversation
        """
        try:
            # First, check if the model is available
            if self.model is None:
                logger.info("Using basic intent parsing since Gemini model is not available")
                return self._basic_intent_parsing(transcription)
                
            # Use Gemini to classify whether this is a trading command or conversation
            classification_prompt = f"""
            Classify this user statement as either a TRADING intent or a CONVERSATION.
            
            TRADING intents contain:
            - A clear buy or sell action
            - A stock ticker or company name
            - Often a quantity of shares
            
            Examples of TRADING intents:
            - "Buy 10 shares of Apple"
            - "I want to sell all my Tesla stock"
            - "Let's get 5 Amazon"
            - "Can you buy me 20 shares of Google?"
            
            CONVERSATION intents are questions about markets, advice requests, or general chat.
            
            Examples of CONVERSATION intents:
            - "What do you think about the market today?"
            - "Should I be worried about inflation?"
            - "What stocks look good right now?"
            - "Tell me about my portfolio"
            
            User statement: "{transcription}"
            
            Answer with just one word: TRADING or CONVERSATION
            """
            
            classification_response = await self.model.generate_content_async(classification_prompt)
            result_type = classification_response.text.strip().upper()
            logger.info(f"Intent classification result: {result_type} for: {transcription}")
            
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
            For the ticker, convert company names like "Apple" to their symbol "AAPL", "Google" to "GOOG", etc.
            For quantity, convert word numbers like "ten" to numeric values like 10.
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
                
                # Fallback to basic parsing if any essential field is missing
                if not all([parsed_intent.get('action'), parsed_intent.get('ticker'), parsed_intent.get('quantity')]):
                    logger.warning(f"Missing fields in parsed intent: {parsed_intent}. Falling back to basic parsing.")
                    basic_result = self._basic_intent_parsing(transcription)
                    
                    # If basic parsing found values for missing fields, use those
                    if parsed_intent.get('action') is None and basic_result.get('action'):
                        parsed_intent['action'] = basic_result['action']
                    if parsed_intent.get('ticker') is None and basic_result.get('ticker'):
                        parsed_intent['ticker'] = basic_result['ticker']
                    if parsed_intent.get('quantity') is None and basic_result.get('quantity'):
                        parsed_intent['quantity'] = basic_result['quantity']
                
                return parsed_intent
            except Exception as json_err:
                logger.warning(f"Failed to parse trading intent from: {transcription}. Error: {json_err}")
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
        
        # Find action - expand to include more trading phrases
        buy_phrases = ["buy", "purchase", "get", "acquire", "long", "want to buy", "would like to buy", "pick up"]
        sell_phrases = ["sell", "sale", "dump", "get rid of", "short", "unload", "want to sell", "would like to sell"]
        
        for phrase in buy_phrases:
            if phrase in text:
                action = "buy"
                break
                
        if not action:  # Only check sell phrases if buy wasn't found
            for phrase in sell_phrases:
                if phrase in text:
                    action = "sell"
                    break
            
        # Common stock tickers (expanded list)
        common_tickers = [
            "aapl", "msft", "goog", "googl", "amzn", "tsla", "meta", "nvda", "nflx", "dis", 
            "intc", "amd", "spy", "qqq", "voo", "baba", "v", "ma", "pypl", "jpm", "wmt", "xom",
            "ko", "pep", "t", "vz", "csco", "adbe", "crm", "ibm", "gs", "ba", "tgt"
        ]
        words = text.split()
        
        # Find ticker - look for any word that matches a common ticker or is all caps
        for word in words:
            word = word.strip(",.!?")
            clean_word = ''.join(c for c in word if c.isalnum())  # Remove any special characters
            if clean_word.lower() in common_tickers or (len(clean_word) <= 5 and clean_word.upper() == clean_word and clean_word.isalpha()):
                ticker = clean_word.upper()
                break
                
        # Find quantity - look for numbers or number words
        import re
        
        # Check for numerical digits
        numbers = re.findall(r'\b\d+\b', text)
        if numbers:
            try:
                quantity = int(numbers[0])
            except ValueError:
                pass
        
        # If no numerical digits found, check for number words
        if quantity is None:
            number_words = {
                'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
                'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
                'twenty': 20, 'thirty': 30, 'forty': 40, 'fifty': 50,
                'hundred': 100, 'thousand': 1000
            }
            
            for word, value in number_words.items():
                if word in text:
                    quantity = value
                    break
                
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
            # Check if this is a price check request
            is_price_check, ticker = await self._check_for_price_query(query)
            if is_price_check and ticker:
                return await self._generate_price_check_response(ticker, user_data)
            
            # If model is None, return a default response
            if self.model is None:
                logger.info("Using fallback conversation response since Gemini model is not available")
                return "The markets have been quite volatile lately. I'd recommend diversifying your portfolio. Anything specific you'd like to know?"
            
            # Format the call transcript for context
            conversation_history = ""
            if 'call_transcript' in user_data and user_data['call_transcript']:
                conversation_history = "CONVERSATION HISTORY:\n"
                for entry in user_data['call_transcript']:
                    conversation_history += f"{entry['speaker']} ({entry['timestamp']}): {entry['content']}\n"
            
            prompt = f"""
            You are WOLF, an AI stock broker with the personality of a 1980s Wall Street broker - confident, sharp, and a bit aggressive but professional. You use period-appropriate slang, speak with energy, and have a flair for the dramatic.

            BROKER CHARACTER TRAITS:
            - Confident and direct, but not arrogant
            - Uses 80s Wall Street slang
            - Speaks in short, punchy sentences
            - Addresses the client by name
            - Is knowledgeable about markets and trading
            - Whenever appropriate, suggests they can check real-time prices
            - Has PERFECT MEMORY of the entire conversation so far
            - Answers questions with full context of what was previously discussed

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
            
            {conversation_history}
            
            Your client has just asked: "{query}"
            
            SPECIAL FEATURES:
            - If the client is asking about a stock price, YOU DON'T NEED TO ANSWER - a separate system will look up the real-time price
            - If their question isn't clearly about a specific stock price, help them with market insights
            - When mentioning stocks, remind them they can check the current price by simply asking
            - IMPORTANT: Use your memory of the conversation history - don't ask for information the client already provided!
            - Reference previous parts of the conversation when relevant
            
            Respond in your broker character with market insight, investment advice, or commentary on the question. Address them by name from the CLIENT INFO.
            Keep it concise (2-3 sentences), conversational, and engaging - like a real 1980s broker would talk on the phone.
            """
            
            response = await self.model.generate_content_async(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Error generating conversation response: {e}")
            return "Look, the markets are always changing, but your strategy shouldn't. Let's focus on building a solid portfolio with good fundamentals. What are you thinking about investing in?"
    
    async def _check_for_price_query(self, query):
        """
        Check if the query is asking for a stock price.
        
        Parameters:
            query (str): The user's query
            
        Returns:
            tuple: (is_price_check, ticker)
        """
        # Common price check patterns
        price_check_keywords = [
            "price", "worth", "trading at", "quote", "going for", 
            "how much is", "what's the price", "what is the price", 
            "how is", "where is", "current price", "stock price"
        ]
        
        query_lower = query.lower()
        is_price_check = any(keyword in query_lower for keyword in price_check_keywords)
        
        # If it looks like a price check, extract the ticker
        if is_price_check:
            # Try to extract ticker using model if available
            if self.model is not None:
                try:
                    prompt = f"""
                    Extract the stock ticker symbol from this price check query:
                    
                    Query: "{query}"
                    
                    Respond with ONLY the ticker symbol in uppercase. If there's no clear ticker, respond with "NONE".
                    If the query mentions a company name (like "Apple" or "Tesla"), convert it to the corresponding ticker (like "AAPL" or "TSLA").
                    """
                    
                    response = await self.model.generate_content_async(prompt)
                    potential_ticker = response.text.strip().upper()
                    
                    # Validate that it looks like a ticker (1-5 uppercase letters)
                    if potential_ticker != "NONE" and len(potential_ticker) <= 5 and potential_ticker.isalpha():
                        return True, potential_ticker
                        
                except Exception as e:
                    logger.warning(f"Error extracting ticker with model: {e}")
            
            # Fallback to regex-based extraction
            import re
            
            # Look for potential tickers (1-5 uppercase letters)
            ticker_matches = re.findall(r'\b[A-Z]{1,5}\b', query)
            if ticker_matches:
                return True, ticker_matches[0]
                
            # Common stock name to ticker mapping for fallback
            name_to_ticker = {
                "apple": "AAPL", "microsoft": "MSFT", "google": "GOOGL", "amazon": "AMZN", 
                "tesla": "TSLA", "facebook": "META", "meta": "META", "netflix": "NFLX", 
                "disney": "DIS", "nvidia": "NVDA", "amd": "AMD", "intel": "INTC"
            }
            
            # Check for company names
            for name, ticker in name_to_ticker.items():
                if name in query_lower:
                    return True, ticker
        
        return is_price_check, None
        
    async def _generate_price_check_response(self, ticker, user_data):
        """
        Generate a response for a stock price check.
        
        Parameters:
            ticker (str): The stock ticker
            user_data (dict): User portfolio and preferences
            
        Returns:
            str: The broker's response with the current price
        """
        # Import here to avoid circular imports
        from ..services.trading_service import TradingService
        
        trading_service = TradingService()
        
        try:
            # Get the current price
            price = await trading_service.get_stock_price(ticker)
            
            if price is None:
                return f"I couldn't get the price for {ticker} right now. The market data feed seems to be having issues. Want to check another ticker?"
            
            # Check if user owns this stock
            user_owns_stock = False
            shares_owned = 0
            avg_price = 0
            profit_loss = 0
            
            for position in user_data.get('positions', []):
                if position.get('ticker') == ticker:
                    user_owns_stock = True
                    shares_owned = position.get('quantity', 0)
                    avg_price = position.get('avg_price', 0)
                    profit_loss = ((price - avg_price) / avg_price * 100) if avg_price and avg_price > 0 else 0
                    break
            
            # Check conversation history to see if we've recently discussed this stock
            previously_discussed = False
            context_info = ""
            
            if 'call_transcript' in user_data and user_data['call_transcript']:
                # Check if we've talked about this ticker in the last few messages
                for entry in reversed(user_data['call_transcript']):
                    if ticker in entry['content'] and entry['speaker'] == 'Broker' and entry['content'] != f"What's {ticker}'s price?":
                        previously_discussed = True
                        context_info = f" As I mentioned earlier about {ticker},"
                        break
            
            # Generate a broker-style response
            if user_owns_stock:
                if profit_loss > 0:
                    return f"{ticker} is trading at ${price:.2f} right now.{context_info} You've got {shares_owned} shares at an average cost of ${avg_price:.2f}, so you're up about {profit_loss:.2f}% on this position. Nice work! Want to add to your position while it's hot?"
                else:
                    return f"{ticker} is at ${price:.2f} right now.{context_info} You've got {shares_owned} shares at an average of ${avg_price:.2f}, so you're down about {abs(profit_loss):.2f}%. Could be a buying opportunity if you want to average down. What do you think?"
            else:
                # Check market momentum for extra color
                market_momentum = "bullish" if abs(hash(ticker)) % 2 == 0 else "showing some weakness"  # Just random for demo
                return f"{ticker} is currently trading at ${price:.2f}.{context_info} The stock is looking {market_momentum} today. You don't have any position in this one yet - want to grab some shares?"
                
        except Exception as e:
            logger.error(f"Error generating price check response: {e}")
            return f"I tried to get the latest quote on {ticker}, but our data feed is acting up. Let me know if you want to check another stock or discuss some trading ideas."
    
    async def generate_broker_response(self, user_intent, trade_result, user_data=None):
        """
        Generate the broker's response after a trade is executed or rejected.
        
        Parameters:
            user_intent (dict): The parsed user intent
            trade_result (dict): The result of the trade execution
            user_data (dict, optional): User data including conversation history
            
        Returns:
            str: The broker's response
        """
        try:
            # If model is None, use template-based response
            if self.model is None:
                logger.info("Using fallback broker response since Gemini model is not available")
                return self._template_broker_response(user_intent, trade_result)
                
            status = trade_result.get('status', 'unknown')
            
            # Format conversation history if available
            conversation_context = ""
            if user_data and 'call_transcript' in user_data and user_data['call_transcript']:
                conversation_context = "CONVERSATION HISTORY (RELEVANT EXCERPTS):\n"
                # Find up to 3 most recent exchanges related to this ticker
                ticker = user_intent.get('ticker', '')
                related_messages = []
                
                for entry in reversed(user_data['call_transcript']):
                    if ticker in entry['content'] and len(related_messages) < 3:
                        related_messages.append(f"{entry['speaker']} ({entry['timestamp']}): {entry['content']}")
                
                if related_messages:
                    conversation_context += "\n".join(reversed(related_messages)) + "\n\n"
                else:
                    conversation_context = ""  # No relevant history found
            
            prompt = f"""
            You are a retro 1980s Wall Street stockbroker named Wolf. Generate a brief, energetic response to your client after:
            
            {conversation_context}
            - They wanted to {user_intent.get('action')} {user_intent.get('quantity')} shares of {user_intent.get('ticker')}
            - The trade status was: {status}
            
            If the trade was successful, mention the new price (${trade_result.get('price', 'unknown')}) and be congratulatory.
            If it failed, explain briefly why in a sympathetic but upbeat way.
            
            If this is a stock they've previously discussed or traded, reference that fact in your response.
            
            Keep it to 1-2 short sentences and make it sound like a 1980s Wall Street broker (casual, slang, energetic).
            """
            
            response = await self.model.generate_content_async(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Error generating broker response: {e}")
            return self._template_broker_response(user_intent, trade_result)
    
    async def generate_trading_order(self, transcription):
        """
        Generate a trading order directly using Gemini.
        This is a simplified approach that directly generates JSON.
        
        Parameters:
            transcription (str): The user's speech transcription
            
        Returns:
            dict: The trading order with action, ticker, and quantity
        """
        try:
            # If model is None, fall back to basic parsing
            if self.model is None:
                logger.info("Using basic parsing since Gemini model is not available")
                return self._basic_intent_parsing(transcription)
            
            prompt = f"""
            Your task is to extract trading order details from the user's message.
            
            User message: "{transcription}"
            
            If this is a trading order, respond with a JSON object containing:
            - action: "buy" or "sell"
            - ticker: the stock symbol (convert company names to symbols, e.g., "Apple" to "AAPL")
            - quantity: the number of shares as an integer
            
            If this is NOT a trading order (e.g., it's a question or conversation), respond with:
            {{"is_conversation": true, "query": "{transcription}"}}
            
            Only respond with valid JSON - no explanations or other text.
            """
            
            response = await self.model.generate_content_async(prompt)
            response_text = response.text.strip()
            
            # Try to parse the response as JSON
            try:
                import json
                import re
                
                # Extract JSON pattern from the response if it's not a clean JSON
                json_pattern = r'\{.*\}'
                json_match = re.search(json_pattern, response_text, re.DOTALL)
                
                if json_match:
                    json_str = json_match.group(0)
                    parsed_order = json.loads(json_str)
                    
                    # If it's a conversation, return as is
                    if parsed_order.get('is_conversation'):
                        return parsed_order
                    
                    # For trading orders, ensure all fields are present
                    if all([parsed_order.get('action'), parsed_order.get('ticker'), parsed_order.get('quantity')]):
                        # Make sure action is lowercase
                        parsed_order['action'] = parsed_order['action'].lower()
                        # Make sure ticker is uppercase
                        parsed_order['ticker'] = parsed_order['ticker'].upper()
                        # Make sure quantity is an integer
                        parsed_order['quantity'] = int(parsed_order['quantity'])
                        # Add is_conversation flag
                        parsed_order['is_conversation'] = False
                        
                        logger.info(f"Successfully generated trading order: {parsed_order}")
                        return parsed_order
                
                # If JSON parsing failed or required fields missing, fall back to basic parsing
                logger.warning(f"Failed to parse valid trading order from Gemini response: {response_text}")
                return self._basic_intent_parsing(transcription)
                
            except Exception as e:
                logger.warning(f"Error parsing Gemini trading order response: {e}")
                return self._basic_intent_parsing(transcription)
                
        except Exception as e:
            logger.error(f"Error generating trading order: {e}")
            return self._basic_intent_parsing(transcription)
            
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
            
    async def generate_stock_recommendation(self, user_data, market_data):
        """
        Generate a proactive stock recommendation like a real broker would.
        
        Parameters:
            user_data (dict): User portfolio and preferences
            market_data (dict): Current market data and news
            
        Returns:
            dict: A recommendation with ticker, action, rationale, and suggested quantity
        """
        try:
            # If model is None, return a default recommendation
            if self.model is None:
                logger.info("Using fallback stock recommendation since Gemini model is not available")
                return {
                    "ticker": "AAPL",
                    "action": "buy",
                    "quantity": 10,
                    "rationale": "Apple's looking strong with the new product lineup. I'd recommend grabbing some shares before the next earnings call."
                }
            
            prompt = f"""
            You are WOLF, an aggressive 1980s Wall Street stockbroker. Generate a proactive stock recommendation for your client.
            
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
            
            Generate a stock recommendation with the following:
            1. A specific ticker symbol for a well-known company
            2. Whether to buy or sell
            3. A suggested quantity (should be affordable based on their cash balance)
            4. A brief, persuasive rationale for the recommendation
            
            Format the response as a JSON object with these fields:
            - ticker: The stock symbol in uppercase
            - action: Either "buy" or "sell"
            - quantity: A reasonable number of shares to trade
            - rationale: A brief, persuasive explanation (1-2 sentences)
            
            Only provide the JSON - no additional text.
            """
            
            response = await self.model.generate_content_async(prompt)
            response_text = response.text.strip()
            
            # Try to parse the response as JSON
            try:
                import json
                import re
                
                # Extract JSON pattern from the response if it's not a clean JSON
                json_pattern = r'\{.*\}'
                json_match = re.search(json_pattern, response_text, re.DOTALL)
                
                if json_match:
                    json_str = json_match.group(0)
                    recommendation = json.loads(json_str)
                    
                    # Validate and format the recommendation
                    if all([recommendation.get('ticker'), recommendation.get('action'), 
                           recommendation.get('quantity'), recommendation.get('rationale')]):
                        # Ensure proper formatting
                        recommendation['ticker'] = recommendation['ticker'].upper()
                        recommendation['action'] = recommendation['action'].lower()
                        recommendation['quantity'] = int(recommendation['quantity'])
                        
                        logger.info(f"Generated stock recommendation: {recommendation}")
                        return recommendation
            
                # If something went wrong, use fallback
                logger.warning(f"Failed to generate valid recommendation, using fallback")
            except Exception as e:
                logger.warning(f"Error parsing recommendation JSON: {e}")
            
            # Fallback recommendation
            return {
                "ticker": "AAPL",
                "action": "buy",
                "quantity": 10,
                "rationale": "Apple's looking strong with the new product lineup. I'd recommend grabbing some shares before the next earnings call."
            }
            
        except Exception as e:
            logger.error(f"Error generating stock recommendation: {e}")
            return {
                "ticker": "AAPL",
                "action": "buy",
                "quantity": 10,
                "rationale": "Apple's looking strong with the new product lineup. I'd recommend grabbing some shares before the next earnings call."
            } 