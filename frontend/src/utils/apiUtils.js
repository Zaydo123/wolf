/**
 * API Utilities for making requests with proper error handling
 */
import axios from 'axios';

// Default API URL with fallback
const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// Configure axios defaults for all requests
axios.defaults.timeout = 15000; // 15 seconds timeout

// Create axios instance with default settings
export const apiClient = axios.create({
  baseURL: API_URL,
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true
});

/**
 * Add retry capability to axios requests
 * @param {number} maxRetries - Maximum number of retries (default: 3)
 * @param {number} initialDelay - Initial delay in ms between retries (default: 1000)
 */
export const setupAxiosRetry = (maxRetries = 3, initialDelay = 1000) => {
  // Add response interceptor for retries
  apiClient.interceptors.response.use(null, async (error) => {
    // Track retry count in the request config
    const config = error.config || {};
    config.__retryCount = config.__retryCount || 0;
    
    // Check if error is one we should retry (network, timeout, etc.)
    const shouldRetry = !error.response 
      || error.code === 'ECONNABORTED'
      || error.message.includes('timeout')
      || error.message.includes('Network Error')
      || error.message.includes('Failed to fetch')
      || (error.response && error.response.status >= 500);
    
    // Return immediately for client errors or exceeded retries
    if (!shouldRetry || config.__retryCount >= maxRetries) {
      return Promise.reject(error);
    }
    
    // Increment retry count
    config.__retryCount += 1;
    
    // Exponential backoff
    const delay = initialDelay * Math.pow(2, config.__retryCount - 1);
    console.log(`API retry ${config.__retryCount}/${maxRetries} for ${config.url} in ${delay}ms`);
    
    // Create new promise to handle delay
    return new Promise((resolve) => {
      setTimeout(() => resolve(apiClient(config)), delay);
    });
  });
};

// Setup retries on module load
setupAxiosRetry();

/**
 * Make a GET request with retries and error handling
 * @param {string} url - The URL to get data from
 * @param {Object} options - Additional axios options
 * @returns {Promise} - Response data or error
 */
export const fetchData = async (url, options = {}) => {
  try {
    console.log(`Fetching data from: ${url}`);
    const response = await apiClient.get(url, options);
    return response.data;
  } catch (error) {
    console.error(`Error fetching ${url}:`, error);
    
    // Enhanced error object with user-friendly message
    const enhancedError = new Error(getUserFriendlyErrorMessage(error));
    enhancedError.originalError = error;
    enhancedError.status = error.response?.status;
    
    throw enhancedError;
  }
};

/**
 * Make a POST request with retries and error handling
 * @param {string} url - The URL to post data to
 * @param {Object} data - The data to send
 * @param {Object} options - Additional axios options
 * @returns {Promise} - Response data or error
 */
export const postData = async (url, data, options = {}) => {
  try {
    console.log(`Posting data to: ${url}`);
    const response = await apiClient.post(url, data, options);
    return response.data;
  } catch (error) {
    console.error(`Error posting to ${url}:`, error);
    
    // Enhanced error object with user-friendly message
    const enhancedError = new Error(getUserFriendlyErrorMessage(error));
    enhancedError.originalError = error;
    enhancedError.status = error.response?.status;
    
    throw enhancedError;
  }
};

/**
 * Generate a user-friendly error message based on the error
 * @param {Error} error - The error object
 * @returns {string} - User-friendly error message
 */
export const getUserFriendlyErrorMessage = (error) => {
  // Network error messages
  if (!error.response) {
    if (error.message.includes('timeout')) {
      return 'Request timed out. Please try again.';
    }
    if (error.message.includes('Network Error') || error.message.includes('Failed to fetch')) {
      return 'Network connection issue. Please check your internet connection and try again.';
    }
    return 'Could not connect to the server. Please try again later.';
  }
  
  // Server error messages (500s)
  if (error.response.status >= 500) {
    return 'Server error. Our team has been notified and is working to fix it.';
  }
  
  // Auth related errors (401, 403)
  if (error.response.status === 401) {
    return 'Your session has expired. Please log in again.';
  }
  
  if (error.response.status === 403) {
    return 'You do not have permission to perform this action.';
  }
  
  // Not found error (404)
  if (error.response.status === 404) {
    return 'The requested resource was not found.';
  }
  
  // Validation errors (400)
  if (error.response.status === 400) {
    // Try to extract validation messages if available
    const data = error.response.data;
    if (data?.message) {
      return data.message;
    }
    return 'Invalid request. Please check your input and try again.';
  }
  
  // Default error message
  return error.message || 'An unexpected error occurred. Please try again.';
};

export default {
  apiClient,
  fetchData,
  postData,
  getUserFriendlyErrorMessage
};