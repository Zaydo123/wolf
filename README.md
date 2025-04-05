# Wolf - Retro AI Stockbroker Paper Trading Platform

A retro-styled paper trading platform inspired by "The Wolf of Wall Street" where users receive AI-powered phone calls simulating conversations with a human stockbroker. Users can trade stocks using natural voice commands over the phone, providing a unique and engaging paper trading experience.

## Key Features

- **AI-Powered Voice Calls**: Receive automated calls from your AI stockbroker at market open, mid-day, or close
- **Voice Trading**: Make trades using natural language over the phone (e.g., "Buy 5 shares of Apple")
- **Retro UI**: Experience the nostalgic feel of 80s/90s trading with a retro-styled interface
- **Real-time Updates**: Watch your portfolio update in real-time via WebSockets
- **Paper Trading**: Practice trading without risking real money

## Tech Stack

- **Frontend**: React.js with WebSocket support
- **Backend**: FastAPI with REST + WebSocket API
- **Database**: Supabase (PostgreSQL)
- **Voice System**: Twilio Programmable Voice
- **AI/NLP**: Google Gemini for AI conversations and intent parsing
- **Stock Data**: Yahoo Finance (yfinance library)

## Project Structure

```
├── backend/                 # FastAPI backend
│   ├── app/                 # Application code
│   │   ├── api/             # API endpoints
│   │   ├── core/            # Core configuration
│   │   ├── db/              # Database connections
│   │   ├── services/        # Business logic services
│   │   └── schemas/         # Pydantic models
│   ├── requirements.txt     # Python dependencies
│   └── schema.sql           # Supabase schema
├── frontend/                # React.js frontend
│   ├── public/              # Static files
│   ├── src/                 # Source code
│   │   ├── components/      # React components
│   │   ├── context/         # React context (auth, etc.)
│   │   ├── hooks/           # Custom React hooks
│   │   ├── pages/           # Page components
│   │   ├── services/        # API services
│   │   ├── styles/          # CSS styles
│   │   └── utils/           # Utility functions
│   └── package.json         # Node.js dependencies
└── README.md                # Project documentation
```

## Getting Started

### Prerequisites

- Node.js (v14+)
- Python (v3.9+)
- Supabase account
- Twilio account
- Google API key (for Gemini)

### Option 1: Running with Docker

The easiest way to run the application is using Docker and Docker Compose:

1. Clone the repository:
   ```
   git clone <repository-url>
   cd wolf
   ```

2. Create a `.env` file in the root directory with your credentials:
   ```
   # Copy the example env file
   cp backend/.env.example .env
   
   # Edit the .env file with your credentials
   nano .env
   ```

3. Build and start the containers:
   ```
   docker-compose up -d
   ```

4. Access the application:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

### Option 2: Manual Setup

#### Backend Setup

1. Navigate to the backend directory:
   ```
   cd backend
   ```

2. Create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Copy the environment example and update with your credentials:
   ```
   cp .env.example .env
   ```

5. Run the backend:
   ```
   uvicorn app.main:app --reload
   ```

#### Frontend Setup

1. Navigate to the frontend directory:
   ```
   cd frontend
   ```

2. Install dependencies:
   ```
   npm install
   ```

3. Create a `.env` file with your environment variables:
   ```
   REACT_APP_API_URL=http://localhost:8000
   REACT_APP_WS_URL=ws://localhost:8000/ws
   REACT_APP_SUPABASE_URL=your_supabase_url
   REACT_APP_SUPABASE_KEY=your_supabase_anon_key
   ```

4. Run the frontend:
   ```
   npm start
   ```

### Database Setup

1. Create a new Supabase project
2. Run the SQL commands from `backend/schema.sql` in the Supabase SQL Editor

## Call Experience

1. User receives a call or initiates a call from the dashboard
2. The AI broker provides a personalized market update based on the user's portfolio and market conditions
3. User can speak naturally to make trades ("Buy 10 shares of Tesla")
4. The AI processes the request and executes the paper trade
5. Real-time updates appear on the dashboard showing the executed trade and updated portfolio

## License

This project is for demonstration purposes only and not intended for production use without further development and security considerations.

## Acknowledgments

- Inspired by "The Wolf of Wall Street"
- Built as a hackathon project 