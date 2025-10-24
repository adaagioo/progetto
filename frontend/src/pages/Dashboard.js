import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { API } from '../App';
import { useCurrency } from '../contexts/CurrencyContext';
import { useTranslation } from 'react-i18next';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { TrendingUp, TrendingDown, AlertTriangle, Package, AlertCircle } from 'lucide-react';
import { toast } from 'sonner';

function Dashboard() {
  const { t } = useTranslation();
  const { format, formatMinor } = useCurrency();
  const navigate = useNavigate();
  const [kpis, setKpis] = useState(null);
  const [valuationSummary, setValuationSummary] = useState(null);
  const [totalInventoryValue, setTotalInventoryValue] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadingTotal, setLoadingTotal] = useState(true);
  const [totalError, setTotalError] = useState(false);

  useEffect(() => {
    fetchKPIs();
    fetchValuation();
    fetchTotalInventoryValue();
  }, []);

  const fetchKPIs = async () => {
    try {
      const response = await axios.get(`${API}/dashboard/kpis`);
      setKpis(response.data);
    } catch (error) {
      toast.error('Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  const fetchValuation = async () => {
    try {
      // Fetch all category valuations in parallel
      const [foodRes, beverageRes, nonfoodRes] = await Promise.all([
        axios.get(`${API}/inventory/valuation/food`),
        axios.get(`${API}/inventory/valuation/beverage`),
        axios.get(`${API}/inventory/valuation/nonfood`)
      ]);
      
      setValuationSummary({
        categories: {
          food: foodRes.data.value || 0,
          beverage: beverageRes.data.value || 0,
          nofood: nonfoodRes.data.value || 0
        }
      });
    } catch (error) {
      console.error('Failed to load valuation:', error);
    }
  };

  const fetchTotalInventoryValue = async () => {
    try {
      setLoadingTotal(true);
      setTotalError(false);
      const response = await axios.get(`${API}/inventory/valuation/total`);
      console.log('Total Inventory Value Response:', response.data, 'RequestId:', response.headers['x-request-id']);
      setTotalInventoryValue(response.data);
    } catch (error) {
      console.error('Failed to load total inventory value:', error);
      setTotalError(true);
    } finally {
      setLoadingTotal(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-lg text-emerald-600">{t('common.loading')}</div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="dashboard-page">
      <div>
        <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold gradient-text mb-2">
          {t('dashboard.title')}
        </h1>
        <p className="text-base text-gray-600">{t('dashboard.subtitle')}</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Food Cost % */}
        <Card 
          className="glass-morphism border-0 card-hover cursor-pointer" 
          data-testid="food-cost-card"
          onClick={() => navigate('/recipes')}
        >
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">{t('dashboard.foodCost')}</CardTitle>
            {kpis?.foodCostPct > 35 ? (
              <TrendingUp className="h-5 w-5 text-red-500" />
            ) : (
              <TrendingDown className="h-5 w-5 text-emerald-500" />
            )}
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-emerald-600" data-testid="food-cost-value">
              {kpis?.foodCostPct || 0}%
            </div>
            <p className="text-xs text-gray-500 mt-1">
              {kpis?.foodCostPct > 35 ? t('dashboard.aboveTarget') : t('dashboard.withinTarget')}
            </p>
          </CardContent>
        </Card>

        {/* Low Stock Items */}
        <Card 
          className="glass-morphism border-0 card-hover cursor-pointer" 
          data-testid="low-stock-card"
          onClick={() => navigate('/inventory?filter=lowStock')}
        >
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">{t('dashboard.lowStock')}</CardTitle>
            <Package className="h-5 w-5 text-amber-500" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-amber-600" data-testid="low-stock-value">
              {kpis?.lowStockCount || 0}
            </div>
            <p className="text-xs text-gray-500 mt-1">{t('dashboard.needReorder')}</p>
          </CardContent>
        </Card>

        {/* Expiring Items */}
        <Card 
          className="glass-morphism border-0 card-hover cursor-pointer" 
          data-testid="expiring-card"
          onClick={() => navigate('/inventory?filter=expiring')}
        >
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">{t('dashboard.expiringSoon')}</CardTitle>
            <AlertTriangle className="h-5 w-5 text-orange-500" />
          </CardHeader>
          <CardContent>
            <div className="space-y-1">
              <div className="flex justify-between items-center">
                <span className="text-xs text-gray-500">1 day:</span>
                <span className="text-sm font-semibold text-red-600" data-testid="expiring-1day">
                  {kpis?.expiring1Day || 0}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-xs text-gray-500">2 days:</span>
                <span className="text-sm font-semibold text-orange-600" data-testid="expiring-2day">
                  {kpis?.expiring2Day || 0}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-xs text-gray-500">3 days:</span>
                <span className="text-sm font-semibold text-amber-600" data-testid="expiring-3day">
                  {kpis?.expiring3Day || 0}
                </span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Gross Margin */}
        <Card 
          className="glass-morphism border-0 card-hover cursor-pointer" 
          data-testid="gross-margin-card"
          onClick={() => navigate('/profit-loss')}
        >
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">{t('dashboard.lastMonthGM')}</CardTitle>
            <TrendingUp className="h-5 w-5 text-emerald-500" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-emerald-600" data-testid="gross-margin-value">
              {format.number(kpis?.lastMonthGrossMargin || 0)}
            </div>
            <p className="text-xs text-gray-500 mt-1">{t('dashboard.previousMonth')}</p>
          </CardContent>
        </Card>
      </div>

      {/* Inventory Valuation by Category */}
      <div>
        <h2 className="text-xl font-bold mb-4">{t('dashboard.inventoryValuation') || 'Inventory Valuation'}</h2>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {valuationSummary ? (
            <>
              <Card 
                className="glass-morphism border-0 card-hover cursor-pointer" 
                onClick={() => navigate('/inventory?category=food')}
              >
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-gray-600">
                    {t('inventory.valuation.food') || 'Food Inventory'}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold text-green-600">
                    {formatMinor(valuationSummary.categories.food)}
                  </div>
                  <p className="text-xs text-gray-500 mt-1">{t('dashboard.clickToView') || 'Click to view'}</p>
                </CardContent>
              </Card>

              <Card 
                className="glass-morphism border-0 card-hover cursor-pointer"
                onClick={() => navigate('/inventory?category=beverage')}
              >
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-gray-600">
                    {t('inventory.valuation.beverage') || 'Beverage Inventory'}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold text-blue-600">
                    {formatMinor(valuationSummary.categories.beverage)}
                  </div>
                  <p className="text-xs text-gray-500 mt-1">{t('dashboard.clickToView') || 'Click to view'}</p>
                </CardContent>
              </Card>

              <Card 
                className="glass-morphism border-0 card-hover cursor-pointer"
                onClick={() => navigate('/inventory?category=nofood')}
              >
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-gray-600">
                    {t('inventory.valuation.nofood') || 'Non-Food Inventory'}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold text-gray-600">
                    {formatMinor(valuationSummary.categories.nofood)}
                  </div>
                  <p className="text-xs text-gray-500 mt-1">{t('dashboard.clickToView') || 'Click to view'}</p>
                </CardContent>
              </Card>
            </>
          ) : (
            <>
              {/* Skeleton cards for category cards when loading */}
              <Card className="glass-morphism border-0">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-gray-600">
                    {t('inventory.valuation.food') || 'Food Inventory'}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold text-gray-400 animate-pulse">⋯</div>
                </CardContent>
              </Card>
              <Card className="glass-morphism border-0">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-gray-600">
                    {t('inventory.valuation.beverage') || 'Beverage Inventory'}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold text-gray-400 animate-pulse">⋯</div>
                </CardContent>
              </Card>
              <Card className="glass-morphism border-0">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-gray-600">
                    {t('inventory.valuation.nofood') || 'Non-Food Inventory'}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold text-gray-400 animate-pulse">⋯</div>
                </CardContent>
              </Card>
            </>
          )}

          {/* Total Inventory Value Card - ALWAYS VISIBLE */}
          <Card 
            className="glass-morphism border-0 bg-gradient-to-br from-emerald-500 to-teal-600 text-white cursor-pointer"
            onClick={() => navigate('/inventory')}
            data-testid="total-inventory-value-card"
          >
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-white/90">
                {t('dashboard.totalInventoryValue') || 'Total Inventory Value'}
              </CardTitle>
            </CardHeader>
            <CardContent>
              {loadingTotal ? (
                <>
                  <div className="text-2xl font-bold animate-pulse">
                    ⋯
                  </div>
                  <p className="text-xs text-white/80 mt-1">Loading...</p>
                </>
              ) : totalError ? (
                <>
                  <div className="text-lg font-medium text-white/90 mb-2">
                    {t('dashboard.couldNotLoadTotal') || 'Couldn\'t load total'}
                  </div>
                  <button 
                    onClick={(e) => {
                      e.stopPropagation();
                      fetchTotalInventoryValue();
                    }}
                    className="text-sm underline text-white/80 hover:text-white"
                  >
                    {t('dashboard.retry') || 'Retry'}
                  </button>
                </>
              ) : totalInventoryValue && (totalInventoryValue.totalValue !== undefined && totalInventoryValue.totalValue !== null) ? (
                <>
                  <div className="text-2xl font-bold text-white">
                    {formatMinor(totalInventoryValue.totalValue || 0)}
                  </div>
                  <p className="text-xs text-white/80 mt-1">
                    {t('dashboard.asOfNow') || 'as of now'}
                  </p>
                  {totalInventoryValue.negativeCount > 0 && (
                    <div 
                      className="mt-2 text-xs bg-red-500/20 border border-red-300/30 rounded px-2 py-1 flex items-center gap-1 cursor-pointer hover:bg-red-500/30 transition-colors"
                      onClick={(e) => {
                        e.stopPropagation();
                        navigate('/inventory?filter=negative');
                      }}
                    >
                      <AlertTriangle className="h-3 w-3" />
                      {t('dashboard.negativeStockWarning', { count: totalInventoryValue.negativeCount }) || 
                        `${totalInventoryValue.negativeCount} item(s) with negative stock`}
                    </div>
                  )}
                </>
              ) : (
                <>
                  <div className="text-2xl font-bold text-white">€0.00</div>
                  <p className="text-xs text-white/80 mt-1">
                    {t('dashboard.asOfNow') || 'as of now'}
                  </p>
                </>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Revenue & COGS Summary */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card 
          className="glass-morphism border-0 cursor-pointer" 
          data-testid="revenue-card"
          onClick={() => navigate('/sales')}
        >
          <CardHeader>
            <CardTitle className="text-lg">{t('dashboard.totalRevenue')}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-4xl font-bold text-emerald-600" data-testid="total-revenue">
              {format.number(kpis?.totalRevenue || 0)}
            </div>
            <p className="text-sm text-gray-500 mt-2">{t('dashboard.fromAllSales')}</p>
          </CardContent>
        </Card>

        <Card 
          className="glass-morphism border-0 cursor-pointer" 
          data-testid="cogs-card"
          onClick={() => navigate('/receiving')}
        >
          <CardHeader>
            <CardTitle className="text-lg">{t('dashboard.totalCogs')}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-4xl font-bold text-orange-600" data-testid="total-cogs">
              {format.number(kpis?.totalCogs || 0)}
            </div>
            <p className="text-sm text-gray-500 mt-2">{t('dashboard.costOfGoods')}</p>
          </CardContent>
        </Card>
      </div>

      {/* {t('dashboard.tips')} */}
      <Card className="glass-morphism border-0" data-testid="tips-card">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <AlertCircle className="h-5 w-5 text-emerald-500" />
            {t('dashboard.tips')}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="space-y-2 text-sm text-gray-600">
            <li className="flex items-start gap-2">
              <span className="text-emerald-500 mt-0.5">•</span>
              <span>Keep food cost percentage below 35% for optimal profitability</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-emerald-500 mt-0.5">•</span>
              <span>Check inventory daily for items expiring within 3 days</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-emerald-500 mt-0.5">•</span>
              <span>Reorder ingredients when stock falls below minimum quantity</span>
            </li>
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}

export default Dashboard;