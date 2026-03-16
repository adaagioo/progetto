/**
 * Extracts a displayable error message from API error responses
 * Handles both string errors and Pydantic validation error arrays
 * 
 * @param {Error} error - Axios error object
 * @param {string} fallback - Fallback message if extraction fails
 * @returns {string} - Human-readable error message
 */
export function getErrorMessage(error, fallback = 'An error occurred') {
  const detail = error?.response?.data?.detail;
  
  if (!detail) {
    return fallback;
  }
  
  // String error message (normal case)
  if (typeof detail === 'string') {
    return detail;
  }
  
  // Pydantic validation error array
  if (Array.isArray(detail) && detail.length > 0) {
    // Extract message from first validation error
    const firstError = detail[0];
    if (firstError?.msg) {
      return firstError.msg;
    }
    // Fallback: stringify if msg not found
    return JSON.stringify(firstError);
  }
  
  // Object with message property
  if (typeof detail === 'object' && detail.msg) {
    return detail.msg;
  }
  
  // Unknown format, return fallback
  return fallback;
}
