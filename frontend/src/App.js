import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import axios from 'axios';
import './i18n'; // Initialize i18n
import '@/App.css';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Recipes from './pages/Recipes';
import Inventory from './pages/Inventory';
import Sales from './pages/Sales';
import Wastage from './pages/Wastage';
import ProfitLoss from './pages/ProfitLoss';
import Ingredients from './pages/Ingredients';
import Settings from './pages/Settings';
import Suppliers from './pages/Suppliers';
import Receiving from './pages/Receiving';
import ForgotPassword from './pages/ForgotPassword';
import ResetPassword from './pages/ResetPassword';
import Layout from './components/Layout';
import { Toaster } from './components/ui/sonner';
import { CurrencyProvider } from './contexts/CurrencyContext';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

export const AuthContext = React.createContext();

function App() {
  const [user, setUser] = useState(null);
  const [restaurant, setRestaurant] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      fetchUser();
    } else {
      setLoading(false);
    }
  }, []);

  const fetchUser = async () => {
    try {
      const response = await axios.get(`${API}/auth/me`);
      setUser(response.data);
      
      // Fetch restaurant data
      const restaurantResponse = await axios.get(`${API}/restaurant`);
      setRestaurant(restaurantResponse.data);
    } catch (error) {
      console.error('Failed to fetch user:', error);
      localStorage.removeItem('token');
      delete axios.defaults.headers.common['Authorization'];
    } finally {
      setLoading(false);
    }
  };

  const login = async (token, userData) => {
    localStorage.setItem('token', token);
    axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    setUser(userData);
    
    // Fetch restaurant data after login
    try {
      const restaurantResponse = await axios.get(`${API}/restaurant`);
      setRestaurant(restaurantResponse.data);
    } catch (error) {
      console.error('Failed to fetch restaurant:', error);
    }
  };

  const logout = () => {
    localStorage.removeItem('token');
    delete axios.defaults.headers.common['Authorization'];
    setUser(null);
    setRestaurant(null);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-emerald-50 to-teal-50">
        <div className="text-xl text-emerald-600">Loading...</div>
      </div>
    );
  }

  return (
    <AuthContext.Provider value={{ user, setUser, restaurant, setRestaurant, login, logout }}>
      <CurrencyProvider user={user} restaurant={restaurant}>
        <BrowserRouter>
          <Toaster position="top-right" />
          <Routes>
            <Route path="/login" element={user ? <Navigate to="/" /> : <Login />} />
            <Route path="/forgot-password" element={user ? <Navigate to="/" /> : <ForgotPassword />} />
            <Route path="/reset" element={user ? <Navigate to="/" /> : <ResetPassword />} />
            <Route
              path="/"
              element={user ? <Layout><Dashboard /></Layout> : <Navigate to="/login" />}
            />
          <Route
            path="/recipes"
            element={user ? <Layout><Recipes /></Layout> : <Navigate to="/login" />}
          />
          <Route
            path="/ingredients"
            element={user ? <Layout><Ingredients /></Layout> : <Navigate to="/login" />}
          />
          <Route
            path="/inventory"
            element={user ? <Layout><Inventory /></Layout> : <Navigate to="/login" />}
          />
          <Route
            path="/sales"
            element={user ? <Layout><Sales /></Layout> : <Navigate to="/login" />}
          />
          <Route
            path="/wastage"
            element={user ? <Layout><Wastage /></Layout> : <Navigate to="/login" />}
          />
          <Route
            path="/profit-loss"
            element={user ? <Layout><ProfitLoss /></Layout> : <Navigate to="/login" />}
          />
          <Route
            path="/suppliers"
            element={user ? <Layout><Suppliers /></Layout> : <Navigate to="/login" />}
          />
          <Route
            path="/receiving"
            element={user ? <Layout><Receiving /></Layout> : <Navigate to="/login" />}
          />
          <Route
            path="/settings"
            element={user ? <Layout><Settings /></Layout> : <Navigate to="/login" />}
          />
        </Routes>
      </BrowserRouter>
    </CurrencyProvider>
    </AuthContext.Provider>
  );
}

export default App;