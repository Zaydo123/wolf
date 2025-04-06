/**
 * CORS Proxy utility for handling Supabase requests in development
 * 
 * This utility helps handle CORS issues when communicating with Supabase
 * in development mode, especially in Docker environments.
 */

/**
 * Detect if we're running in a development environment
 */
export const isDevelopment = process.env.NODE_ENV === 'development';

/**
 * Get the appropriate base URL for Supabase API requests
 * In development, use the configured port in Docker
 */
export const getSupabaseProxyUrl = () => {
  if (isDevelopment) {
    // For Docker/local development, use the local Supabase instance with correct port
    return 'https://ptejakxtmvgfeyuvfgxv.supabase.co';
  }
  
  // In production, use the configured URL
  return process.env.REACT_APP_SUPABASE_URL;
};

/**
 * Create a proxy request to Supabase that handles CORS issues
 * @param {string} endpoint - The Supabase endpoint path
 * @param {Object} options - Fetch options
 * @returns {Promise} - Fetch response
 */
export const proxySupabaseRequest = async (endpoint, options = {}) => {
  const baseUrl = getSupabaseProxyUrl();
  const url = `${baseUrl}${endpoint}`;
  
  // Set up default headers and CORS options
  const fetchOptions = {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers
    },
    mode: 'no-cors',
    credentials: 'omit'
  };
  
  try {
    console.log(`Proxying Supabase request to: ${url}`);
    const response = await fetch(url, fetchOptions);
    return response;
  } catch (error) {
    console.error('Proxy request failed:', error);
    throw error;
  }
};

export default {
  isDevelopment,
  getSupabaseProxyUrl,
  proxySupabaseRequest
};