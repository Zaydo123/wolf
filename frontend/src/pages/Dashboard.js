import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import styled from 'styled-components';
import axios from 'axios';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

const DashboardContainer = styled.div`
  display: grid;
  grid-template-columns: 1fr 2fr;
  gap: 2rem;
  
  @media (max-width: 768px) {
    grid-template-columns: 1fr;
  }
`;

const SidePanel = styled.div`
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
`;

const MainPanel = styled.div`
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
`;

const Card = styled.div`
  background-color: rgba(0, 0, 0, 0.8);
  border: 1px solid var(--primary);
  border-radius: 4px;
  padding: 1.5rem;
  box-shadow: 0 0 15px rgba(57, 255, 20, 0.3);
`;

const PortfolioValue = styled.div`
  font-size: 2.5rem;
  color: var(--primary);
  margin: 1rem 0;
  text-shadow: 0 0 10px var(--primary);
`;

const MarketCard = styled(Card)`
  border-color: var(--accent);
  box-shadow: 0 0 15px rgba(0, 255, 255, 0.3);
`;

const StockItem = styled.div`
  display: flex;
  justify-content: space-between;
  padding: 0.5rem 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  
  &:last-child {
    border-bottom: none;
  }
`;

const TradeHistory = styled.div`
  max-height: 300px;
  overflow-y: auto;
  margin-top: 1rem;
`;

const TradeItem = styled.div`
  display: flex;
  justify-content: space-between;
  padding: 0.75rem 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  
  &:last-child {
    border-bottom: none;
  }
`;

const Button = styled.button`
  align-self: center;
  margin-top: 1rem;
`;

const PriceUp = styled.span`
  color: var(--success);
`;

const PriceDown = styled.span`
  color: var(--warning);
`;

const LoadingContainer = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 50vh;
`;

const Dashboard = ({ socket }) => {
  const { user } = useAuth();
  const [portfolio, setPortfolio] = useState(null);
  const [marketSummary, setMarketSummary] = useState(null);
  const [tradeHistory, setTradeHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
  
  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        setLoading(true);
        
        // Fetch portfolio data
        const portfolioRes = await axios.get(`${API_URL}/api/trades/portfolio/${user.id}`);
        setPortfolio(portfolioRes.data);
        
        // Fetch market summary
        const marketRes = await axios.get(`${API_URL}/api/trades/market/summary`);
        setMarketSummary(marketRes.data);
        
        // Fetch trade history
        const historyRes = await axios.get(`${API_URL}/api/trades/history/${user.id}?limit=10`);
        setTradeHistory(historyRes.data.trades);
        
        setLoading(false);
      } catch (err) {
        console.error('Error fetching dashboard data:', err);
        setError('Failed to load dashboard data. Please try again later.');
        setLoading(false);
      }
    };
    
    fetchDashboardData();
    
    // Set up WebSocket listeners for real-time updates
    if (socket) {
      socket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        
        if (data.type === 'trade_executed' && data.user_id === user.id) {
          // Update trade history with the new trade
          setTradeHistory(prev => [data.trade, ...prev].slice(0, 10));
          
          // Refresh portfolio data
          axios.get(`${API_URL}/api/trades/portfolio/${user.id}`)
            .then(res => setPortfolio(res.data))
            .catch(err => console.error('Error refreshing portfolio:', err));
        }
      };
    }
    
    return () => {
      if (socket) {
        socket.onmessage = null;
      }
    };
  }, [API_URL, user, socket]);
  
  const handleInitiateCall = async () => {
    try {
      await axios.post(`${API_URL}/api/calls/initiate/${user.id}`);
      alert('Call initiated! You will receive a phone call shortly.');
    } catch (err) {
      console.error('Error initiating call:', err);
      alert('Failed to initiate call. Please try again later.');
    }
  };
  
  if (loading) {
    return (
      <LoadingContainer>
        <div className="loading">
          <div></div>
          <div></div>
          <div></div>
        </div>
        <p>Loading dashboard data...</p>
      </LoadingContainer>
    );
  }
  
  if (error) {
    return <div>{error}</div>;
  }
  
  // Generate chart data
  const chartData = portfolio?.positions?.map(position => ({
    name: position.ticker,
    value: position.value,
    pv: position.value
  })) || [];
  
  return (
    <div>
      <h1>DASHBOARD</h1>
      
      <DashboardContainer>
        <SidePanel>
          <Card>
            <h3>PORTFOLIO VALUE</h3>
            <PortfolioValue>${portfolio?.portfolio_value?.toLocaleString()}</PortfolioValue>
            <p>Cash Balance: ${portfolio?.cash_balance?.toLocaleString()}</p>
            
            <Button onClick={handleInitiateCall}>
              CALL MY BROKER
            </Button>
          </Card>
          
          <MarketCard>
            <h3>MARKET SUMMARY</h3>
            {marketSummary && (
              <>
                <StockItem>
                  <span>S&P 500</span>
                  <span>{marketSummary.sp500}</span>
                </StockItem>
                <StockItem>
                  <span>DOW JONES</span>
                  <span>{marketSummary.dow}</span>
                </StockItem>
                <StockItem>
                  <span>NASDAQ</span>
                  <span>{marketSummary.nasdaq}</span>
                </StockItem>
              </>
            )}
          </MarketCard>
        </SidePanel>
        
        <MainPanel>
          <Card>
            <h3>HOLDINGS</h3>
            {portfolio?.positions?.length > 0 ? (
              <>
                <div style={{ width: '100%', height: 200, marginBottom: '1rem' }}>
                  <ResponsiveContainer>
                    <LineChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(57, 255, 20, 0.2)" />
                      <XAxis dataKey="name" stroke="var(--text)" />
                      <YAxis stroke="var(--text)" />
                      <Tooltip contentStyle={{ backgroundColor: 'var(--background)' }} />
                      <Line type="monotone" dataKey="value" stroke="var(--primary)" activeDot={{ r: 8 }} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
                {portfolio.positions.map((position, index) => (
                  <StockItem key={index}>
                    <div>
                      <strong>{position.ticker}</strong> ({position.quantity} shares)
                    </div>
                    <div>
                      ${position.current_price} 
                      {position.profit_loss >= 0 ? (
                        <PriceUp> (▲ {position.profit_loss.toFixed(2)}%)</PriceUp>
                      ) : (
                        <PriceDown> (▼ {Math.abs(position.profit_loss).toFixed(2)}%)</PriceDown>
                      )}
                    </div>
                  </StockItem>
                ))}
              </>
            ) : (
              <p>No holdings in your portfolio.</p>
            )}
          </Card>
          
          <Card>
            <h3>RECENT TRADES</h3>
            {tradeHistory.length > 0 ? (
              <TradeHistory>
                {tradeHistory.map((trade, index) => (
                  <TradeItem key={index}>
                    <div>
                      <strong>{trade.action.toUpperCase()}</strong> {trade.quantity} {trade.ticker}
                    </div>
                    <div>
                      ${trade.price} (${trade.total_value.toFixed(2)})
                    </div>
                  </TradeItem>
                ))}
              </TradeHistory>
            ) : (
              <p>No recent trades.</p>
            )}
          </Card>
        </MainPanel>
      </DashboardContainer>
    </div>
  );
};

export default Dashboard; 