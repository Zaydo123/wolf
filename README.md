# Wolf Trading Platform

A modern trading platform with a retro twist. Wolf combines real-time market data with an innovative phone calling system, allowing users to receive market updates and trade notifications through actual voice calls. The platform features a unique retro-terminal interface while leveraging cutting-edge technologies for real-time trading capabilities.

## Key Features

- **Voice Calling Integration**: Receive market updates and trade notifications through actual phone calls
- **Real-Time Trading**: Paper trading with live market data
- **Portfolio Management**: Track positions, profits, and trade history
- **Live Market Data**: Real-time stock prices and market indicators
- **AI Trading Assistant**: Powered by Google's Gemini for market analysis
- **News Aggregation**: Live financial news from major sources
- **Retro UI**: Nostalgic terminal-style interface with modern functionality

## Technology Stack

### Frontend Technologies
- **React.js** (v18.2.0) - Core frontend framework
- **Styled Components** (v6.0.7) - Styling and UI components
- **React Router DOM** (v6.15.0) - Navigation and routing
- **Recharts** (v2.8.0) - Interactive charts
- **Axios** (v1.5.0) - HTTP client

### Backend Technologies
- **FastAPI** (v0.103.1) - High-performance API framework
- **Uvicorn** (v0.23.2) - ASGI server
- **Pydantic** (v2.3.0) - Data validation
- **WebSockets** (v11.0.3) - Real-time updates
- **HTTPX** (v0.24.1) - Async HTTP client
- **AsyncPG** (v0.30.0) - Async PostgreSQL

### Database & Authentication
- **Supabase** (v2.3.0 Python, v2.33.1 JS) - Database and auth
- **PostgreSQL** - Primary database
- **Python-Jose** (v3.3.0) - JWT handling

### External Services Integration
- **Twilio** (v8.5.0) - Phone calling system
- **Google Generative AI** (v0.3.1) - AI assistant
- **ElevenLabs** (v1.3.0) - Voice synthesis ( Unused but in code for future reference)
- **Alpha Vantage** - Market data APIs

### Data Processing & Utilities
- **YFinance** (v0.2.36) - Yahoo Finance data
- **Feedparser** (v6.0.10) - RSS feed processing
- **Python-Multipart** (v0.0.6) - Form data handling
- **Python-Dotenv** (v1.0.0) - Environment management
- **Tenacity** (v8.2.3) - Retry handling
- **AIOHTTP** (v3.9.5) - Async HTTP

## Getting Started

1. Clone the repository
2. Set up environment variables (see `.env.example`)
3. Install dependencies:
   ```bash
   # Backend
   cd backend
   pip install -r requirements.txt

   # Frontend
   cd frontend
   npm install
   ```
4. Start the services:
   ```bash
   # Backend
   cd backend
   uvicorn app.main:app --reload

   # Frontend
   cd frontend
   npm start
   ```

## Environment Variables Required

- `SUPABASE_URL` - Supabase project URL
- `SUPABASE_KEY` - Supabase project key
- `TWILIO_ACCOUNT_SID` - Twilio account identifier
- `TWILIO_AUTH_TOKEN` - Twilio authentication token
- `ALPHA_VANTAGE_API_KEY` - Alpha Vantage API key
- `GEMINI_API_KEY` - Google Gemini API key
- `ELEVENLABS_API_KEY` - ElevenLabs API key
