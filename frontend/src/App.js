import React, { useState, useEffect } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import axios from 'axios';

// Pages
import Dashboard from './pages/Dashboard';
import Login from './pages/Login';
import Register from './pages/Register';
import Portfolio from './pages/Portfolio';
import CallHistory from './pages/CallHistory';
import Settings from './pages/Settings';

// Components
import Navbar from './components/Navbar';
import { AuthProvider, useAuth } from './context/AuthContext';

// WebSocket connection for real-time updates
function setupWebSocket(userId) {
  const wsUrl = process.env.REACT_APP_WS_URL || 'ws://localhost:8000/ws';
  const socket = new WebSocket(`${wsUrl}/${userId}`);
  
  socket.onopen = () => {
    console.log('WebSocket connection established');
  };
  
  socket.onclose = () => {
    console.log('WebSocket connection closed');
    // Attempt to reconnect in 5 seconds
    setTimeout(() => setupWebSocket(userId), 5000);
  };
  
  socket.onerror = (error) => {
    console.error('WebSocket error:', error);
  };
  
  return socket;
}

// Protected route component
const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();
  
  if (loading) {
    return (
      <div className="loading-screen">
        <div className="loading">
          <div></div>
          <div></div>
          <div></div>
        </div>
        <p>Loading...</p>
      </div>
    );
  }
  
  if (!isAuthenticated) {
    return <Navigate to="/login" />;
  }
  
  return children;
};

function App() {
  const { user } = useAuth();
  const [socket, setSocket] = useState(null);
  
  useEffect(() => {
    // Set up WebSocket connection when user is authenticated
    if (user && !socket) {
      const newSocket = setupWebSocket(user.id);
      setSocket(newSocket);
      
      return () => {
        newSocket.close();
      };
    }
  }, [user, socket]);
  
  return (
    <div className="app crt-effect">
      <Navbar />
      <main className="container">
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route 
            path="/" 
            element={
              <ProtectedRoute>
                <Dashboard socket={socket} />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/portfolio" 
            element={
              <ProtectedRoute>
                <Portfolio socket={socket} />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/calls" 
            element={
              <ProtectedRoute>
                <CallHistory />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/settings" 
            element={
              <ProtectedRoute>
                <Settings />
              </ProtectedRoute>
            } 
          />
        </Routes>
      </main>
    </div>
  );
}

// Wrap App with AuthProvider
const AppWithAuth = () => (
  <AuthProvider>
    <App />
  </AuthProvider>
);

export default AppWithAuth; 