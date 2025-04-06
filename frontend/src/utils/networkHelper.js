/**
 * Network Helper Utility
 * 
 * Provides functions to help with network connectivity issues,
 * specifically for Supabase authentication.
 */

// Default ports for Supabase - Try 54323 first (the port specified)
const COMMON_SUPABASE_PORTS = [54323, 54321, 54322, 8000, 3000];

// All potential Supabase URLs to try
export const POTENTIAL_SUPABASE_URLS = [
  // IPv4 localhost (prioritized for direct development)
  ...COMMON_SUPABASE_PORTS.map(port => `http://127.0.0.1:${port}`),
  // Named localhost
  ...COMMON_SUPABASE_PORTS.map(port => `http://localhost:${port}`),
  // IPv6 localhost
  ...COMMON_SUPABASE_PORTS.map(port => `http://[::1]:${port}`),
];

/**
 * Test connection to a given URL
 * @param {string} url - URL to test
 * @param {number} timeout - Timeout in milliseconds
 * @returns {Promise<boolean>} - Whether the connection was successful
 */
export const testConnection = async (url, timeout = 5000) => {
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);
    
    // Test the base URL with no additional path
    const testUrl = url;
    
    console.log(`Testing connection to: ${testUrl}`);
    
    try {
      // First attempt with simple GET to the base URL
      const response = await fetch(testUrl, {
        method: 'GET',
        mode: 'no-cors', // This won't throw CORS errors
        cache: 'no-cache',
        credentials: 'omit', // Don't send cookies to avoid CORS issues
        signal: controller.signal,
        headers: {
          'Accept': 'application/json',
          'Cache-Control': 'no-cache'
        }
      });
      
      // With no-cors mode, we can't read the response,
      // but if we get here without error, connection works
      clearTimeout(timeoutId);
      console.log(`Connection to ${url} successful`);
      return true;
    } catch (initialError) {
      console.log(`Initial connection test failed: ${initialError.message}, trying alternative endpoint...`);
      
      // If that fails, try the auth health endpoint (common in Supabase)
      const healthUrl = url.endsWith('/') ? `${url}auth/v1/health` : `${url}/auth/v1/health`;
      await fetch(healthUrl, {
        method: 'GET',
        mode: 'no-cors',
        cache: 'no-cache',
        credentials: 'omit',
        signal: controller.signal,
      });
      
      // If we get here, the health endpoint worked
      clearTimeout(timeoutId);
      console.log(`Connection to ${url} successful via health endpoint`);
      return true;
    }
  } catch (error) {
    console.log(`Connection to ${url} failed:`, error.message);
    return false;
  }
};

/**
 * Find working Supabase URL by testing connections
 * @returns {Promise<string|null>} - Working URL or null if none found
 */
export const findWorkingSupabaseUrl = async () => {
  console.log('Testing Supabase URLs...');
  
  // First try the configured URL if available
  const configuredUrl = process.env.REACT_APP_SUPABASE_URL;
  if (configuredUrl) {
    console.log(`Testing configured URL: ${configuredUrl}`);
    if (await testConnection(configuredUrl)) {
      console.log(`Using configured Supabase URL: ${configuredUrl}`);
      return configuredUrl;
    }
  }
  
  // Try all potential URLs
  for (const url of POTENTIAL_SUPABASE_URLS) {
    if (await testConnection(url)) {
      console.log(`Found working Supabase URL: ${url}`);
      return url;
    }
  }
  
  console.error('No working Supabase URL found');
  // Return the configured URL as a fallback
  return configuredUrl || 'http://127.0.0.1:54321';
};

export default {
  testConnection,
  findWorkingSupabaseUrl,
  POTENTIAL_SUPABASE_URLS
};