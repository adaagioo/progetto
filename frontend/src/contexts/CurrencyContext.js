import React, { createContext, useContext, useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { formatCurrency, formatNumber, formatDate } from '../utils/currency';

const CurrencyContext = createContext();

export const useCurrency = () => {
  const context = useContext(CurrencyContext);
  if (!context) {
    throw new Error('useCurrency must be used within CurrencyProvider');
  }
  return context;
};

export const CurrencyProvider = ({ children, user, restaurant }) => {
  const { i18n } = useTranslation();
  const [currency, setCurrency] = useState('EUR');
  const [locale, setLocale] = useState('en-US');

  useEffect(() => {
    // Set currency from restaurant
    if (restaurant?.currency?.code) {
      setCurrency(restaurant.currency.code);
    }
    
    // Set locale from user, fallback to restaurant default
    const userLocale = user?.locale || restaurant?.defaultLocale || 'en-US';
    setLocale(userLocale);
    
    // Update i18n language
    const lang = userLocale.split('-')[0];
    i18n.changeLanguage(lang);
  }, [user, restaurant, i18n]);

  const format = {
    currency: (minorUnits) => formatCurrency(minorUnits, currency, locale),
    number: (value, decimals = 2) => formatNumber(value, locale, decimals),
    date: (date) => formatDate(date, locale)
  };

  // Alias for currency formatter (for backward compatibility and clarity)
  const formatMinor = (minorUnits) => formatCurrency(minorUnits, currency, locale);

  return (
    <CurrencyContext.Provider value={{ currency, locale, format, formatMinor }}>
      {children}
    </CurrencyContext.Provider>
  );
};
