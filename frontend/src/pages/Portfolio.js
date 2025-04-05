import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { PieChart, Pie, Cell, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Legend } from 'recharts';
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

  useEffect(() => {
    const fetchPortfolio = async () => {
      try {
        // In a real app, this would be a call to an API
        // For demo, we'll set some mock data
        const mockData = {
          portfolioValue: 24650.75,
          cashBalance: 5350.25,
          positions: [
            { ticker: 'AAPL', quantity: 10, currentValue: 3750.50, averagePrice: 130.25, profit: 450.50 },
            { ticker: 'MSFT', quantity: 15, currentValue: 4875.25, averagePrice: 290.50, profit: 510.25 },
            { ticker: 'GOOGL', quantity: 5, currentValue: 6250.50, averagePrice: 1150.25, profit: 720.50 },
            { ticker: 'AMZN', quantity: 8, currentValue: 2850.25, averagePrice: 330.50, profit: -210.75 },
            { ticker: 'TSLA', quantity: 12, currentValue: 1575.00, averagePrice: 145.25, profit: -168.00 }
          ]
        };
        
        setPortfolio(mockData);
        setLoading(false);
      } catch (err) {
        setError('Failed to load portfolio data');
        setLoading(false);
      }
    };

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
    return <div className="error-message">{error}</div>;
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
      </div>
    </div>
  );
};

export default Portfolio; 