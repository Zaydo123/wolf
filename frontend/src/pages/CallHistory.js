import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import '../styles/CallHistory.css';

const CallHistory = () => {
  const { user } = useAuth();
  const [calls, setCalls] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [scheduleData, setScheduleData] = useState({
    phoneNumber: '',
    callTime: '09:30',
    callType: 'market_open'
  });

  useEffect(() => {
    const fetchCallHistory = async () => {
      try {
        // In a real app, we would fetch from the API
        // For demo, we'll use mock data
        const mockData = [
          {
            id: 1,
            timestamp: '2023-05-01T09:30:00Z',
            duration: 142,
            type: 'market_open',
            summary: 'Discussed opening positions in AAPL and MSFT based on pre-market movement',
            actions: ['BUY AAPL 10', 'BUY MSFT 5']
          },
          {
            id: 2,
            timestamp: '2023-05-02T09:30:00Z',
            duration: 156,
            type: 'market_open',
            summary: 'Market showing weakness, recommended defensive positions',
            actions: ['SELL TSLA 5', 'BUY T 20']
          },
          {
            id: 3,
            timestamp: '2023-05-03T12:30:00Z',
            duration: 128,
            type: 'mid_day',
            summary: 'Tech sector rallying, recommended increasing tech exposure',
            actions: ['BUY GOOGL 2', 'BUY AMZN 3']
          },
          {
            id: 4,
            timestamp: '2023-05-04T16:00:00Z',
            duration: 147,
            type: 'market_close',
            summary: 'Strong day for portfolio, recommended holding positions overnight',
            actions: []
          },
          {
            id: 5,
            timestamp: '2023-05-05T09:30:00Z',
            duration: 133,
            type: 'market_open',
            summary: 'Jobs report better than expected, markets opening higher',
            actions: ['BUY SPY 10', 'SELL T 10']
          }
        ];
        
        setCalls(mockData);
        setLoading(false);
      } catch (err) {
        setError('Failed to load call history');
        setLoading(false);
      }
    };

    fetchCallHistory();
  }, [user]);

  const handleScheduleSubmit = async (e) => {
    e.preventDefault();
    try {
      setLoading(true);
      
      // In a real app, we would send this to the API
      console.log('Scheduling call:', scheduleData);
      
      // Mock success
      setTimeout(() => {
        alert('Call scheduled successfully!');
        setLoading(false);
      }, 1000);
      
    } catch (err) {
      setError('Failed to schedule call');
      setLoading(false);
    }
  };

  const handleInputChange = (e) => {
    setScheduleData({
      ...scheduleData,
      [e.target.name]: e.target.value
    });
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { 
      month: 'short', 
      day: 'numeric', 
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const formatDuration = (seconds) => {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
  };

  const getCallTypeLabel = (type) => {
    switch (type) {
      case 'market_open':
        return 'Market Open';
      case 'mid_day':
        return 'Mid-Day';
      case 'market_close':
        return 'Market Close';
      default:
        return type;
    }
  };

  if (loading && calls.length === 0) {
    return (
      <div className="loading-screen">
        <div className="loading">
          <div></div>
          <div></div>
          <div></div>
        </div>
        <p>Loading call history...</p>
      </div>
    );
  }

  if (error && calls.length === 0) {
    return <div className="error-message">{error}</div>;
  }

  return (
    <div className="call-history-container">
      <h1>Call History</h1>
      
      <div className="schedule-call-section">
        <h2>Schedule a Call</h2>
        <form onSubmit={handleScheduleSubmit} className="schedule-form">
          <div className="form-group">
            <label htmlFor="phoneNumber">Phone Number</label>
            <input
              type="tel"
              id="phoneNumber"
              name="phoneNumber"
              value={scheduleData.phoneNumber}
              onChange={handleInputChange}
              placeholder="Enter your phone number"
              required
            />
          </div>
          
          <div className="form-group">
            <label htmlFor="callTime">Call Time</label>
            <input
              type="time"
              id="callTime"
              name="callTime"
              value={scheduleData.callTime}
              onChange={handleInputChange}
              required
            />
          </div>
          
          <div className="form-group">
            <label htmlFor="callType">Call Type</label>
            <select
              id="callType"
              name="callType"
              value={scheduleData.callType}
              onChange={handleInputChange}
              required
            >
              <option value="market_open">Market Open (9:30 AM)</option>
              <option value="mid_day">Mid-Day (12:30 PM)</option>
              <option value="market_close">Market Close (4:00 PM)</option>
            </select>
          </div>
          
          <button type="submit" className="schedule-button" disabled={loading}>
            {loading ? 'Scheduling...' : 'Schedule Call'}
          </button>
        </form>
      </div>
      
      <div className="calls-list">
        <h2>Previous Calls</h2>
        {calls.length === 0 ? (
          <p className="no-calls">No call history available yet</p>
        ) : (
          <div className="call-cards">
            {calls.map(call => (
              <div key={call.id} className="call-card">
                <div className="call-header">
                  <div className="call-date">{formatDate(call.timestamp)}</div>
                  <div className="call-badge">{getCallTypeLabel(call.type)}</div>
                </div>
                
                <div className="call-details">
                  <div className="call-info">
                    <span className="label">Duration:</span> 
                    <span className="value">{formatDuration(call.duration)}</span>
                  </div>
                  
                  <div className="call-summary">
                    <span className="label">Summary:</span>
                    <p>{call.summary}</p>
                  </div>
                  
                  {call.actions && call.actions.length > 0 && (
                    <div className="call-actions">
                      <span className="label">Actions Taken:</span>
                      <ul>
                        {call.actions.map((action, index) => (
                          <li key={index}>{action}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
                
                <div className="call-controls">
                  <button className="play-button">
                    <i className="fas fa-play"></i> Play Recording
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default CallHistory; 