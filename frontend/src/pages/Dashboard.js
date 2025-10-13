import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { API } from '../App';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { TrendingUp, TrendingDown, AlertTriangle, DollarSign, Package, AlertCircle } from 'lucide-react';
import { toast } from 'sonner';

function Dashboard() {
  const [kpis, setKpis] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchKPIs();
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

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-lg text-emerald-600">Loading dashboard...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="dashboard-page">
      <div>
        <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold gradient-text mb-2">
          Dashboard
        </h1>
        <p className="text-base text-gray-600">Overview of your restaurant performance</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Food Cost % */}
        <Card className="glass-morphism border-0 card-hover" data-testid="food-cost-card">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">Food Cost %</CardTitle>
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
              {kpis?.foodCostPct > 35 ? 'Above target' : 'Within target'}
            </p>
          </CardContent>
        </Card>

        {/* Low Stock Items */}
        <Card className="glass-morphism border-0 card-hover" data-testid="low-stock-card">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">Low Stock</CardTitle>
            <Package className="h-5 w-5 text-amber-500" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-amber-600" data-testid="low-stock-value">
              {kpis?.lowStockCount || 0}
            </div>
            <p className="text-xs text-gray-500 mt-1">Items need reordering</p>
          </CardContent>
        </Card>

        {/* Expiring Items */}
        <Card className="glass-morphism border-0 card-hover" data-testid="expiring-card">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">Expiring Soon</CardTitle>
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
        <Card className="glass-morphism border-0 card-hover" data-testid="gross-margin-card">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">Last Month GM</CardTitle>
            <DollarSign className="h-5 w-5 text-emerald-500" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-emerald-600" data-testid="gross-margin-value">
              ${kpis?.lastMonthGrossMargin || 0}
            </div>
            <p className="text-xs text-gray-500 mt-1">Previous month</p>
          </CardContent>
        </Card>
      </div>

      {/* Revenue & COGS Summary */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card className="glass-morphism border-0" data-testid="revenue-card">
          <CardHeader>
            <CardTitle className="text-lg">Total Revenue</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-4xl font-bold text-emerald-600" data-testid="total-revenue">
              ${kpis?.totalRevenue || 0}
            </div>
            <p className="text-sm text-gray-500 mt-2">From all sales</p>
          </CardContent>
        </Card>

        <Card className="glass-morphism border-0" data-testid="cogs-card">
          <CardHeader>
            <CardTitle className="text-lg">Total COGS</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-4xl font-bold text-orange-600" data-testid="total-cogs">
              ${kpis?.totalCogs || 0}
            </div>
            <p className="text-sm text-gray-500 mt-2">Cost of goods sold</p>
          </CardContent>
        </Card>
      </div>

      {/* Quick Tips */}
      <Card className="glass-morphism border-0" data-testid="tips-card">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <AlertCircle className="h-5 w-5 text-emerald-500" />
            Quick Tips
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