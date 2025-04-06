import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import '../styles/CallHistory.css';
import axios from 'axios';

const CallHistory = () => {
  const { user } = useAuth();
  const [calls, setCalls] = useState([]);
  const [schedules, setSchedules] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [scheduleData, setScheduleData] = useState({
    phoneNumber: '',
    callTime: '09:30',
    callType: 'market_open'
  });
  const [submitSuccess, setSubmitSuccess] = useState(false);
  
  const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

  // Utility function to retry operations
  const retryOperation = async (operation, maxRetries = 3, initialDelay = 1000) => {
    let lastError = null;
    let currentDelay = initialDelay;
    
    for (let attempt = 0; attempt < maxRetries; attempt++) {
      try {
        return await operation();
      } catch (err) {
        lastError = err;
        console.log(`Attempt ${attempt + 1} failed, retrying in ${currentDelay}ms...`, err);
        await new Promise(resolve => setTimeout(resolve, currentDelay));
        // Exponential backoff
        currentDelay = Math.floor(currentDelay * 1.5);
      }
    }
    throw lastError;
  };

  useEffect(() => {
    const fetchCallData = async () => {
      if (!user) return;
      
      setLoading(true);
      setError('');
      
      try {
        // Use Promise.allSettled to fetch both resources in parallel with retries
        const [callHistoryResult, schedulesResult] = await Promise.allSettled([
          retryOperation(async () => {
            try {
              console.log("Fetching call history...");
              const response = await axios.get(`${API_URL}/api/calls/history/${user.id}`);
              if (!response.data || !response.data.calls) {
                throw new Error("Invalid response format from server");
              }
              return response;
            } catch (error) {
              // Check if it's a network error
              if (error.message && (
                error.message.includes('Failed to fetch') ||
                error.message.includes('NetworkError') ||
                error.message.includes('Network Error') ||
                error.code === 'ECONNABORTED'
              )) {
                console.log('Network error fetching call history, will retry:', error.message);
                throw error; // Rethrow to trigger retry
              }
              throw error; // Rethrow other errors
            }
          }),
          retryOperation(async () => {
            try {
              console.log("Fetching call schedules...");
              const response = await axios.get(`${API_URL}/api/calls/schedules/${user.id}`);
              if (!response.data || !response.data.schedules) {
                throw new Error("Invalid response format from server");
              }
              return response;
            } catch (error) {
              // Check if it's a network error
              if (error.message && (
                error.message.includes('Failed to fetch') ||
                error.message.includes('NetworkError') ||
                error.message.includes('Network Error') ||
                error.code === 'ECONNABORTED'
              )) {
                console.log('Network error fetching schedules, will retry:', error.message);
                throw error; // Rethrow to trigger retry
              }
              throw error; // Rethrow other errors
            }
          })
        ]);
        
        // Process call history result
        if (callHistoryResult.status === 'fulfilled') {
          setCalls(callHistoryResult.value.data.calls || []);
        } else {
          console.error('Call history fetch failed after retries:', callHistoryResult.reason);
          setError('Failed to load call history. Please try again later.');
        }
        
        // Process schedules result
        if (schedulesResult.status === 'fulfilled') {
          setSchedules(schedulesResult.value.data.schedules || []);
        } else {
          console.error('Schedules fetch failed after retries:', schedulesResult.reason);
          // Don't set error for schedules as it's less critical
        }
        
      } catch (err) {
        console.error('Error fetching call data:', err);
        setError('Failed to load call data. Please check your internet connection and try again.');
      } finally {
        setLoading(false);
      }
    };

    fetchCallData();
  }, [user, API_URL]);

  const handleScheduleSubmit = async (e) => {
    e.preventDefault();
    try {
      setLoading(true);
      setError('');
      
      // Get user data first to pre-fill with retry
      const getUserData = async () => {
        try {
          return await retryOperation(() => axios.get(`${API_URL}/api/users/${user.id}`));
        } catch (error) {
          console.error('Failed to fetch user data after retries:', error);
          throw new Error('Could not fetch user profile data. Please try again.');
        }
      };
      
      const userResponse = await getUserData();
      const userData = userResponse.data;
      
      // Use phone number from user profile if not provided
      const phoneNumber = scheduleData.phoneNumber || userData.phone_number;
      
      if (!phoneNumber) {
        setError('Please provide a phone number');
        setLoading(false);
        return;
      }
      
      // Submit schedule request with retry
      const scheduleCall = async () => {
        try {
          return await retryOperation(() => 
            axios.post(`${API_URL}/api/calls/schedule`, {
              user_id: user.id,
              phone_number: phoneNumber,
              call_time: scheduleData.callTime,
              call_type: scheduleData.callType
            })
          );
        } catch (error) {
          console.error('Failed to schedule call after retries:', error);
          throw new Error('Network issue while scheduling call. Please try again.');
        }
      };
      
      await scheduleCall();
      
      // Reset form and show success message
      setScheduleData({
        phoneNumber: '',
        callTime: '09:30',
        callType: 'market_open'
      });
      
      setSubmitSuccess(true);
      
      // Fetch updated schedules with retry
      const getUpdatedSchedules = async () => {
        try {
          return await retryOperation(() => 
            axios.get(`${API_URL}/api/calls/schedules/${user.id}`)
          );
        } catch (error) {
          console.error('Failed to fetch updated schedules after retries:', error);
          return { data: { schedules: [] } }; // Fallback to empty list
        }
      };
      
      const schedulesResponse = await getUpdatedSchedules();
      setSchedules(schedulesResponse.data.schedules || []);
      
      // Clear success message after 3 seconds
      setTimeout(() => {
        setSubmitSuccess(false);
      }, 3000);
      
      setLoading(false);
    } catch (err) {
      console.error('Error scheduling call:', err);
      
      // Provide user-friendly error message
      let errorMessage = 'Failed to schedule call';
      if (err.message) {
        if (err.message.includes('Failed to fetch') || 
            err.message.includes('network') || 
            err.message.includes('Network')) {
          errorMessage = 'Network connection issue. Please check your internet connection and try again.';
        } else {
          errorMessage = err.message;
        }
      }
      
      setError(errorMessage);
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
    if (!dateString) return 'N/A';
    
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
    if (!seconds) return 'N/A';
    
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

  if (loading && calls.length === 0 && schedules.length === 0) {
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

  return (
    <div className="call-history-container">
      <h1>Call History</h1>
      
      <div className="schedule-call-section">
        <h2>Schedule a Call</h2>
        {submitSuccess && (
          <div className="success-message">
            Call scheduled successfully!
          </div>
        )}
        {error && (
          <div className="error-message">
            {error}
          </div>
        )}
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
            />
            <small>Leave blank to use your profile phone number</small>
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
      
      {schedules.length > 0 && (
        <div className="scheduled-calls-section">
          <h2>Upcoming Scheduled Calls</h2>
          <div className="scheduled-calls-list">
            {schedules.map((schedule, index) => (
              <div key={index} className="scheduled-call-card">
                <div className="call-type">{getCallTypeLabel(schedule.call_type)}</div>
                <div className="call-time">{schedule.call_time}</div>
                <div className="call-status">{schedule.status}</div>
              </div>
            ))}
          </div>
        </div>
      )}
      
      <div className="calls-list">
        <h2>Previous Calls</h2>
        {calls.length === 0 ? (
          <p className="no-calls">No call history available yet</p>
        ) : (
          <div className="call-cards">
            {calls.map(call => (
              <div key={call.id} className="call-card">
                <div className="call-header">
                  <div className="call-date">{formatDate(call.started_at)}</div>
                  <div className={`call-badge ${call.status.toLowerCase()}`}>{call.status}</div>
                </div>
                
                <div className="call-details">
                  <div className="call-info">
                    <span className="label">Duration:</span> 
                    <span className="value">{formatDuration(call.duration)}</span>
                  </div>
                  
                  {call.summary && (
                    <div className="call-summary">
                      <span className="label">Summary:</span>
                      <p>{call.summary}</p>
                    </div>
                  )}
                  
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
                  
                  {call.transcript && call.transcript.length > 0 && (
                    <div className="call-transcript">
                      <span className="label">Transcript:</span>
                      <div className="transcript-content">
                        {call.transcript.map((entry, index) => (
                          <div key={index} className={`transcript-entry ${entry.speaker.toLowerCase()}`}>
                            <div className="transcript-header">
                              <span className="speaker">{entry.speaker}</span>
                              <span className="timestamp">{entry.timestamp}</span>
                            </div>
                            <div className="message">{entry.content}</div>
                          </div>
                        ))}
                      </div>
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