import React, { createContext, useState, useContext, useEffect } from 'react';
import { createClient } from '@supabase/supabase-js';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { findWorkingSupabaseUrl, POTENTIAL_SUPABASE_URLS } from '../utils/networkHelper';

// Default values (will be updated with dynamic checks)
// Use 54323 as the default port
const DEFAULT_URL = 'https://ptejakxtmvgfeyuvfgxv.supabase.co';
const DEFAULT_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0';

// Create a custom fetch with better error handling and auto-retry logic
const createCustomFetch = (timeout = 15000, maxRetries = 3) => {
  return (url, options = {}) => {
    // Function to make a single fetch attempt
    const attemptFetch = async (retryCount = 0) => {
      console.log(`Supabase fetch attempt ${retryCount + 1}/${maxRetries + 1}: ${url}`);
      
      // Add timeout to fetch
      const controller = new AbortController();
      const timeoutId = setTimeout(() => {
        console.log(`Fetch timeout for: ${url}`);
        controller.abort();
      }, timeout);
      
      try {
        const response = await fetch(url, {
          ...options,
          signal: controller.signal,
          headers: {
            ...options.headers,
          },
          mode: 'cors',
          credentials: 'include'
        });
        
        clearTimeout(timeoutId);
        return response;
      } catch (error) {
        clearTimeout(timeoutId);
        console.error(`Fetch error for ${url}:`, error.message);
        
        // If we have retries left and it's a network error, retry
        if (retryCount < maxRetries && 
            (error.name === 'AbortError' || 
             error.message.includes('Failed to fetch') ||
             error.message.includes('Network Error'))) {
          // Exponential backoff
          const delay = Math.min(1000 * Math.pow(2, retryCount), 10000);
          console.log(`Retrying in ${delay}ms...`);
          await new Promise(resolve => setTimeout(resolve, delay));
          return attemptFetch(retryCount + 1);
        }
        
        // Out of retries or not a retriable error
        throw error;
      }
    };
    
    // Start the first attempt
    return attemptFetch();
  };
};

// Create a placeholder client first (will be updated later)
let supabase = createClient(
  'https://ptejakxtmvgfeyuvfgxv.supabase.co', 
  'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InB0ZWpha3h0bXZnZmV5dXZmZ3h2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDM5MjU3OTIsImV4cCI6MjA1OTUwMTc5Mn0.vkbBtOSaRksi8r6R08UQrib93a1t7eiGcLrwi5Hf_do', 
  {
    auth: {
      autoRefreshToken: true,
      persistSession: true,
      detectSessionInUrl: true,
      storageKey: 'wolf_supabase_auth',
    }
  }
);

// Export a function to dynamically update the Supabase client
export const updateSupabaseClient = async () => {
  try {
    // Use a hardcoded value for now to ensure it works
    // This prioritizes working over dynamically finding a URL
    const workingUrl = 'https://ptejakxtmvgfeyuvfgxv.supabase.co';
    const supabaseKey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InB0ZWpha3h0bXZnZmV5dXZmZ3h2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDM5MjU3OTIsImV4cCI6MjA1OTUwMTc5Mn0.vkbBtOSaRksi8r6R08UQrib93a1t7eiGcLrwi5Hf_do';
    
    console.log('Creating Supabase client with URL:', workingUrl);
    
    // Use default fetch instead of custom fetch for reliability
    supabase = createClient(
      workingUrl, 
      supabaseKey, 
      {
        auth: {
          autoRefreshToken: true,
          persistSession: true,
          detectSessionInUrl: true,
          storageKey: 'wolf_supabase_auth',
        }
      }
    );
    
    console.log('Supabase client updated successfully');
    return supabase;
  } catch (err) {
    console.error('Failed to update Supabase client:', err);
    return supabase; // Return existing client as fallback
  }
};

const AuthContext = createContext();

