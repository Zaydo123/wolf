import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import styled from 'styled-components';
import axios from 'axios';
import { postData } from '../utils/apiUtils';
import '../styles/Portfolio.css'; // Import for retro terminal styles
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

const LoadingIndicator = styled.span`
  display: inline-flex;
  align-items: center;
  
  .dot {
    width: 8px;
    height: 8px;
    margin: 0 2px;
    background-color: var(--primary);
    border-radius: 50%;
    display: inline-block;
    animation: dot-pulse 1.5s infinite ease-in-out;
  }
  
  .dot:nth-child(2) {
    animation-delay: 0.2s;
  }
  
  .dot:nth-child(3) {
    animation-delay: 0.4s;
  }
  
  @keyframes dot-pulse {
    0%, 80%, 100% { 
      transform: scale(0.8);
      opacity: 0.5;
    }
    40% { 
      transform: scale(1.2);
      opacity: 1;
    }
  }
`;

const Dashboard = ({ socket }) => {
  const { user } = useAuth();
  const [portfolio, setPortfolio] = useState(null);
  const [marketSummary, setMarketSummary] = useState(null);
  const [tradeHistory, setTradeHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [marketDataLoading, setMarketDataLoading] = useState(false);
  const [lastUpdated, setLastUpdated] = useState(new Date());
  
  const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
  
  // Add the useRef and useEffect for automatic refresh
  const marketDataInitialized = React.useRef(false);
  
  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        setLoading(true);
        setError(null);
        
        // Always fetch fresh data - no caching
        const portfolioRes = await axios.get(`${API_URL}/api/trades/portfolio/${user.id}?fresh=true`);
        setPortfolio(portfolioRes.data);
        
        // Fetch market summary with fresh data and handle any potential errors
        try {
          const marketRes = await axios.get(`${API_URL}/api/trades/market/summary?fresh=true`);
          console.log("Market data response:", marketRes.data);
          
          // Check if market data is valid before setting state
          if (marketRes.data && 
              typeof marketRes.data === 'object' && 
              'sp500' in marketRes.data) {
            setMarketSummary(marketRes.data);
            console.log("Market data set successfully:", marketRes.data);
          } else if (marketRes.data && 'trades' in marketRes.data) {
            // Server is returning trades array instead of market data
            console.error("Received trades instead of market data:", marketRes.data);
            
            // Set error state for market data instead of fallbacks
            setMarketSummary({
              sp500: "ERROR: API RETURNED TRADES DATA",
              dow: "ERROR: API RETURNED TRADES DATA",
              nasdaq: "ERROR: API RETURNED TRADES DATA",
              error: true
            });
          } else {
            console.error("Invalid market data format:", marketRes.data);
            
            // Set error state for market data
            setMarketSummary({
              sp500: "ERROR: INVALID FORMAT",
              dow: "ERROR: INVALID FORMAT",
              nasdaq: "ERROR: INVALID FORMAT",
              error: true
            });
          }
        } catch (marketErr) {
          console.error("Error fetching market data:", marketErr);
          
          // Set error state for market data
          setMarketSummary({
            sp500: `ERROR: ${marketErr.message || 'FETCH FAILED'}`,
            dow: `ERROR: ${marketErr.message || 'FETCH FAILED'}`,
            nasdaq: `ERROR: ${marketErr.message || 'FETCH FAILED'}`,
            error: true
          });
        }
        
        // Fetch trade history - get up to 10 trades to fill the retro terminal
        const historyRes = await axios.get(`${API_URL}/api/trades/history/${user.id}?limit=10`);
        console.log("Trade history response:", historyRes.data);
        setTradeHistory(historyRes.data.trades || []);
        console.log(`Loaded ${historyRes.data.trades?.length || 0} recent trades from database`);
        
        // Debug timestamp handling - check how timestamps are formatted
        if (historyRes.data.trades && historyRes.data.trades.length > 0) {
          const sampleTrade = historyRes.data.trades[0];
          console.log("Sample trade data:", sampleTrade);
          console.log("Trade timestamp type:", typeof sampleTrade.timestamp);
          console.log("Parsed timestamp:", new Date(sampleTrade.timestamp));
        }
        
        // Update last updated timestamp
        setLastUpdated(new Date());
        
        setLoading(false);
      } catch (err) {
        console.error('Error fetching dashboard data:', err);
        if (err.response?.status === 404) {
          setError('User not found. Please try logging out and back in.');
        } else {
          setError('Failed to load dashboard data. Please try again later.');
        }
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
  
  // Add a new useEffect to refresh market data after initial loading
  useEffect(() => {
    // If market summary is missing values or contains "Unknown" values, refresh it
    if (marketSummary) {
      const hasUnknownValues = 
        marketSummary.sp500?.includes('Unknown') || 
        marketSummary.dow?.includes('Unknown') || 
        marketSummary.nasdaq?.includes('Unknown');
      
      // Only refresh if we haven't done it yet and there are unknown values
      if (!marketDataInitialized.current && hasUnknownValues) {
        // Set the flag to prevent repeated refreshes
        marketDataInitialized.current = true;
        
        console.log('Auto-refreshing market data due to missing values:', marketSummary);
        
        // Wait a moment and then refresh the market data
        const timer = setTimeout(() => {
          refreshMarketData();
        }, 2000);
        
        return () => clearTimeout(timer);
      }
    }
  }, [marketSummary]);
  
  const handleInitiateCall = async () => {
    try {
      // Show status message to user
      setLoading(true);
      
      if (!user || !user.id) {
        alert("User information not available. Please try logging in again.");
        setLoading(false);
        return;
      }
      
      // Initiate the call - Reverted to include user.id in path
      const response = await axios.post(`${API_URL}/api/calls/initiate/${user.id}`);
      
      // Show success message
      alert('Call initiated! You will receive a phone call shortly.');
      
    } catch (err) {
      console.error('Error initiating call:', err);
      
      // Provide specific error messages based on the HTTP error
      if (err.response) {
        if (err.response.status === 404) {
          alert('User not found. Please make sure you are registered correctly.');
        } else if (err.response.status === 400) {
          alert(`Error: ${err.response.data.detail}`);
        } else if (err.response.status === 500) {
          alert(`Server error: ${err.response.data.detail}`);
        } else {
          alert('Failed to initiate call. Please try again later.');
        }
      } else {
        alert('Failed to initiate call. Please try again later.');
      }
    } finally {
      setLoading(false);
    }
  };
  
  // Add a separate function to refresh market data
  const refreshMarketData = async () => {
    try {
      setMarketDataLoading(true);
      console.log('Refreshing market data with fresh=true');
      
      // Explicitly use the fresh=true parameter to bypass any caching
      const marketRes = await axios.get(`${API_URL}/api/trades/market/summary?fresh=true`);
      
      if (marketRes.data && typeof marketRes.data === 'object') {
        if ('sp500' in marketRes.data) {
          console.log('Market data refreshed successfully:', marketRes.data);
          setMarketSummary(marketRes.data);
        } else if ('trades' in marketRes.data) {
          // Server is returning trades array instead of market data
          console.error("Received trades instead of market data:", marketRes.data);
          
          // Set error state for market data
          setMarketSummary({
            sp500: "ERROR: API RETURNED TRADES DATA",
            dow: "ERROR: API RETURNED TRADES DATA",
            nasdaq: "ERROR: API RETURNED TRADES DATA",
            error: true
          });
        } else {
          console.error('Invalid market data format received:', marketRes.data);
          
          // Set error state for market data
          setMarketSummary({
            sp500: "ERROR: INVALID FORMAT",
            dow: "ERROR: INVALID FORMAT",
            nasdaq: "ERROR: INVALID FORMAT",
            error: true
          });
        }
      } else {
        console.error('Invalid market data format received:', marketRes.data);
        
        // Set error state for market data
        setMarketSummary({
          sp500: "ERROR: INVALID RESPONSE",
          dow: "ERROR: INVALID RESPONSE",
          nasdaq: "ERROR: INVALID RESPONSE",
          error: true
        });
      }
      
      // Update last updated timestamp after refresh
      setLastUpdated(new Date());
      
      setMarketDataLoading(false);
    } catch (err) {
      console.error('Error refreshing market data:', err);
      
      // Set error state for market data
      setMarketSummary({
        sp500: `ERROR: ${err.message || 'FETCH FAILED'}`,
        dow: `ERROR: ${err.message || 'FETCH FAILED'}`,
        nasdaq: `ERROR: ${err.message || 'FETCH FAILED'}`,
        error: true
      });
      
      setMarketDataLoading(false);
    }
  };
  
  // Modify the renderStockValue function to format index values
  const renderStockValue = (value) => {
    // If value is undefined or empty, show loading indicator
    if (!value) {
      console.log(`Market value loading: "${value}"`);
      return (
        <LoadingIndicator>
          <span className="dot"></span>
          <span className="dot"></span>
          <span className="dot"></span>
        </LoadingIndicator>
      );
    }
    
    // If value contains "ERROR", show error styling
    if (value.includes('ERROR')) {
      console.log(`Market value error: "${value}"`);
      return <span style={{ color: 'var(--warning)' }}>{value}</span>;
    }
    
    console.log(`Rendering market value: "${value}"`);
    
    // Check if the value contains a percentage
    if (value.includes('(')) {
      const [price, percentPart] = value.split(' (');
      const percent = parseFloat(percentPart);
      
      if (!isNaN(percent)) {
        if (percent > 0) {
          return <span>{price} <PriceUp>(▲ {percentPart}</PriceUp></span>
        } else if (percent < 0) {
          return <span>{price} <PriceDown>(▼ {percentPart.replace('-', '')}</PriceDown></span>
        } else {
          return <span>{price} ({percentPart}</span>
        }
      }
    }
    
    return <span>{value}</span>;
  };
  
  // Add debug logging for trade history fetch
  const fetchTradeHistory = React.useCallback(async () => {
    try {
      console.log('Fetching trade history for user:', user.id);
      const response = await axios.get(`${API_URL}/api/trades/history/${user.id}?limit=10`);
      console.log('Trade history response:', response.data);
      
      if (response.data && Array.isArray(response.data.trades)) {
        console.log('Setting trade history:', response.data.trades);
        setTradeHistory(response.data.trades);
      } else {
        console.error('Invalid trade history format:', response.data);
        setTradeHistory([]);
      }
    } catch (err) {
      console.error('Error fetching trade history:', err);
      setTradeHistory([]);
    }
  }, [API_URL, user?.id]);

  // Use effect to fetch trade history and set up socket listener
  useEffect(() => {
    if (user?.id) {
      console.log('User ID available, fetching trade history...');
      fetchTradeHistory();

      // Set up socket listener for trade updates
      if (socket) {
        console.log('Setting up socket listener for trade updates');
        socket.onmessage = (event) => {
          const data = JSON.parse(event.data);
          console.log('Socket message received:', data);
          
          if (data.type === 'trade_executed' && data.user_id === user.id) {
            console.log('Trade executed for current user, refreshing history...');
            fetchTradeHistory();
          }
        };
      }
    }

    // Cleanup socket listener
    return () => {
      if (socket) {
        socket.onmessage = null;
      }
    };
  }, [user?.id, socket, fetchTradeHistory]);
  
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
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
              <span>MARKET DATA</span>
              <Button 
                onClick={refreshMarketData}
                disabled={marketDataLoading}
                style={{ padding: '0.25rem 0.5rem', fontSize: '0.8rem' }}
              >
                {marketDataLoading ? 'REFRESHING...' : 'REFRESH'}
              </Button>
            </div>
            
            <div style={{ fontSize: '0.7rem', marginBottom: '0.5rem', color: '#888' }}>
              Last updated: {lastUpdated.toLocaleTimeString()}
            </div>
            
            {marketSummary ? (
              <>
                <StockItem>
                  <span>S&P 500</span>
                  <span>{renderStockValue(marketSummary.sp500)}</span>
                </StockItem>
                <StockItem>
                  <span>DOW JONES</span>
                  <span>{renderStockValue(marketSummary.dow)}</span>
                </StockItem>
                <StockItem>
                  <span>NASDAQ</span>
                  <span>{renderStockValue(marketSummary.nasdaq)}</span>
                </StockItem>
              </>
            ) : (
              <>
                <StockItem>
                  <span>S&P 500</span>
                  <LoadingIndicator>
                    <span className="dot"></span>
                    <span className="dot"></span>
                    <span className="dot"></span>
                  </LoadingIndicator>
                </StockItem>
                <StockItem>
                  <span>DOW JONES</span>
                  <LoadingIndicator>
                    <span className="dot"></span>
                    <span className="dot"></span>
                    <span className="dot"></span>
                  </LoadingIndicator>
                </StockItem>
                <StockItem>
                  <span>NASDAQ</span>
                  <LoadingIndicator>
                    <span className="dot"></span>
                    <span className="dot"></span>
                    <span className="dot"></span>
                  </LoadingIndicator>
                </StockItem>
              </>
            )}
          </MarketCard>
          
          {/* Add News Card */}
          <Card>
            <h3>NEWS</h3>
            <div style={{ maxHeight: '150px', overflow: 'auto', fontSize: '0.85rem' }}>
              {marketSummary && marketSummary.top_news ? (
                marketSummary.top_news.split('\n').map((item, index) => (
                  <div key={index} style={{ marginBottom: '0.5rem' }}>
                    • {item}
                  </div>
                ))
              ) : (
                <LoadingIndicator>
                  <span className="dot"></span>
                  <span className="dot"></span>
                  <span className="dot"></span>
                </LoadingIndicator>
              )}
            </div>
          </Card>
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
            {tradeHistory && tradeHistory.length > 0 ? (
              <div className="retro-terminal">
                <div className="terminal-header">
                  <div className="terminal-title">TRADE HISTORY</div>
                  <div className="terminal-controls">
                    <span className="control"></span>
                    <span className="control"></span>
                    <span className="control"></span>
                  </div>
                </div>
                <table className="trades-table">
                  <thead>
                    <tr>
                      <th>DATE</th>
                      <th>TICKER</th>
                      <th>ACTION</th>
                      <th>QTY</th>
                      <th>PRICE</th>
                      <th>TOTAL</th>
                    </tr>
                  </thead>
                  <tbody>
                    {tradeHistory.map((trade, index) => (
                      <tr key={trade.id || index} className={`trade-row ${trade.action}`}>
                        <td>{new Date(trade.timestamp).toLocaleString()}</td>
                        <td>{trade.ticker}</td>
                        <td className={trade.action === 'buy' ? 'buy-action' : 'sell-action'}>
                          {trade.action.toUpperCase()}
                        </td>
                        <td>{trade.quantity}</td>
                        <td>${trade.price.toFixed(2)}</td>
                        <td>${trade.total_value.toFixed(2)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="retro-terminal">
                <div className="terminal-header">
                  <div className="terminal-title">TRADE HISTORY</div>
                  <div className="terminal-controls">
                    <span className="control"></span>
                    <span className="control"></span>
                    <span className="control"></span>
                  </div>
                </div>
                <div style={{ padding: '20px', color: '#39ff14', textAlign: 'center' }}>
                  <p>NO TRADE HISTORY FOUND (0 trades)</p>
                  <p>EXECUTE TRADES TO BUILD HISTORY</p>
                  <p>TRADES APPEAR IN REAL TIME</p>
                </div>
              </div>
            )}
          </Card>
        </MainPanel>
      </DashboardContainer>
    </div>
  );
};

export default Dashboard; 