import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import '../styles/Settings.css';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const Settings = () => {
  const { user, getUserProfile, updateUser, logout } = useAuth();
  const [userProfile, setUserProfile] = useState(null);
  const [profileData, setProfileData] = useState({
    name: '',
    email: user?.email || '',
    phoneNumber: '',
    password: '',
    confirmPassword: ''
  });
  const [preferences, setPreferences] = useState({
    marketOpenAlerts: true,
    marketCloseAlerts: true,
    earningsAlerts: true,
    newsAlerts: false,
    callRecordings: true,
    darkMode: false,
    tradingMode: 'paper'
  });
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState('');
  const [error, setError] = useState('');

  // Add useEffect to load user profile data
  useEffect(() => {
    async function loadUserProfile() {
      if (user) {
        try {
          const profile = await getUserProfile();
          setUserProfile(profile);
          setProfileData(prev => ({
            ...prev,
            name: profile?.name || '',
            email: profile?.email || user?.email || '',
            phoneNumber: profile?.phone_number || ''
          }));
        } catch (err) {
          console.error("Error loading user profile:", err);
        }
      }
    }
    
    loadUserProfile();
  }, [user, getUserProfile]);

  const handleProfileChange = (e) => {
    setProfileData({
      ...profileData,
      [e.target.name]: e.target.value
    });
  };

  const handlePreferenceChange = (e) => {
    const value = e.target.type === 'checkbox' ? e.target.checked : e.target.value;
    setPreferences({
      ...preferences,
      [e.target.name]: value
    });
  };

  const handleProfileSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    
    if (profileData.password && profileData.password !== profileData.confirmPassword) {
      return setError('Passwords do not match');
    }
    
    try {
      setLoading(true);
      
      // In a real app, we would call an API endpoint
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      console.log('Profile update:', profileData);
      setSuccess('Profile updated successfully');
      setLoading(false);
    } catch (err) {
      setError('Failed to update profile');
      setLoading(false);
    }
  };

  const handlePreferencesSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    
    try {
      setLoading(true);
      
      // In a real app, we would call an API endpoint
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      console.log('Preferences update:', preferences);
      setSuccess('Preferences updated successfully');
      setLoading(false);
    } catch (err) {
      setError('Failed to update preferences');
      setLoading(false);
    }
  };

  const handleLogout = () => {
    logout();
  };

  return (
    <div className="settings-container">
      <h1>Settings</h1>
      
      {success && <div className="success-message">{success}</div>}
      {error && <div className="error-message">{error}</div>}
      
      <div className="settings-section">
        <h2>Profile Settings</h2>
        <form onSubmit={handleProfileSubmit} className="settings-form">
          <div className="form-group">
            <label htmlFor="name">Full Name</label>
            <input
              type="text"
              id="name"
              name="name"
              value={profileData.name}
              onChange={handleProfileChange}
              required
            />
          </div>
          
          <div className="form-group">
            <label htmlFor="email">Email Address</label>
            <input
              type="email"
              id="email"
              name="email"
              value={profileData.email}
              onChange={handleProfileChange}
              required
            />
          </div>
          
          <div className="form-group">
            <label htmlFor="phoneNumber">Phone Number</label>
            <input
              type="tel"
              id="phoneNumber"
              name="phoneNumber"
              value={profileData.phoneNumber}
              onChange={handleProfileChange}
              placeholder="For call notifications"
            />
          </div>
          
          <div className="form-group">
            <label htmlFor="password">New Password (leave blank to keep current)</label>
            <input
              type="password"
              id="password"
              name="password"
              value={profileData.password}
              onChange={handleProfileChange}
            />
          </div>
          
          <div className="form-group">
            <label htmlFor="confirmPassword">Confirm New Password</label>
            <input
              type="password"
              id="confirmPassword"
              name="confirmPassword"
              value={profileData.confirmPassword}
              onChange={handleProfileChange}
            />
          </div>
          
          <button 
            type="submit" 
            className="save-button" 
            disabled={loading}
          >
            {loading ? 'Saving...' : 'Save Profile'}
          </button>
        </form>
      </div>
      
      <div className="settings-section">
        <h2>Notification Preferences</h2>
        <form onSubmit={handlePreferencesSubmit} className="settings-form">
          <div className="form-group checkbox">
            <input
              type="checkbox"
              id="marketOpenAlerts"
              name="marketOpenAlerts"
              checked={preferences.marketOpenAlerts}
              onChange={handlePreferenceChange}
            />
            <label htmlFor="marketOpenAlerts">Market Open Alerts (9:30 AM ET)</label>
          </div>
          
          <div className="form-group checkbox">
            <input
              type="checkbox"
              id="marketCloseAlerts"
              name="marketCloseAlerts"
              checked={preferences.marketCloseAlerts}
              onChange={handlePreferenceChange}
            />
            <label htmlFor="marketCloseAlerts">Market Close Alerts (4:00 PM ET)</label>
          </div>
          
          <div className="form-group checkbox">
            <input
              type="checkbox"
              id="earningsAlerts"
              name="earningsAlerts"
              checked={preferences.earningsAlerts}
              onChange={handlePreferenceChange}
            />
            <label htmlFor="earningsAlerts">Earnings Announcements for Owned Stocks</label>
          </div>
          
          <div className="form-group checkbox">
            <input
              type="checkbox"
              id="newsAlerts"
              name="newsAlerts"
              checked={preferences.newsAlerts}
              onChange={handlePreferenceChange}
            />
            <label htmlFor="newsAlerts">Breaking News Alerts</label>
          </div>
          
          <div className="form-group checkbox">
            <input
              type="checkbox"
              id="callRecordings"
              name="callRecordings"
              checked={preferences.callRecordings}
              onChange={handlePreferenceChange}
            />
            <label htmlFor="callRecordings">Save Call Recordings</label>
          </div>
          
          <div className="form-group">
            <label htmlFor="tradingMode">Trading Mode</label>
            <select
              id="tradingMode"
              name="tradingMode"
              value={preferences.tradingMode}
              onChange={handlePreferenceChange}
            >
              <option value="paper">Paper Trading (Practice)</option>
              <option value="live">Live Trading (Real Money)</option>
            </select>
          </div>
          
          <button 
            type="submit" 
            className="save-button" 
            disabled={loading}
          >
            {loading ? 'Saving...' : 'Save Preferences'}
          </button>
        </form>
      </div>
      
      <div className="settings-section">
        <h2>Account Actions</h2>
        <div className="account-actions">
          <button 
            onClick={handleLogout}
            className="logout-button"
          >
            Log Out
          </button>
          
          <button className="danger-button">
            Delete Account
          </button>
        </div>
      </div>
      
      <div className="settings-section">
        <h2>Account Repair</h2>
        <p>If you're experiencing issues with your account, you can try repairing it.</p>
        <button 
          onClick={async () => {
            if (!user || !user.id) {
              alert('You need to be logged in to repair your account');
              return;
            }
            
            try {
              setLoading(true);
              
              // Call the ensure_user_exists endpoint
              const response = await fetch(
                `${API_URL}/api/users/ensure/${user.id}`, 
                {
                  method: 'POST',
                  headers: {
                    'Content-Type': 'application/json'
                  },
                  body: JSON.stringify({
                    phone_number: profileData.phoneNumber || ''
                  })
                }
              );
              
              if (!response.ok) {
                throw new Error('Failed to repair account');
              }
              
              const result = await response.json();
              
              if (result.action === 'created') {
                alert('Account repair successful! Your user profile has been created.');
              } else if (result.action === 'updated_phone') {
                alert('Account repair successful! Your phone number has been updated.');
              } else {
                alert('Account check completed. No issues were found with your account.');
              }
              
            } catch (error) {
              console.error('Error repairing account:', error);
              alert(`Error repairing account: ${error.message}`);
            } finally {
              setLoading(false);
            }
          }}
          disabled={loading}
          className="settings-button"
        >
          Repair My Account
        </button>
      </div>
    </div>
  );
};

export default Settings; 