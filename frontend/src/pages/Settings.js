import React, { useState, useEffect, useContext } from 'react';
import axios from 'axios';
import { API, AuthContext } from '../App';
import { useTranslation } from 'react-i18next';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Settings as SettingsIcon, Globe, DollarSign, Check } from 'lucide-react';
import { toast } from 'sonner';

function Settings() {
  const { t, i18n } = useTranslation();
  const { user, setUser } = useContext(AuthContext);
  const [restaurant, setRestaurant] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetchRestaurant();
  }, []);

  // Set initial language from user locale
  useEffect(() => {
    if (user?.locale) {
      const lang = user.locale.split('-')[0];
      i18n.changeLanguage(lang);
    }
  }, [user, i18n]);

  const fetchRestaurant = async () => {
    try {
      const response = await axios.get(`${API}/restaurant`);
      setRestaurant(response.data);
    } catch (error) {
      toast.error('Failed to load restaurant data');
    } finally {
      setLoading(false);
    }
  };

  const handleLocaleChange = async (newLocale) => {
    try {
      await axios.put(`${API}/auth/locale`, { locale: newLocale });
      
      // Update local user state
      const updatedUser = { ...user, locale: newLocale };
      setUser(updatedUser);
      
      // Change i18n language
      const lang = newLocale.split('-')[0];
      i18n.changeLanguage(lang);
      
      toast.success(t('msg.updated'));
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update locale');
    }
  };

  const handleCurrencyChange = async (currencyCode) => {
    if (!restaurant) return;

    setSaving(true);
    try {
      const currencyConfig = {
        EUR: { code: 'EUR', symbol: '€', decimals: 2 },
        USD: { code: 'USD', symbol: '$', decimals: 2 }
      };

      await axios.put(`${API}/restaurant`, {
        currency: currencyConfig[currencyCode]
      });

      setRestaurant({
        ...restaurant,
        currency: currencyConfig[currencyCode]
      });

      toast.success(t('msg.updated'));
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update currency');
    } finally {
      setSaving(false);
    }
  };

  const handleRestaurantNameUpdate = async (e) => {
    e.preventDefault();
    if (!restaurant) return;

    setSaving(true);
    try {
      const formData = new FormData(e.target);
      const name = formData.get('name');

      await axios.put(`${API}/restaurant`, { name });

      setRestaurant({ ...restaurant, name });
      toast.success(t('msg.updated'));
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update restaurant');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-lg text-emerald-600">{t('common.loading')}</div>
      </div>
    );
  }

  const currentLocale = user?.locale || 'en-US';
  const currentCurrency = restaurant?.currency?.code || 'EUR';
  const currentLang = currentLocale.split('-')[0];

  return (
    <div className="space-y-6" data-testid="settings-page">
      <div>
        <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold gradient-text mb-2">
          {t('settings.title')}
        </h1>
        <p className="text-base text-gray-600">{t('settings.general')}</p>
      </div>

      <Tabs defaultValue="general" className="w-full">
        <TabsList className="grid w-full grid-cols-2 lg:w-auto lg:inline-grid">
          <TabsTrigger value="general" data-testid="general-tab">
            <SettingsIcon className="w-4 h-4 mr-2" />
            General
          </TabsTrigger>
          <TabsTrigger value="localization" data-testid="localization-tab">
            <Globe className="w-4 h-4 mr-2" />
            Language & Currency
          </TabsTrigger>
        </TabsList>

        <TabsContent value=\"general\" className=\"space-y-4\">
          <Card className=\"glass-morphism border-0\">
            <CardHeader>
              <CardTitle>{t('settings.restaurant')}</CardTitle>
              <CardDescription>Manage your restaurant information</CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleRestaurantNameUpdate} className=\"space-y-4\">
                <div className=\"space-y-2\">
                  <Label htmlFor=\"name\">Restaurant Name</Label>
                  <Input
                    id=\"name\"
                    name=\"name\"
                    defaultValue={restaurant?.name}
                    required
                    data-testid=\"restaurant-name-input\"
                    className=\"input-focus\"
                  />
                </div>

                <div className=\"space-y-2\">
                  <Label>Subscription Plan</Label>
                  <div className=\"flex items-center gap-2 p-3 bg-emerald-50 rounded-lg\">
                    <Check className=\"w-5 h-5 text-emerald-600\" />
                    <span className=\"font-semibold text-emerald-600\" data-testid=\"plan-display\">
                      {restaurant?.plan}
                    </span>
                  </div>
                </div>

                <div className=\"space-y-2\">
                  <Label>Status</Label>
                  <div className=\"flex items-center gap-2 p-3 bg-green-50 rounded-lg\">
                    <div className=\"w-2 h-2 bg-green-500 rounded-full\"></div>
                    <span className=\"font-medium text-green-700\" data-testid=\"status-display\">
                      {restaurant?.subscriptionStatus === 'active' ? 'Active' : restaurant?.subscriptionStatus}
                    </span>
                  </div>
                </div>

                <Button 
                  type=\"submit\" 
                  className=\"btn-primary text-white\"
                  disabled={saving}
                  data-testid=\"save-restaurant-button\"
                >
                  {saving ? 'Saving...' : t('common.save')}
                </Button>
              </form>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value=\"localization\" className=\"space-y-4\">
          <Card className=\"glass-morphism border-0\">
            <CardHeader>
              <CardTitle className=\"flex items-center gap-2\">
                <Globe className=\"w-5 h-5 text-emerald-500\" />
                {t('settings.locale')}
              </CardTitle>
              <CardDescription>Choose your preferred language</CardDescription>
            </CardHeader>
            <CardContent className=\"space-y-4\">
              <div className=\"grid grid-cols-1 md:grid-cols-2 gap-3\">
                <button
                  onClick={() => handleLocaleChange('en-US')}
                  className={`flex items-center justify-between p-4 rounded-lg border-2 transition-all ${
                    currentLocale === 'en-US'
                      ? 'border-emerald-500 bg-emerald-50'
                      : 'border-gray-200 hover:border-emerald-300'
                  }`}
                  data-testid=\"locale-en-button\"
                >
                  <div className=\"flex items-center gap-3\">
                    <span className=\"text-2xl\">🇺🇸</span>
                    <div className=\"text-left\">
                      <div className=\"font-semibold\">English</div>
                      <div className=\"text-sm text-gray-500\">United States</div>
                    </div>
                  </div>
                  {currentLocale === 'en-US' && (
                    <Check className=\"w-5 h-5 text-emerald-600\" />
                  )}
                </button>

                <button
                  onClick={() => handleLocaleChange('it-IT')}
                  className={`flex items-center justify-between p-4 rounded-lg border-2 transition-all ${
                    currentLocale === 'it-IT'
                      ? 'border-emerald-500 bg-emerald-50'
                      : 'border-gray-200 hover:border-emerald-300'
                  }`}
                  data-testid=\"locale-it-button\"
                >
                  <div className=\"flex items-center gap-3\">
                    <span className=\"text-2xl\">🇮🇹</span>
                    <div className=\"text-left\">
                      <div className=\"font-semibold\">Italiano</div>
                      <div className=\"text-sm text-gray-500\">Italia</div>
                    </div>
                  </div>
                  {currentLocale === 'it-IT' && (
                    <Check className=\"w-5 h-5 text-emerald-600\" />
                  )}
                </button>
              </div>

              <div className=\"p-4 bg-blue-50 rounded-lg\">
                <p className=\"text-sm text-blue-800\">
                  <strong>Current:</strong> {currentLocale === 'en-US' ? 'English (US)' : 'Italiano (IT)'}
                </p>
              </div>
            </CardContent>
          </Card>

          <Card className=\"glass-morphism border-0\">
            <CardHeader>
              <CardTitle className=\"flex items-center gap-2\">
                <DollarSign className=\"w-5 h-5 text-emerald-500\" />
                {t('settings.currency')}
              </CardTitle>
              <CardDescription>Set your restaurant's default currency</CardDescription>
            </CardHeader>
            <CardContent className=\"space-y-4\">
              <div className=\"grid grid-cols-1 md:grid-cols-2 gap-3\">
                <button
                  onClick={() => handleCurrencyChange('EUR')}
                  className={`flex items-center justify-between p-4 rounded-lg border-2 transition-all ${
                    currentCurrency === 'EUR'
                      ? 'border-emerald-500 bg-emerald-50'
                      : 'border-gray-200 hover:border-emerald-300'
                  }`}
                  disabled={saving}
                  data-testid=\"currency-eur-button\"
                >
                  <div className=\"flex items-center gap-3\">
                    <span className=\"text-3xl font-bold text-emerald-600\">€</span>
                    <div className=\"text-left\">
                      <div className=\"font-semibold\">Euro (EUR)</div>
                      <div className=\"text-sm text-gray-500\">European Union</div>
                    </div>
                  </div>
                  {currentCurrency === 'EUR' && (
                    <Check className=\"w-5 h-5 text-emerald-600\" />
                  )}
                </button>

                <button
                  onClick={() => handleCurrencyChange('USD')}
                  className={`flex items-center justify-between p-4 rounded-lg border-2 transition-all ${
                    currentCurrency === 'USD'
                      ? 'border-emerald-500 bg-emerald-50'
                      : 'border-gray-200 hover:border-emerald-300'
                  }`}
                  disabled={saving}
                  data-testid=\"currency-usd-button\"
                >
                  <div className=\"flex items-center gap-3\">
                    <span className=\"text-3xl font-bold text-emerald-600\">$</span>
                    <div className=\"text-left\">
                      <div className=\"font-semibold\">US Dollar (USD)</div>
                      <div className=\"text-sm text-gray-500\">United States</div>
                    </div>
                  </div>
                  {currentCurrency === 'USD' && (
                    <Check className=\"w-5 h-5 text-emerald-600\" />
                  )}
                </button>
              </div>

              <div className=\"p-4 bg-blue-50 rounded-lg\">
                <p className=\"text-sm text-blue-800\">
                  <strong>Current:</strong> {currentCurrency} ({restaurant?.currency?.symbol})
                </p>
                <p className=\"text-xs text-blue-600 mt-1\">
                  All monetary values will be displayed in this currency
                </p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}

export default Settings;
