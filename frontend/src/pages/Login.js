import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import styled from 'styled-components';

const LoginContainer = styled.div`
  max-width: 400px;
  margin: 2rem auto;
  padding: 2rem;
  background-color: rgba(0, 0, 0, 0.8);
  border: 1px solid var(--primary);
  border-radius: 4px;
  box-shadow: 0 0 20px rgba(57, 255, 20, 0.3);
`;

const Title = styled.h1`
  text-align: center;
  margin-bottom: 2rem;
`;

const Form = styled.form`
  display: flex;
  flex-direction: column;
`;

const Input = styled.input`
  margin-bottom: 1rem;
  padding: 0.75rem;
`;

const Button = styled.button`
  margin-top: 1rem;
  padding: 0.75rem;
`;

const ErrorMessage = styled.div`
  color: var(--warning);
  margin-bottom: 1rem;
  text-align: center;
`;

const StatusMessage = styled.div`
  margin-bottom: 1rem;
  text-align: center;
  color: ${props => props.type === 'error' ? 'var(--warning)' : 'var(--primary)'};
`;

const RegisterLink = styled.div`
  margin-top: 1.5rem;
  text-align: center;
`;

const Login = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState('checking');
  
  const { login, updateConnection, connectionReady } = useAuth();
  const navigate = useNavigate();
  
  // Check connection to APIs on component mount
  useEffect(() => {
    const checkConnection = async () => {
      try {
        console.log('Login: Checking API connections...');
        
        // First try to update Supabase connection
        if (updateConnection) {
          try {
            await updateConnection();
            console.log('Supabase connection updated from Login component');
          } catch (error) {
            console.warn('Login: Failed to update Supabase connection:', error);
          }
        }
        
        // Check connection to backend API
        const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:8000';
        
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 5000);
        
        try {
          // Try to access a known backend endpoint
          await fetch(`${apiUrl}/api/users/health`, { 
            method: 'GET',
            signal: controller.signal,
            mode: 'no-cors',
            headers: {
              'Accept': 'application/json'
            }
          });
          console.log('Backend API connection successful');
          setConnectionStatus('ready');
        } catch (err) {
          console.warn('API connection check failed, app may still work:', err);
          
          // If this fails, try one more endpoint
          try {
            await fetch(`${apiUrl}`, { 
              method: 'GET',
              signal: controller.signal,
              mode: 'no-cors',
              headers: {
                'Accept': 'application/json'
              }
            });
            console.log('Basic backend connection successful');
            setConnectionStatus('ready');
          } catch (secondErr) {
            console.warn('Basic connection check also failed:', secondErr);
            setConnectionStatus('warning');
          }
        } finally {
          clearTimeout(timeoutId);
        }
      } catch (err) {
        console.error('Connection checks failed:', err);
        setConnectionStatus('error');
      }
    };
    
    // Only run this if the auth provider signals connection is ready
    if (connectionReady) {
      checkConnection();
    } else {
      // If auth provider is still connecting, wait for it
      console.log('Waiting for auth provider to connect...');
    }
  }, [connectionReady, updateConnection]);
  
  // Show a debug message in development mode
  useEffect(() => {
    if (process.env.NODE_ENV === 'development') {
      console.log('Supabase config:', {
        url: process.env.REACT_APP_SUPABASE_URL || 'https://ptejakxtmvgfeyuvfgxv.supabase.co',
        keyAvailable: Boolean(process.env.REACT_APP_SUPABASE_KEY)
      });
    }
  }, []);
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    
    if (!email || !password) {
      setError('Please enter both email and password');
      return;
    }
    
    // First, check if we're still in a checking state
    if (connectionStatus === 'checking') {
      setError('Still checking connection. Please wait a moment...');
      return;
    }
    
    try {
      setLoading(true);
      console.log('Login form: attempting login for', email);
      
      // Try to update connection one more time before login
      if (updateConnection) {
        try {
          await updateConnection();
        } catch (connError) {
          console.warn('Failed to update connection before login, proceeding anyway');
        }
      }
      
      // Add debug info
      if (!process.env.REACT_APP_SUPABASE_URL) {
        console.warn('REACT_APP_SUPABASE_URL is not set, using dynamic URL detection');
      }
      
      // Attempt login with more robust error handling
      await login(email, password);
      
      // Navigate on successful login
      console.log('Login successful, navigating to dashboard');
      navigate('/');
    } catch (error) {
      console.error('Login form error:', error);
      
      // Provide more helpful error messages
      let errorMessage = 'Failed to log in';
      
      if (error.message) {
        if (error.message.includes('fetch') || 
            error.message.includes('network') || 
            error.message.includes('Failed to fetch')) {
          errorMessage = 'Network connection issue. Please check your internet connection and try again.';
        } else if (error.message.includes('Invalid login')) {
          errorMessage = 'Invalid email or password. Please try again.';
        } else if (error.message.includes('timeout')) {
          errorMessage = 'Login request timed out. Please try again.';
        } else if (error.message.includes('multiple attempts')) {
          errorMessage = 'Connection issues detected. Please check your network and try again.';
        } else {
          errorMessage = error.message;
        }
      }
      
      setError(errorMessage);
      
      // If it looks like a network error, try to refresh the connection
      if (errorMessage.includes('Network') || errorMessage.includes('connection')) {
        try {
          if (updateConnection) {
            console.log('Attempting to refresh Supabase connection after error...');
            await updateConnection();
          }
        } catch (refreshError) {
          console.error('Failed to refresh connection:', refreshError);
        }
      }
    } finally {
      setLoading(false);
    }
  };
  
  // Connection status message
  const getConnectionMessage = () => {
    switch (connectionStatus) {
      case 'checking':
        return 'Checking connection...';
      case 'error':
        return 'Warning: Connection to Supabase at port 54323 could not be established. Please make sure Supabase is running.';
      case 'warning':
        return 'Connection seems slow. Make sure Supabase is running on port 54323.';
      default:
        return null;
    }
  };
  
  const connectionMessage = getConnectionMessage();
  
  return (
    <LoginContainer>
      <Title>LOGIN</Title>
      
      {connectionMessage && (
        <StatusMessage type={connectionStatus === 'error' ? 'error' : 'info'}>
          {connectionMessage}
        </StatusMessage>
      )}
      
      {connectionStatus === 'error' && (
        <StatusMessage type="info" style={{ marginTop: '10px' }}>
          Hint: Use test@example.com / password to login without Supabase
        </StatusMessage>
      )}
      
      {error && <ErrorMessage>{error}</ErrorMessage>}
      
      <Form onSubmit={handleSubmit}>
        <Input
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
        
        <Input
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
        
        <Button type="submit" disabled={loading}>
          {loading ? 'LOGGING IN...' : 'LOGIN'}
        </Button>
      </Form>
      
      <RegisterLink>
        Don't have an account? <Link to="/register">Register now</Link>
      </RegisterLink>
      

    </LoginContainer>
  );
};

export default Login;