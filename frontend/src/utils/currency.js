/**
 * Currency utilities for frontend
 * Handles formatting and parsing with locale support
 */

export const CURRENCY_CONFIG = {
  EUR: { symbol: '€', decimals: 2, minorUnit: 100 },
  USD: { symbol: '$', decimals: 2, minorUnit: 100 }
};

/**
 * Format amount with locale-aware formatting
 * @param {number} minorUnits - Amount in minor units (cents)
 * @param {string} currencyCode - Currency code (EUR, USD)
 * @param {string} locale - Locale for formatting (en-US, it-IT)
 * @returns {string} Formatted amount
 */
export function formatCurrency(minorUnits, currencyCode = 'EUR', locale = 'en-US') {
  if (minorUnits === null || minorUnits === undefined) return '-';
  
  const config = CURRENCY_CONFIG[currencyCode] || CURRENCY_CONFIG.EUR;
  const decimalAmount = minorUnits / config.minorUnit;
  
  try {
    return new Intl.NumberFormat(locale, {
      style: 'currency',
      currency: currencyCode,
      minimumFractionDigits: config.decimals,
      maximumFractionDigits: config.decimals
    }).format(decimalAmount);
  } catch (error) {
    // Fallback if locale not supported
    return `${config.symbol}${decimalAmount.toFixed(config.decimals)}`;
  }
}

/**
 * Format number with locale-aware formatting
 * @param {number} value - Number to format
 * @param {string} locale - Locale for formatting
 * @param {number} decimals - Decimal places
 * @returns {string} Formatted number
 */
export function formatNumber(value, locale = 'en-US', decimals = 2) {
  if (value === null || value === undefined) return '-';
  
  try {
    return new Intl.NumberFormat(locale, {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals
    }).format(value);
  } catch (error) {
    return value.toFixed(decimals);
  }
}

/**
 * Format date with locale-aware formatting
 * @param {string|Date} date - Date to format
 * @param {string} locale - Locale for formatting
 * @returns {string} Formatted date
 */
export function formatDate(date, locale = 'en-US') {
  if (!date) return '-';
  
  try {
    const dateObj = typeof date === 'string' ? new Date(date) : date;
    return new Intl.DateTimeFormat(locale, {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    }).format(dateObj);
  } catch (error) {
    return date.toString();
  }
}

/**
 * Parse decimal input to minor units
 * @param {string} input - User input (e.g., "8.50" or "8,50")
 * @param {string} currencyCode - Currency code
 * @returns {number} Amount in minor units
 */
export function parseToMinorUnits(input, currencyCode = 'EUR') {
  if (!input) return 0;
  
  const config = CURRENCY_CONFIG[currencyCode] || CURRENCY_CONFIG.EUR;
  
  // Normalize comma/dot for decimal separator
  const normalized = input.toString().replace(',', '.');
  const decimal = parseFloat(normalized);
  
  if (isNaN(decimal)) return 0;
  
  return Math.round(decimal * config.minorUnit);
}

/**
 * Convert minor units to decimal for display in input
 * @param {number} minorUnits - Amount in minor units
 * @param {string} currencyCode - Currency code
 * @returns {string} Decimal string
 */
export function fromMinorUnits(minorUnits, currencyCode = 'EUR') {
  if (minorUnits === null || minorUnits === undefined) return '';
  
  const config = CURRENCY_CONFIG[currencyCode] || CURRENCY_CONFIG.EUR;
  return (minorUnits / config.minorUnit).toFixed(config.decimals);
}

/**
 * Get currency symbol
 * @param {string} currencyCode - Currency code
 * @returns {string} Currency symbol
 */
export function getCurrencySymbol(currencyCode = 'EUR') {
  return CURRENCY_CONFIG[currencyCode]?.symbol || '€';
}
