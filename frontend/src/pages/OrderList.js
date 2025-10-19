import React, { useState, useEffect, useCallback, useContext } from 'react';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import { ShoppingCart, Calendar, Search, Filter, AlertCircle, Save, RefreshCw, Package } from 'lucide-react';
import { useCurrency } from '../contexts/CurrencyContext';
import { AuthContext } from '../App';

function OrderList() {
  const { t } = useTranslation();
  const { formatMinor } = useCurrency();
  const { user } = useContext(AuthContext);
  const [loading, setLoading] = useState(false);
  const [orderList, setOrderList] = useState(null);
  const [targetDate, setTargetDate] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [filterView, setFilterView] = useState('all'); // 'all', 'lowStock', 'expiring'
  const [suppliers, setSuppliers] = useState([]);

  // Set default target date to tomorrow
  useEffect(() => {
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    setTargetDate(tomorrow.toISOString().split('T')[0]);
  }, []);

  // RBAC check
  const canEdit = user?.roleKey === 'admin' || user?.roleKey === 'manager';

  // Load existing order list for date
  const loadOrderList = useCallback(async (date) => {
    if (!date) return;
    
    try {
      setLoading(true);
      const token = localStorage.getItem('token');
      const response = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/order-list`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.ok) {
        const allLists = await response.json();
        const listForDate = allLists.find(list => list.date === date);
        if (listForDate) {
          setOrderList(listForDate);
        } else {
          setOrderList(null);
        }
      }
    } catch (error) {
      console.error('Failed to load order list:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (targetDate) {
      loadOrderList(targetDate);
    }
  }, [targetDate, loadOrderList]);

  // Generate order list forecast
  const handleGenerate = async () => {
    if (!targetDate) {
      toast.error(t('orderList.error.required') || 'Please select a target date');
      return;
    }

    try {
      setLoading(true);
      const token = localStorage.getItem('token');
      const response = await fetch(
        `${process.env.REACT_APP_BACKEND_URL}/api/order-list/forecast?date=${targetDate}`,
        {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }
      );

      if (response.ok) {
        const forecast = await response.json();
        setOrderList({
          date: targetDate,
          items: forecast.items || []
        });
        toast.success(t('orderList.success.generated') || 'Order list generated successfully');
      } else {
        toast.error(t('orderList.error.generate') || 'Failed to generate order list');
      }
    } catch (error) {
      console.error('Failed to generate order list:', error);
      toast.error(t('orderList.error.generate') || 'Failed to generate order list');
    } finally {
      setLoading(false);
    }
  };

  // Save order list
  const handleSave = async () => {
    if (!orderList || !orderList.items || orderList.items.length === 0) {
      toast.error(t('orderList.error.required') || 'No items to save');
      return;
    }

    try {
      setLoading(true);
      const token = localStorage.getItem('token');
      const response = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/order-list`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          date: targetDate,
          items: orderList.items
        })
      });

      if (response.ok) {
        const saved = await response.json();
        setOrderList(saved);
        toast.success(t('orderList.success.saved') || 'Order list saved successfully');
      } else {
        toast.error(t('orderList.error.save') || 'Failed to save order list');
      }
    } catch (error) {
      console.error('Failed to save order list:', error);
      toast.error(t('orderList.error.save') || 'Failed to save order list');
    } finally {
      setLoading(false);
    }
  };

  // Update actual order quantity
  const handleActualQty = (index, value) => {
    if (!canEdit) return;
    
    setOrderList(prev => {
      const updated = { ...prev };
      updated.items = [...prev.items];
      updated.items[index] = {
        ...updated.items[index],
        actualQty: parseFloat(value) || 0
      };
      return updated;
    });
  };

  // Update suggested quantity (override)
  const handleSuggestedOverride = (index, value) => {
    if (!canEdit) return;
    
    setOrderList(prev => {
      const updated = { ...prev };
      updated.items = [...prev.items];
      updated.items[index] = {
        ...updated.items[index],
        suggestedQty: parseFloat(value) || 0
      };
      return updated;
    });
  };

  // Update supplier
  const handleSupplierChange = (index, supplierId) => {
    if (!canEdit) return;
    
    setOrderList(prev => {
      const updated = { ...prev };
      updated.items = [...prev.items];
      updated.items[index] = {
        ...updated.items[index],
        supplierId: supplierId
      };
      return updated;
    });
  };

  // Calculate pack-rounded quantity
  const roundToPack = (qty, packSize) => {
    if (!packSize || packSize <= 0) return qty;
    return Math.ceil(qty / packSize) * packSize;
  };

  // Update notes
  const handleNotes = (index, value) => {
    setOrderList(prev => {
      const updated = { ...prev };
      updated.items = [...prev.items];
      updated.items[index] = {
        ...updated.items[index],
        notes: value
      };
      return updated;
    });
  };

  // Filter and search items
  const filteredItems = orderList?.items?.filter(item => {
    // Search filter
    if (searchTerm && !item.ingredientName?.toLowerCase().includes(searchTerm.toLowerCase())) {
      return false;
    }

    // View filter
    if (filterView === 'lowStock' && !item.drivers?.includes('low_stock')) {
      return false;
    }
    if (filterView === 'expiring' && !item.drivers?.includes('expiring_soon')) {
      return false;
    }

    return true;
  }) || [];

  // Get driver badge
  const getDriverBadge = (driver) => {
    const colors = {
      low_stock: 'bg-red-100 text-red-800',
      prep_needs: 'bg-blue-100 text-blue-800',
      sales_forecast: 'bg-green-100 text-green-800',
      expiring_soon: 'bg-orange-100 text-orange-800'
    };

    return (
      <span className={`px-2 py-1 text-xs rounded ${colors[driver] || 'bg-gray-100 text-gray-800'}`}>
        {t(`orderList.driver.${driver}`) || driver}
      </span>
    );
  };

  // Get urgency (for sorting/highlighting)
  const getUrgency = (item) => {
    if (item.drivers?.includes('expiring_soon') || item.drivers?.includes('low_stock')) {
      return 'high';
    }
    if (item.drivers?.includes('prep_needs')) {
      return 'medium';
    }
    return 'low';
  };

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold flex items-center gap-2">
              <ShoppingCart className="h-8 w-8" />
              {t('orderList.title')}
            </h1>
            <p className="text-gray-600 mt-1">{t('orderList.subtitle')}</p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={handleGenerate}
              disabled={loading || !targetDate}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
            >
              <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
              {t('orderList.generate')}
            </button>
            {canEdit && orderList && orderList.items && orderList.items.length > 0 && (
              <button
                onClick={handleSave}
                disabled={loading}
                className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 flex items-center gap-2"
              >
                <Save className="h-4 w-4" />
                {t('orderList.save')}
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Date picker and filters */}
      <div className="mb-6 bg-white p-4 rounded-lg shadow">
        <div className="flex flex-wrap items-center gap-4">
          {/* Target Date */}
          <div className="flex items-center gap-2">
            <Calendar className="h-4 w-4 text-gray-500" />
            <label className="text-sm font-medium">{t('orderList.targetDate')}:</label>
            <input
              type="date"
              value={targetDate}
              onChange={(e) => setTargetDate(e.target.value)}
              className="border border-gray-300 rounded px-3 py-1"
            />
          </div>

          {/* Search */}
          <div className="flex-1 min-w-[200px]">
            <div className="relative">
              <Search className="absolute left-3 top-2.5 h-4 w-4 text-gray-400" />
              <input
                type="text"
                placeholder={t('orderList.search')}
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg"
              />
            </div>
          </div>

          {/* View Filter */}
          <div className="flex items-center gap-2">
            <Filter className="h-4 w-4 text-gray-500" />
            <select
              value={filterView}
              onChange={(e) => setFilterView(e.target.value)}
              className="border border-gray-300 rounded px-3 py-2"
            >
              <option value="all">{t('orderList.filter.all')}</option>
              <option value="lowStock">{t('orderList.filter.lowStock')}</option>
              <option value="expiring">{t('orderList.filter.expiring')}</option>
            </select>
          </div>
        </div>
      </div>

      {/* Order List Table */}
      {orderList && orderList.items && orderList.items.length > 0 ? (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 sticky top-0">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    {t('orderList.ingredient')}
                  </th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                    {t('orderList.current')}
                  </th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                    {t('orderList.minStock')}
                  </th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                    {t('orderList.suggested')}
                  </th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                    {t('orderList.actualQty')}
                  </th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                    {t('orderList.unit')}
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    {t('orderList.supplier')}
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    {t('orderList.drivers')}
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    {t('orderList.notes')}
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {filteredItems.map((item, index) => {
                  const urgency = getUrgency(item);
                  const isLowStock = item.drivers?.includes('low_stock');
                  const isExpiring = item.drivers?.includes('expiring_soon');
                  
                  return (
                    <tr 
                      key={index}
                      className={`hover:bg-gray-50 ${isLowStock || isExpiring ? 'bg-orange-50' : ''}`}
                      data-testid={`order-item-${index}`}
                    >
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <Package className="h-4 w-4 text-gray-400" />
                          <span className="font-medium">{item.ingredientName || item.ingredientId}</span>
                          {isExpiring && (
                            <AlertCircle className="h-4 w-4 text-orange-500" title={t('orderList.driver.expiring_soon')} />
                          )}
                        </div>
                        {item.expiryDate && (
                          <p className="text-xs text-gray-500 mt-1">
                            {t('orderList.expiryDate')}: {item.expiryDate}
                          </p>
                        )}
                      </td>
                      <td className="px-4 py-3 text-center text-gray-900">
                        {item.currentQty?.toFixed(2) || '0.00'}
                      </td>
                      <td className="px-4 py-3 text-center text-gray-900">
                        {item.minStockQty?.toFixed(2) || '0.00'}
                      </td>
                      <td className="px-4 py-3 text-center">
                        {canEdit ? (
                          <input
                            type="number"
                            step="0.01"
                            value={item.suggestedQty || ''}
                            onChange={(e) => handleSuggestedOverride(index, e.target.value)}
                            className="w-20 px-2 py-1 border border-gray-300 rounded text-center"
                            data-testid={`suggested-qty-${index}`}
                          />
                        ) : (
                          <span className="text-gray-900">{item.suggestedQty?.toFixed(2) || '0.00'}</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-center">
                        <input
                          type="number"
                          step="0.01"
                          value={item.actualQty || ''}
                          onChange={(e) => handleActualQty(index, e.target.value)}
                          placeholder="--"
                          className="w-20 px-2 py-1 border border-gray-300 rounded text-center"
                          data-testid={`actual-order-${index}`}
                        />
                      </td>
                      <td className="px-4 py-3 text-center text-gray-600">
                        {item.unit}
                      </td>
                      <td className="px-4 py-3">
                        <span className="text-sm text-gray-900">
                          {item.supplierName || '--'}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex flex-wrap gap-1">
                          {item.drivers?.map((driver, idx) => (
                            <span key={idx}>{getDriverBadge(driver)}</span>
                          ))}
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <input
                          type="text"
                          value={item.notes || ''}
                          onChange={(e) => handleNotes(index, e.target.value)}
                          placeholder={t('orderList.notes')}
                          className="w-full px-2 py-1 border border-gray-300 rounded"
                          data-testid={`order-notes-${index}`}
                        />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow p-12 text-center">
          <ShoppingCart className="h-16 w-16 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            {t('orderList.noData')}
          </h3>
          <p className="text-gray-500 mb-4">
            {t('orderList.generateFirst')}
          </p>
          <button
            onClick={handleGenerate}
            disabled={loading || !targetDate}
            className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {t('orderList.generate')}
          </button>
        </div>
      )}

      {/* Summary */}
      {orderList && orderList.items && orderList.items.length > 0 && (
        <div className="mt-6 bg-blue-50 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">
                Total Items: <span className="font-semibold text-gray-900">{orderList.items.length}</span>
              </p>
              <p className="text-sm text-gray-600">
                Low Stock: <span className="font-semibold text-red-600">
                  {orderList.items.filter(item => item.drivers?.includes('low_stock')).length}
                </span>
              </p>
              <p className="text-sm text-gray-600">
                Expiring Soon: <span className="font-semibold text-orange-600">
                  {orderList.items.filter(item => item.drivers?.includes('expiring_soon')).length}
                </span>
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-600">
                Order Date: <span className="font-semibold text-gray-900">{targetDate}</span>
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default OrderList;
