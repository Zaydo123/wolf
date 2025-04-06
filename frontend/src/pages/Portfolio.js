import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { PieChart, Pie, Cell, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Legend } from 'recharts';
import { fetchData, postData } from '../utils/apiUtils';
import '../styles/Portfolio.css';

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8', '#FF6666'];

const Portfolio = ({ socket }) => {
  const { user } = useAuth();
  const [portfolio, setPortfolio] = useState({
    portfolioValue: 0,
    cashBalance: 0,
    positions: []
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Define fetchPortfolio outside useEffect so we can call it from retry button 
  const fetchPortfolio = async () => {
    if (!user?.id) {
      setError('No user ID available');
      setLoading(false);
      return;
    }
    
    try {
      console.log(`Fetching portfolio for user ID: ${user.id}`);
      
      // First, call the update-prices endpoint to refresh data
      console.log('Updating portfolio prices...');
      await postData(`/api/trades/portfolio/${user.id}/update-prices`);
      console.log('Portfolio prices updated successfully');
      
      // Use the fetchData utility for better error handling and retries
      const data = await fetchData(`/api/trades/portfolio/${user.id}`);
      
      // Transform the API data to match our component's expected format
      // First, ensure the data has the expected structure
      if (!data || typeof data !== 'object') {
        console.error('Invalid portfolio data received:', data);
        throw new Error('Invalid data format received from server');
      }
      
      // Check if portfolio_value is present and is a number
      const portfolioValue = typeof data.portfolio_value === 'number' ? data.portfolio_value : 0;
      const cashBalance = typeof data.cash_balance === 'number' ? data.cash_balance : 0;
      
      // Make sure positions is an array
      const positions = Array.isArray(data.positions) ? data.positions : [];
      
      const portfolioData = {
        portfolioValue: portfolioValue,
        cashBalance: cashBalance,
        positions: positions.map(position => {
          // Ensure required fields exist with defaults if missing
          const ticker = position.ticker || 'UNKNOWN';
          const quantity = typeof position.quantity === 'number' ? position.quantity : 0;
          const value = typeof position.value === 'number' ? position.value : 0;
          const avgPrice = typeof position.avg_price === 'number' ? position.avg_price : 0;
          const currentPrice = typeof position.current_price === 'number' ? position.current_price : avgPrice;
          
          return {
            ticker: ticker,
            quantity: quantity,
            currentValue: value,
            averagePrice: avgPrice,
            profit: (currentPrice - avgPrice) * quantity
          };
        })
      };
      
      console.log('Portfolio data loaded successfully:', portfolioData);
      setPortfolio(portfolioData);
      setError(''); // Clear any previous errors
      setLoading(false);
    } catch (err) {
      console.error('Error fetching portfolio:', err);
      setError(`Failed to load portfolio data: ${err.message}`);
      setLoading(false);
    }
  };

  useEffect(() => {
    // Load portfolio data when component mounts
    fetchPortfolio();

    // Handle WebSocket updates
    if (socket) {
      socket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        
        if (data.type === 'trade_executed' && data.user_id === user.id) {
          fetchPortfolio();
        }
      };
    }
  }, [user, socket]);

  const getPieChartData = () => {
    const positions = portfolio.positions.map(pos => ({
      name: pos.ticker,
      value: pos.currentValue
    }));
    
    positions.push({
      name: 'Cash',
      value: portfolio.cashBalance
    });
    
    return positions;
  };

  const getPerformanceData = () => {
    return portfolio.positions.map(pos => ({
      name: pos.ticker,
      profit: pos.profit
    }));
  };

  if (loading) {
    return (
      <div className="loading-screen">
        <div className="loading">
          <div></div>
          <div></div>
          <div></div>
        </div>
        <p>Loading portfolio...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="error-container">
        <div className="error-message">{error}</div>
        <button 
          className="retry-button" 
          onClick={() => {
            setLoading(true);
            setError('');
            fetchPortfolio();
          }}
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="portfolio-container">
      <h1>Your Portfolio</h1>
      
      <div className="portfolio-summary">
        <div className="summary-card">
          <h3>Total Value</h3>
          <p className="value">${portfolio.portfolioValue.toFixed(2)}</p>
        </div>
        
        <div className="summary-card">
          <h3>Cash Balance</h3>
          <p className="value">${portfolio.cashBalance.toFixed(2)}</p>
        </div>
        
        <div className="summary-card">
          <h3>Positions</h3>
          <p className="value">{portfolio.positions.length}</p>
        </div>
      </div>
      
      <div className="portfolio-charts">
        <div className="chart-container">
          <h3>Asset Allocation</h3>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={getPieChartData()}
                cx="50%"
                cy="50%"
                labelLine={false}
                outerRadius={80}
                fill="#8884d8"
                dataKey="value"
                label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
              >
                {getPieChartData().map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip formatter={(value) => `$${value.toFixed(2)}`} />
            </PieChart>
          </ResponsiveContainer>
        </div>
        
        <div className="chart-container">
          <h3>Position Performance</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={getPerformanceData()}>
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip formatter={(value) => `$${value.toFixed(2)}`} />
              <Legend />
              <Bar dataKey="profit" fill="#8884d8">
                {getPerformanceData().map((entry, index) => (
                  <Cell 
                    key={`cell-${index}`} 
                    fill={entry.profit >= 0 ? '#00C49F' : '#FF6666'} 
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
      
      <div className="positions-table">
        <h3>Your Positions</h3>
        
        {portfolio.positions.length > 0 ? (
          <table>
            <thead>
              <tr>
                <th>Symbol</th>
                <th>Quantity</th>
                <th>Avg. Price</th>
                <th>Current Value</th>
                <th>Profit/Loss</th>
              </tr>
            </thead>
            <tbody>
              {portfolio.positions.map((position) => (
                <tr key={position.ticker}>
                  <td>{position.ticker}</td>
                  <td>{position.quantity}</td>
                  <td>${position.averagePrice.toFixed(2)}</td>
                  <td>${position.currentValue.toFixed(2)}</td>
                  <td className={position.profit >= 0 ? 'profit' : 'loss'}>
                    ${Math.abs(position.profit).toFixed(2)} 
                    {position.profit >= 0 ? '▲' : '▼'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div className="empty-portfolio">
            <p>You don't have any positions yet.</p>
            <p>You have ${portfolio.cashBalance.toFixed(2)} available to invest.</p>
            <button className="action-button" onClick={() => window.location.href = '/dashboard'}>
              Start Trading
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default Portfolio; 