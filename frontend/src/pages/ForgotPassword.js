import React, { useState } from 'react';
import axios from 'axios';
import { API } from '../App';
import { Link } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { ChefHat, ArrowLeft } from 'lucide-react';
import { toast } from 'sonner';

function ForgotPassword() {
  const [email, setEmail] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      await axios.post(`${API}/auth/forgot`, { email });
      setSubmitted(true);
      toast.success('Password reset email sent!');
    } catch (error) {
      if (error.response?.status === 429) {
        toast.error('Too many requests. Please try again later.');
      } else {
        toast.error(error.response?.data?.detail || 'Failed to send reset email');
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-gradient-to-br from-emerald-50 via-teal-50 to-green-50">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-emerald-500 to-teal-600 rounded-2xl mb-4 shadow-lg">
            <ChefHat className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-4xl font-bold gradient-text mb-2">RistoBrain</h1>
          <p className="text-gray-600">Reset your password</p>
        </div>

        <Card className="glass-morphism border-0 shadow-xl">
          <CardHeader>
            <CardTitle>Forgot Password</CardTitle>
            <CardDescription>
              {submitted ? 'Check your email' : 'Enter your email address'}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {submitted ? (
              <div className="space-y-4">
                <div className="p-4 bg-emerald-50 rounded-lg text-center">
                  <p className="text-sm text-emerald-800">
                    If an account exists with <strong>{email}</strong>, you will receive a password reset link shortly.
                  </p>
                </div>
                <Link to="/login">
                  <Button className="w-full btn-primary text-white" data-testid="back-to-login-button">
                    <ArrowLeft className="w-4 h-4 mr-2" />
                    Back to Login
                  </Button>
                </Link>
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="space-y-4" data-testid="forgot-password-form">
                <div className="space-y-2">
                  <Label htmlFor="email">Email</Label>
                  <Input
                    id="email"
                    type="email"
                    placeholder="chef@restaurant.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    data-testid="forgot-email-input"
                    className="input-focus"
                  />
                </div>
                <Button
                  type="submit"
                  className="w-full btn-primary text-white"
                  disabled={isLoading}
                  data-testid="send-reset-button"
                >
                  {isLoading ? 'Sending...' : 'Send Reset Link'}
                </Button>
                <Link to="/login">
                  <Button variant="ghost" className="w-full" data-testid="cancel-button">
                    <ArrowLeft className="w-4 h-4 mr-2" />
                    Back to Login
                  </Button>
                </Link>
              </form>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

export default ForgotPassword;