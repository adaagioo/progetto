import React, { useState, useEffect, useContext } from 'react';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import { TrendingUp, Calendar, Save, Plus, X, ChevronLeft, ChevronRight } from 'lucide-react';
import { useCurrency } from '../contexts/CurrencyContext';
import { AuthContext } from '../App';

function PLSnapshot() {
  const { t, i18n } = useTranslation();
  const { currency, formatMinor } = useCurrency();
  const { user } = useContext(AuthContext);
  const [loading, setLoading] = useState(false);
  const [snapshots, setSnapshots] = useState([]);
  const [selectedWeek, setSelectedWeek] = useState(null);
  const [formData, setFormData] = useState(null);
  const [isEditing, setIsEditing] = useState(false);

  // RBAC check
  const canEdit = user?.roleKey === 'admin' || user?.roleKey === 'manager';

  // Get current locale from i18n
  const currentLocale = i18n.language === 'it' ? 'it-IT' : 'en-US';

  // Initialize week picker with current week
  useEffect(() => {
    const today = new Date();
    // Get Monday of current week
    const monday = new Date(today);
    const day = monday.getDay();
    const diff = monday.getDate() - day + (day === 0 ? -6 : 1);
    monday.setDate(diff);
    
    // Get Sunday
    const sunday = new Date(monday);
    sunday.setDate(monday.getDate() + 6);
    
    setSelectedWeek({
      start: monday.toISOString().split('T')[0],
      end: sunday.toISOString().split('T')[0]
    });
  }, []);

  // Load snapshots
  useEffect(() => {
    if (selectedWeek) {
      loadSnapshots();
    }
  }, [selectedWeek]);

  const loadSnapshots = async () => {
    if (!selectedWeek) return;

    try {
      setLoading(true);
      const token = localStorage.getItem('token');
      const response = await fetch(
        `${process.env.REACT_APP_BACKEND_URL}/api/pl/snapshot?start_date=${selectedWeek.start}&end_date=${selectedWeek.end}`,
        {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }
      );

      if (response.ok) {
        const data = await response.json();
        setSnapshots(data);
        
        // If snapshot exists for this week, populate form
        if (data.length > 0) {
          setFormData(data[0]);
          setIsEditing(true);
        } else {
          // Initialize empty form
          initializeForm();
          setIsEditing(false);
        }
      }
    } catch (error) {
      console.error('Failed to load P&L snapshots:', error);
      toast.error(t('pl.error.load'));
    } finally {
      setLoading(false);
    }
  };

  const initializeForm = () => {
    setFormData({
      period: {
        start: selectedWeek.start,
        end: selectedWeek.end,
        timezone: 'Europe/Rome',
        granularity: 'WEEK'
      },
      currency: currency,
      displayLocale: currentLocale,
      sales_turnover: 0,
      sales_food_beverage: 0,
      sales_delivery: 0,
      cogs_food_beverage: 0,
      cogs_raw_waste: 0,
      opex_non_food: 0,
      opex_platforms: 0,
      labour_employees: 0,
      labour_staff_meal: 0,
      marketing_online_ads: 0,
      marketing_free_items: 0,
      rent_base_effective: 0,
      rent_garden: 0,
      other_total: 0,
      notes: ''
    });
  };

  // Navigate weeks
  const previousWeek = () => {
    const monday = new Date(selectedWeek.start);
    monday.setDate(monday.getDate() - 7);
    const sunday = new Date(monday);
    sunday.setDate(monday.getDate() + 6);
    
    setSelectedWeek({
      start: monday.toISOString().split('T')[0],
      end: sunday.toISOString().split('T')[0]
    });
  };

  const nextWeek = () => {
    const monday = new Date(selectedWeek.start);
    monday.setDate(monday.getDate() + 7);
    const sunday = new Date(monday);
    sunday.setDate(monday.getDate() + 6);
    
    setSelectedWeek({
      start: monday.toISOString().split('T')[0],
      end: sunday.toISOString().split('T')[0]
    });
  };

  // Format currency with locale
  const formatCurrency = (amount) => {
    return new Intl.NumberFormat(formData?.displayLocale || currentLocale, {
      style: 'currency',
      currency: formData?.currency || currency,
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(amount);
  };

  // Calculate percentages
  const calculatePercent = (amount) => {
    if (!formData?.sales_turnover || formData.sales_turnover === 0) return 0;
    return ((amount / formData.sales_turnover) * 100).toFixed(2);
  };

  // Calculate totals
  const calculateTotals = () => {
    if (!formData) return {};

    const cogs_total = formData.cogs_food_beverage + formData.cogs_raw_waste;
    const opex_total = formData.opex_non_food + formData.opex_platforms;
    const labour_total = formData.labour_employees + formData.labour_staff_meal;
    const marketing_total = formData.marketing_online_ads + formData.marketing_free_items;
    const rent_total = formData.rent_base_effective + formData.rent_garden;
    
    const kpi_ebitda = formData.sales_turnover - (
      cogs_total + opex_total + labour_total + marketing_total + rent_total + formData.other_total
    );

    return {
      cogs_total,
      opex_total,
      labour_total,
      marketing_total,
      rent_total,
      kpi_ebitda
    };
  };

  const totals = formData ? calculateTotals() : {};

  // Update field
  const updateField = (field, value) => {
    if (!canEdit) return;
    
    setFormData(prev => ({
      ...prev,
      [field]: parseFloat(value) || 0
    }));
  };

  // Save snapshot
  const handleSave = async () => {
    if (!formData || !canEdit) return;

    try {
      setLoading(true);
      const token = localStorage.getItem('token');
      
      // Calculate totals for backend
      const dataToSave = {
        ...formData,
        period: {
          start: selectedWeek.start,
          end: selectedWeek.end,
          timezone: 'Europe/Rome',
          granularity: 'WEEK'
        },
        currency: currency,
        displayLocale: currentLocale
      };

      const response = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/pl/snapshot`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(dataToSave)
      });

      if (response.ok) {
        const saved = await response.json();
        setFormData(saved);
        setIsEditing(true);
        toast.success(isEditing ? t('pl.success.updated') : t('pl.success.created'));
        loadSnapshots();
      } else {
        toast.error(t('pl.error.save'));
      }
    } catch (error) {
      console.error('Failed to save P&L snapshot:', error);
      toast.error(t('pl.error.save'));
    } finally {
      setLoading(false);
    }
  };

  // Format date range for display
  const formatDateRange = (start, end) => {
    const startDate = new Date(start);
    const endDate = new Date(end);
    return `${startDate.toLocaleDateString(currentLocale)} - ${endDate.toLocaleDateString(currentLocale)}`;
  };

  if (!selectedWeek) {
    return <div className="p-6">Loading...</div>;
  }

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold flex items-center gap-2">
              <TrendingUp className="h-8 w-8" />
              {t('pl.title')}
            </h1>
            <p className="text-gray-600 mt-1">{t('pl.subtitle')}</p>
          </div>
          {canEdit && formData && (
            <button
              onClick={handleSave}
              disabled={loading}
              className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 flex items-center gap-2"
            >
              <Save className="h-4 w-4" />
              {t('pl.save')}
            </button>
          )}
        </div>
      </div>

      {/* Week Picker */}
      <div className="mb-6 bg-white p-4 rounded-lg shadow">
        <div className="flex items-center justify-between">
          <button
            onClick={previousWeek}
            className="p-2 hover:bg-gray-100 rounded"
            data-testid="prev-week"
          >
            <ChevronLeft className="h-5 w-5" />
          </button>
          
          <div className="flex items-center gap-3">
            <Calendar className="h-5 w-5 text-gray-500" />
            <span className="font-medium text-lg">
              {formatDateRange(selectedWeek.start, selectedWeek.end)}
            </span>
          </div>

          <button
            onClick={nextWeek}
            className="p-2 hover:bg-gray-100 rounded"
            data-testid="next-week"
          >
            <ChevronRight className="h-5 w-5" />
          </button>
        </div>
      </div>

      {/* P&L Table */}
      {formData ? (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700 w-1/2">
                    {t('pl.title')}
                  </th>
                  <th className="px-4 py-3 text-right text-sm font-semibold text-gray-700 w-1/4">
                    {t('pl.amount')}
                  </th>
                  <th className="px-4 py-3 text-right text-sm font-semibold text-gray-700 w-1/4">
                    {t('pl.percent')}
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {/* SALES SECTION */}
                <tr className="bg-blue-50">
                  <td colSpan="3" className="px-4 py-2 font-bold text-blue-900">
                    {t('pl.sales')}
                  </td>
                </tr>
                <tr>
                  <td className="px-4 py-2 pl-8">{t('pl.sales.turnover')}</td>
                  <td className="px-4 py-2 text-right">
                    {canEdit ? (
                      <input
                        type="number"
                        step="0.01"
                        value={formData.sales_turnover}
                        onChange={(e) => updateField('sales_turnover', e.target.value)}
                        className="w-full px-2 py-1 border rounded text-right"
                        data-testid="sales-turnover"
                      />
                    ) : (
                      formatCurrency(formData.sales_turnover)
                    )}
                  </td>
                  <td className="px-4 py-2 text-right font-semibold">100.00%</td>
                </tr>
                <tr>
                  <td className="px-4 py-2 pl-8">{t('pl.sales.foodBeverage')}</td>
                  <td className="px-4 py-2 text-right">
                    {canEdit ? (
                      <input
                        type="number"
                        step="0.01"
                        value={formData.sales_food_beverage}
                        onChange={(e) => updateField('sales_food_beverage', e.target.value)}
                        className="w-full px-2 py-1 border rounded text-right"
                      />
                    ) : (
                      formatCurrency(formData.sales_food_beverage)
                    )}
                  </td>
                  <td className="px-4 py-2 text-right">{calculatePercent(formData.sales_food_beverage)}%</td>
                </tr>
                <tr>
                  <td className="px-4 py-2 pl-8">{t('pl.sales.delivery')}</td>
                  <td className="px-4 py-2 text-right">
                    {canEdit ? (
                      <input
                        type="number"
                        step="0.01"
                        value={formData.sales_delivery}
                        onChange={(e) => updateField('sales_delivery', e.target.value)}
                        className="w-full px-2 py-1 border rounded text-right"
                      />
                    ) : (
                      formatCurrency(formData.sales_delivery)
                    )}
                  </td>
                  <td className="px-4 py-2 text-right">{calculatePercent(formData.sales_delivery)}%</td>
                </tr>

                {/* COGS SECTION */}
                <tr className="bg-red-50">
                  <td colSpan="3" className="px-4 py-2 font-bold text-red-900">
                    {t('pl.cogs')}
                  </td>
                </tr>
                <tr>
                  <td className="px-4 py-2 pl-8">{t('pl.cogs.foodBeverage')}</td>
                  <td className="px-4 py-2 text-right">
                    {canEdit ? (
                      <input
                        type="number"
                        step="0.01"
                        value={formData.cogs_food_beverage}
                        onChange={(e) => updateField('cogs_food_beverage', e.target.value)}
                        className="w-full px-2 py-1 border rounded text-right"
                      />
                    ) : (
                      formatCurrency(formData.cogs_food_beverage)
                    )}
                  </td>
                  <td className="px-4 py-2 text-right">{calculatePercent(formData.cogs_food_beverage)}%</td>
                </tr>
                <tr>
                  <td className="px-4 py-2 pl-8">{t('pl.cogs.rawWaste')}</td>
                  <td className="px-4 py-2 text-right">
                    {canEdit ? (
                      <input
                        type="number"
                        step="0.01"
                        value={formData.cogs_raw_waste}
                        onChange={(e) => updateField('cogs_raw_waste', e.target.value)}
                        className="w-full px-2 py-1 border rounded text-right"
                      />
                    ) : (
                      formatCurrency(formData.cogs_raw_waste)
                    )}
                  </td>
                  <td className="px-4 py-2 text-right">{calculatePercent(formData.cogs_raw_waste)}%</td>
                </tr>
                <tr className="bg-red-100 font-semibold">
                  <td className="px-4 py-2 pl-8">{t('pl.cogs.total')}</td>
                  <td className="px-4 py-2 text-right">{formatCurrency(totals.cogs_total)}</td>
                  <td className="px-4 py-2 text-right">{calculatePercent(totals.cogs_total)}%</td>
                </tr>

                {/* OPEX SECTION */}
                <tr className="bg-orange-50">
                  <td colSpan="3" className="px-4 py-2 font-bold text-orange-900">
                    {t('pl.opex')}
                  </td>
                </tr>
                <tr>
                  <td className="px-4 py-2 pl-8">{t('pl.opex.nonFood')}</td>
                  <td className="px-4 py-2 text-right">
                    {canEdit ? (
                      <input
                        type="number"
                        step="0.01"
                        value={formData.opex_non_food}
                        onChange={(e) => updateField('opex_non_food', e.target.value)}
                        className="w-full px-2 py-1 border rounded text-right"
                      />
                    ) : (
                      formatCurrency(formData.opex_non_food)
                    )}
                  </td>
                  <td className="px-4 py-2 text-right">{calculatePercent(formData.opex_non_food)}%</td>
                </tr>
                <tr>
                  <td className="px-4 py-2 pl-8">{t('pl.opex.platforms')}</td>
                  <td className="px-4 py-2 text-right">
                    {canEdit ? (
                      <input
                        type="number"
                        step="0.01"
                        value={formData.opex_platforms}
                        onChange={(e) => updateField('opex_platforms', e.target.value)}
                        className="w-full px-2 py-1 border rounded text-right"
                      />
                    ) : (
                      formatCurrency(formData.opex_platforms)
                    )}
                  </td>
                  <td className="px-4 py-2 text-right">{calculatePercent(formData.opex_platforms)}%</td>
                </tr>
                <tr className="bg-orange-100 font-semibold">
                  <td className="px-4 py-2 pl-8">{t('pl.opex.total')}</td>
                  <td className="px-4 py-2 text-right">{formatCurrency(totals.opex_total)}</td>
                  <td className="px-4 py-2 text-right">{calculatePercent(totals.opex_total)}%</td>
                </tr>

                {/* LABOUR SECTION */}
                <tr className="bg-purple-50">
                  <td colSpan="3" className="px-4 py-2 font-bold text-purple-900">
                    {t('pl.labour')}
                  </td>
                </tr>
                <tr>
                  <td className="px-4 py-2 pl-8">{t('pl.labour.employees')}</td>
                  <td className="px-4 py-2 text-right">
                    {canEdit ? (
                      <input
                        type="number"
                        step="0.01"
                        value={formData.labour_employees}
                        onChange={(e) => updateField('labour_employees', e.target.value)}
                        className="w-full px-2 py-1 border rounded text-right"
                      />
                    ) : (
                      formatCurrency(formData.labour_employees)
                    )}
                  </td>
                  <td className="px-4 py-2 text-right">{calculatePercent(formData.labour_employees)}%</td>
                </tr>
                <tr>
                  <td className="px-4 py-2 pl-8">{t('pl.labour.staffMeal')}</td>
                  <td className="px-4 py-2 text-right">
                    {canEdit ? (
                      <input
                        type="number"
                        step="0.01"
                        value={formData.labour_staff_meal}
                        onChange={(e) => updateField('labour_staff_meal', e.target.value)}
                        className="w-full px-2 py-1 border rounded text-right"
                      />
                    ) : (
                      formatCurrency(formData.labour_staff_meal)
                    )}
                  </td>
                  <td className="px-4 py-2 text-right">{calculatePercent(formData.labour_staff_meal)}%</td>
                </tr>
                <tr className="bg-purple-100 font-semibold">
                  <td className="px-4 py-2 pl-8">{t('pl.labour.total')}</td>
                  <td className="px-4 py-2 text-right">{formatCurrency(totals.labour_total)}</td>
                  <td className="px-4 py-2 text-right">{calculatePercent(totals.labour_total)}%</td>
                </tr>

                {/* MARKETING SECTION */}
                <tr className="bg-green-50">
                  <td colSpan="3" className="px-4 py-2 font-bold text-green-900">
                    {t('pl.marketing')}
                  </td>
                </tr>
                <tr>
                  <td className="px-4 py-2 pl-8">{t('pl.marketing.onlineAds')}</td>
                  <td className="px-4 py-2 text-right">
                    {canEdit ? (
                      <input
                        type="number"
                        step="0.01"
                        value={formData.marketing_online_ads}
                        onChange={(e) => updateField('marketing_online_ads', e.target.value)}
                        className="w-full px-2 py-1 border rounded text-right"
                      />
                    ) : (
                      formatCurrency(formData.marketing_online_ads)
                    )}
                  </td>
                  <td className="px-4 py-2 text-right">{calculatePercent(formData.marketing_online_ads)}%</td>
                </tr>
                <tr>
                  <td className="px-4 py-2 pl-8">{t('pl.marketing.freeItems')}</td>
                  <td className="px-4 py-2 text-right">
                    {canEdit ? (
                      <input
                        type="number"
                        step="0.01"
                        value={formData.marketing_free_items}
                        onChange={(e) => updateField('marketing_free_items', e.target.value)}
                        className="w-full px-2 py-1 border rounded text-right"
                      />
                    ) : (
                      formatCurrency(formData.marketing_free_items)
                    )}
                  </td>
                  <td className="px-4 py-2 text-right">{calculatePercent(formData.marketing_free_items)}%</td>
                </tr>
                <tr className="bg-green-100 font-semibold">
                  <td className="px-4 py-2 pl-8">{t('pl.marketing.total')}</td>
                  <td className="px-4 py-2 text-right">{formatCurrency(totals.marketing_total)}</td>
                  <td className="px-4 py-2 text-right">{calculatePercent(totals.marketing_total)}%</td>
                </tr>

                {/* RENT SECTION */}
                <tr className="bg-yellow-50">
                  <td colSpan="3" className="px-4 py-2 font-bold text-yellow-900">
                    {t('pl.rent')}
                  </td>
                </tr>
                <tr>
                  <td className="px-4 py-2 pl-8">{t('pl.rent.baseEffective')}</td>
                  <td className="px-4 py-2 text-right">
                    {canEdit ? (
                      <input
                        type="number"
                        step="0.01"
                        value={formData.rent_base_effective}
                        onChange={(e) => updateField('rent_base_effective', e.target.value)}
                        className="w-full px-2 py-1 border rounded text-right"
                      />
                    ) : (
                      formatCurrency(formData.rent_base_effective)
                    )}
                  </td>
                  <td className="px-4 py-2 text-right">{calculatePercent(formData.rent_base_effective)}%</td>
                </tr>
                <tr>
                  <td className="px-4 py-2 pl-8">{t('pl.rent.garden')}</td>
                  <td className="px-4 py-2 text-right">
                    {canEdit ? (
                      <input
                        type="number"
                        step="0.01"
                        value={formData.rent_garden}
                        onChange={(e) => updateField('rent_garden', e.target.value)}
                        className="w-full px-2 py-1 border rounded text-right"
                      />
                    ) : (
                      formatCurrency(formData.rent_garden)
                    )}
                  </td>
                  <td className="px-4 py-2 text-right">{calculatePercent(formData.rent_garden)}%</td>
                </tr>
                <tr className="bg-yellow-100 font-semibold">
                  <td className="px-4 py-2 pl-8">{t('pl.rent.total')}</td>
                  <td className="px-4 py-2 text-right">{formatCurrency(totals.rent_total)}</td>
                  <td className="px-4 py-2 text-right">{calculatePercent(totals.rent_total)}%</td>
                </tr>

                {/* OTHER SECTION */}
                <tr className="bg-gray-50">
                  <td colSpan="3" className="px-4 py-2 font-bold text-gray-900">
                    {t('pl.other')}
                  </td>
                </tr>
                <tr>
                  <td className="px-4 py-2 pl-8">{t('pl.other.total')}</td>
                  <td className="px-4 py-2 text-right">
                    {canEdit ? (
                      <input
                        type="number"
                        step="0.01"
                        value={formData.other_total}
                        onChange={(e) => updateField('other_total', e.target.value)}
                        className="w-full px-2 py-1 border rounded text-right"
                      />
                    ) : (
                      formatCurrency(formData.other_total)
                    )}
                  </td>
                  <td className="px-4 py-2 text-right">{calculatePercent(formData.other_total)}%</td>
                </tr>

                {/* EBITDA */}
                <tr className="bg-indigo-100 font-bold text-lg">
                  <td className="px-4 py-3">{t('pl.kpi.ebitda')}</td>
                  <td className="px-4 py-3 text-right">{formatCurrency(totals.kpi_ebitda)}</td>
                  <td className="px-4 py-3 text-right">{calculatePercent(totals.kpi_ebitda)}%</td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* Notes Section */}
          <div className="p-4 border-t">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              {t('pl.notes')}
            </label>
            {canEdit ? (
              <textarea
                value={formData.notes || ''}
                onChange={(e) => setFormData(prev => ({ ...prev, notes: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                rows="3"
                placeholder={t('pl.notes')}
              />
            ) : (
              <p className="text-gray-700">{formData.notes || '--'}</p>
            )}
          </div>
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow p-12 text-center">
          <TrendingUp className="h-16 w-16 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            {t('pl.noData')}
          </h3>
          <p className="text-gray-500 mb-4">
            {t('pl.createFirst')}
          </p>
        </div>
      )}
    </div>
  );
}

export default PLSnapshot;