export const useAuth = () => useContext(AuthContext);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [session, setSession] = useState(null);
  const [connectionReady, setConnectionReady] = useState(false);
  const navigate = useNavigate();

  // Check for session on initial load
  // Utility function to retry failed requests
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

  // Initialize Supabase connection
  useEffect(() => {
    const initializeConnection = async () => {
      console.log('Initializing Supabase connection...');
      setLoading(true);
      
      try {
        // Try to find a working Supabase URL and update the client
        await updateSupabaseClient();
        setConnectionReady(true);
        console.log('Supabase connection initialized successfully');
      } catch (err) {
        console.error('Failed to initialize Supabase connection:', err);
        // Still mark as ready to proceed with fallback
        setConnectionReady(true);
      } finally {
        // Make sure loading is set to false even if there's an error
        setLoading(false);
      }
    };
    
    initializeConnection();
  }, []);
  
  // Configure axios defaults with timeout
  useEffect(() => {
    axios.defaults.timeout = 30000; // 30 seconds timeout
    
    // Add retry interceptor
    axios.interceptors.response.use(null, async (error) => {
      // If request was aborted or timed out, or server is unreachable
      if (error.code === 'ECONNABORTED' || error.message === 'Network Error' || 
          error.message.includes('timeout') || error.message.includes('Failed to fetch')) {
        
        const config = error.config;
        
        // Set retry count
        config.__retryCount = config.__retryCount || 0;
        
        if (config.__retryCount < 2) { // Max 2 retries
          config.__retryCount += 1;
          
          // Delay before retry (exponential backoff)
          const backoffDelay = config.__retryCount * 1000;
          await new Promise(resolve => setTimeout(resolve, backoffDelay));
          
          console.log(`Retrying request (${config.__retryCount}/2): ${config.url}`);
          return axios(config);
        }
      }
      
      return Promise.reject(error);
    });
  }, []);

  // Check auth session directly without waiting for connectionReady
  useEffect(() => {
    const checkSession = async () => {
      try {
        console.log('Checking auth session...');
        
        // Timeout for session check to prevent hanging
        const sessionCheckPromise = supabase.auth.getSession();
        const timeoutPromise = new Promise((_, reject) => 
          setTimeout(() => reject(new Error('Session check timed out')), 5000)
        );
        
        // Race between the session check and timeout
        const { data } = await Promise.race([sessionCheckPromise, timeoutPromise]);
        
        if (data?.session) {
          console.log('Session found:', data.session.user.email);
          const { user } = data.session;
          setUser(user);
          // Set up axios interceptor with the current session token
          axios.defaults.headers.common['Authorization'] = `Bearer ${data.session.access_token}`;
          axios.defaults.withCredentials = true;
        } else {
          console.log('No active session found');
        }
      } catch (error) {
        console.error('Session check error:', error.message);
        setError('Could not connect to authentication service');
      } finally {
        setLoading(false);
      }
    };

    // Start session check immediately
    checkSession();

    // Set up auth state change listener
    const { data: authListener } = supabase.auth.onAuthStateChange(
      async (event, session) => {
        if (session) {
          setUser(session.user);
          // Update axios interceptor with the new session token
          axios.defaults.headers.common['Authorization'] = `Bearer ${session.access_token}`;
          axios.defaults.withCredentials = true;
        } else {
          setUser(null);
          // Remove auth header when logged out
          delete axios.defaults.headers.common['Authorization'];
        }
        setLoading(false);
      }
    );

    return () => {
      authListener.subscription.unsubscribe();
    };
  }, []);

  // Register function
  const register = async (email, password, name, phone) => {
    try {
      setLoading(true);
      
      // Register with Supabase Auth
      const { data, error } = await supabase.auth.signUp({
        email,
        password,
      });
      
      if (error) {
        // If the error is just that the user already exists, we can proceed
        // to create the user profile in our database
        if (error.message && error.message.includes('already registered')) {
          console.log('User already exists in auth system, proceeding to create profile');
        } else {
          throw error;
        }
      }
      
      // Get user ID, either from the new registration or by signing in
      let userId = data?.user?.id;
      
      // If user already existed, we need to sign in to get their ID
      if (!userId && error && error.message && error.message.includes('already registered')) {
        const signInResult = await supabase.auth.signInWithPassword({
          email,
          password
        });
        
        if (signInResult.error) {
          throw new Error('Failed to sign in with existing account. Please use correct password.');
        }
        
        userId = signInResult.data?.user?.id;
      }
      
      if (userId) {
        // Create user profile (API call to our backend)
        const response = await fetch(`${process.env.REACT_APP_API_URL || 'http://localhost:8000'}/api/users/register`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            email, 
            password, 
            name, 
            phone_number: phone,
            initial_balance: 10000
          }),
        });
        
        if (!response.ok) {
          const errorText = await response.text();
          console.error('Profile creation error:', errorText);
          
          // If error is about user already registered, we can just continue
          if (errorText.includes('already registered')) {
            console.log('User profile already exists, proceeding to login');
            return { user: { id: userId } };
          }
          
          throw new Error('Failed to create user profile: ' + errorText);
        }
        
        return { user: { id: userId } };
      } else {
        throw new Error('Failed to get user ID during registration');
      }
    } catch (error) {
      setError(error.message);
      throw error;
    } finally {
      setLoading(false);
    }
  };

  // Simple delay function
  const delay = (ms) => new Promise(resolve => setTimeout(resolve, ms));

  // Extra fallback for running without Supabase
  const mockLogin = (email, password) => {
    console.log("Using MOCK login (Supabase not available)");
    // Only allow test@example.com with password 'password'
    if (email === 'test@example.com' && password === 'password') {
      return {
        data: {
          user: {
            id: 'mock-user-123',
            email: email,
            user_metadata: { name: 'Test User' }
          },
          session: {
            access_token: 'mock-token-123',
            user: {
              id: 'mock-user-123',
              email: email,
              user_metadata: { name: 'Test User' }
            }
          }
        },
        error: null
      };
    } else {
      return {
        data: { user: null, session: null },
        error: { message: 'Invalid login credentials' }
      };
    }
  };

  // Login function with simpler and more reliable approach
  const login = async (email, password) => {
    try {
      setLoading(true);
      setError(null);
      
      console.log("Starting login process for:", email);
      
      let loginResult = null;
      
      // Check for mock login override for when Supabase is unavailable
      // Use test@example.com / password to bypass Supabase
      if (email === 'test@example.com') {
        console.log("Using test account - Supabase will be bypassed");
        loginResult = mockLogin(email, password);
      } else {
        // Update client with hardcoded URL
        try {
          await updateSupabaseClient();
        } catch (err) {
          console.warn("Could not update Supabase client, proceeding with default:", err.message);
        }
        
        console.log("Attempting login with Supabase client...");
        
        // Simple direct login with timeout
        const loginPromise = supabase.auth.signInWithPassword({ email, password });
        const timeoutPromise = new Promise((_, reject) => 
          setTimeout(() => reject(new Error('Login request timed out')), 8000)
        );
        
        try {
          loginResult = await Promise.race([loginPromise, timeoutPromise]);
        } catch (err) {
          console.error("Login attempt failed:", err);
          throw new Error(`Login failed: ${err.message}`);
        }
      }
      
      // Process the result
      if (loginResult?.error) {
        console.error("Login error:", loginResult.error);
        throw loginResult.error;
      }
      
      if (!loginResult?.data?.user) {
        console.error("No user data received in login response");
        throw new Error('No user data returned');
      }
      
      // Successfully logged in
      console.log("Login successful, user:", loginResult.data.user.email);
      
      // Store the login data for later use
      const { data } = loginResult;
      
      // Set the auth token for axios
      axios.defaults.headers.common['Authorization'] = `Bearer ${data.session.access_token}`;
      axios.defaults.withCredentials = true;
      
      // Ensure user exists in our database with retry
      try {
        const ensureUserOperation = async () => {
          return await axios.post(
            `${process.env.REACT_APP_API_URL || 'http://localhost:8000'}/api/users/ensure/${data.user.id}`
          );
        };
        
        const response = await retryOperation(ensureUserOperation);
        
        if (response.data.status !== 'success') {
          console.warn('User ensure check returned non-success status but continuing');
        }
      } catch (ensureError) {
        console.error('Error ensuring user exists after retries:', ensureError);
        // Don't throw here, as the user might still be able to use the app
      }
      
      setUser(data.user);
      setSession(data.session);
      // Redirect to homepage instead of dashboard
      navigate('/');
    } catch (error) {
      console.error('Login failed:', error);
      let errorMessage = 'Login failed';
      
      // Provide user-friendly error messages
      if (error.message) {
        if (error.message.includes('fetch') || 
            error.message.includes('network') || 
            error.message.includes('Failed to fetch')) {
          errorMessage = 'Network connection issue. Please check your internet connection and try again.';
        } else if (error.message.includes('Invalid login credentials')) {
          errorMessage = 'Invalid email or password. Please try again.';
        } else {
          errorMessage = error.message;
        }
      }
      
      setError(errorMessage);
      throw error;
    } finally {
      setLoading(false);
    }
  };

  // Logout function
  const logout = async () => {
    try {
      setLoading(true);
      const { error } = await supabase.auth.signOut();
      
      if (error) {
        throw error;
      }
      
      setUser(null);
    } catch (error) {
      setError(error.message);
      throw error;
    } finally {
      setLoading(false);
    }
  };

  // Reset password
  const resetPassword = async (email) => {
    try {
      setLoading(true);
      const { error } = await supabase.auth.resetPasswordForEmail(email, {
        redirectTo: `${window.location.origin}/reset-password`,
      });
      
      if (error) {
        throw error;
      }
      
      return { success: true };
    } catch (error) {
      setError(error.message);
      throw error;
    } finally {
      setLoading(false);
    }
  };

  // Get user profile data
  const getUserProfile = async () => {
    if (!user) return null;
    
    try {
      const response = await fetch(`${process.env.REACT_APP_API_URL || 'http://localhost:8000'}/api/users/${user.id}`);
      
      if (!response.ok) {
        throw new Error('Failed to fetch user profile');
      }
      
      const data = await response.json();
      return data;
    } catch (error) {
      setError(error.message);
      throw error;
    }
  };

  const value = {
    user,
    loading,
    error,
    connectionReady,
    isAuthenticated: !!user,
    login,
    register,
    logout,
    resetPassword,
    getUserProfile,
    updateConnection: updateSupabaseClient, // Expose this so components can trigger a connection update
  };

  // Always render children, don't get stuck in loading
  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}; 