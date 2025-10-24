import React, { useState, useEffect, useCallback, useContext } from 'react';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import { ClipboardList, Calendar, Search, Filter, AlertCircle, Save, RefreshCw } from 'lucide-react';
import { useCurrency } from '../contexts/CurrencyContext';
import { AuthContext } from '../App';

function PrepList() {
  const { t } = useTranslation();
  const { formatMinor } = useCurrency();
  const { user } = useContext(AuthContext);
  const [loading, setLoading] = useState(false);
  const [prepList, setPrepList] = useState(null);
  const [targetDate, setTargetDate] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [filterView, setFilterView] = useState('toMake'); // 'all', 'toMake', 'available'

  // Set default target date to tomorrow
  useEffect(() => {
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    setTargetDate(tomorrow.toISOString().split('T')[0]);
  }, []);

  // RBAC check
  const canEdit = user?.roleKey === 'admin' || user?.roleKey === 'manager';

  // Load existing prep list for date
  const loadPrepList = useCallback(async (date) => {
    if (!date) return;
    
    try {
      setLoading(true);
      const token = localStorage.getItem('token');
      const response = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/prep-list`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.ok) {
        const allLists = await response.json();
        const listForDate = allLists.find(list => list.date === date);
        if (listForDate) {
          setPrepList(listForDate);
        } else {
          setPrepList(null);
        }
      }
    } catch (error) {
      console.error('Failed to load prep list:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (targetDate) {
      loadPrepList(targetDate);
    }
  }, [targetDate, loadPrepList]);

  // Generate prep list forecast
  const handleGenerate = async () => {
    if (!targetDate) {
      toast.error(t('prepList.error.required') || 'Please select a target date');
      return;
    }

    try {
      setLoading(true);
      const token = localStorage.getItem('token');
      const response = await fetch(
        `${process.env.REACT_APP_BACKEND_URL}/api/prep-list/forecast?date=${targetDate}`,
        {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }
      );

      if (response.ok) {
        const forecast = await response.json();
        setPrepList({
          date: targetDate,
          items: forecast.items || []
        });
        toast.success(t('prepList.success.generated') || 'Prep list generated successfully');
      } else {
        toast.error(t('prepList.error.generate') || 'Failed to generate prep list');
      }
    } catch (error) {
      console.error('Failed to generate prep list:', error);
      toast.error(t('prepList.error.generate') || 'Failed to generate prep list');
    } finally {
      setLoading(false);
    }
  };

  // Save prep list
  const handleSave = async () => {
    if (!prepList || !prepList.items || prepList.items.length === 0) {
      toast.error(t('prepList.error.required') || 'No items to save');
      return;
    }

    try {
      setLoading(true);
      const token = localStorage.getItem('token');
      const response = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/prep-list`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          date: targetDate,
          items: prepList.items
        })
      });

      if (response.ok) {
        const saved = await response.json();
        setPrepList(saved);
        toast.success(t('prepList.success.saved') || 'Prep list saved successfully');
      } else {
        toast.error(t('prepList.error.save') || 'Failed to save prep list');
      }
    } catch (error) {
      console.error('Failed to save prep list:', error);
      toast.error(t('prepList.error.save') || 'Failed to save prep list');
    } finally {
      setLoading(false);
    }
  };

  // Update item override
  const handleOverride = (index, field, value) => {
    if (!canEdit) return;
    
    setPrepList(prev => {
      const updated = { ...prev };
      updated.items = [...prev.items];
      updated.items[index] = {
        ...updated.items[index],
        [field]: value
      };
      
      // If overriding toMakeQty, update forecastSource
      if (field === 'toMakeQty' || field === 'overrideQty') {
        updated.items[index].forecastSource = 'manual_override';
        updated.items[index].overrideQty = value;
      }
      
      return updated;
    });
  };

  // Update actual qty
  const handleActualQty = (index, value) => {
    setPrepList(prev => {
      const updated = { ...prev };
      updated.items = [...prev.items];
      updated.items[index] = {
        ...updated.items[index],
        actualQty: parseFloat(value) || 0
      };
      return updated;
    });
  };

  // Update notes
  const handleNotes = (index, value) => {
    setPrepList(prev => {
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
  const filteredItems = prepList?.items?.filter(item => {
    // Search filter
    if (searchTerm && !item.preparationName?.toLowerCase().includes(searchTerm.toLowerCase())) {
      return false;
    }

    // View filter
    if (filterView === 'toMake' && item.toMakeQty <= 0) {
      return false;
    }
    if (filterView === 'available' && item.availableQty <= 0) {
      return false;
    }

    return true;
  }) || [];

  // Get urgency level based on toMakeQty
  const getUrgency = (item) => {
    if (item.toMakeQty > item.forecastQty * 0.8) return 'high';
    if (item.toMakeQty > item.forecastQty * 0.5) return 'medium';
    return 'low';
  };

  // Get urgency badge color
  const getUrgencyColor = (urgency) => {
    if (urgency === 'high') return 'bg-red-100 text-red-800';
    if (urgency === 'medium') return 'bg-yellow-100 text-yellow-800';
    return 'bg-green-100 text-green-800';
  };

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold flex items-center gap-2">
              <ClipboardList className="h-8 w-8" />
              {t('prepList.title')}
            </h1>
            <p className="text-gray-600 mt-1">{t('prepList.subtitle')}</p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={handleGenerate}
              disabled={loading || !targetDate}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
            >
              <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
              {t('prepList.generate')}
            </button>
            {canEdit && prepList && prepList.items && prepList.items.length > 0 && (
              <button
                onClick={handleSave}
                disabled={loading}
                className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 flex items-center gap-2"
              >
                <Save className="h-4 w-4" />
                {t('prepList.save')}
              </button>
            )}
            {/* Export Buttons */}
            {prepList && prepList.items && prepList.items.length > 0 && (
              <div className="flex gap-2">
                <button
                  onClick={async () => {
                    try {
                      const token = localStorage.getItem('token');
                      const locale = localStorage.getItem('i18nextLng') || 'en';
                      const response = await fetch(
                        `${process.env.REACT_APP_BACKEND_URL}/api/prep-list/export?date=${targetDate}&format=pdf&locale=${locale}`,
                        {
                          headers: {
                            'Authorization': `Bearer ${token}`
                          }
                        }
                      );
                      
                      if (response.ok) {
                        const blob = await response.blob();
                        const url = window.URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = url;
                        a.download = `DailyPreparations_${targetDate}.pdf`;
                        document.body.appendChild(a);
                        a.click();
                        window.URL.revokeObjectURL(url);
                        document.body.removeChild(a);
                        toast.success(t('export.success') || 'Export successful');
                      } else if (response.status === 404) {
                        const requestId = response.headers.get('x-request-id') || 'unknown';
                        console.warn('No data to export. RequestId:', requestId);
                        toast.warning(t('export.noData') || `No data to export for ${targetDate}`);
                      } else {
                        const requestId = response.headers.get('x-request-id') || 'unknown';
                        console.error('Export failed. RequestId:', requestId, 'Status:', response.status);
                        const error = await response.json().catch(() => ({ detail: 'Export failed' }));
                        toast.error(`${error.detail || t('export.error')} (Request ID: ${requestId})`);
                      }
                    } catch (error) {
                      console.error('Export error:', error);
                      toast.error(t('export.error') || 'Export failed');
                    }
                  }}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2"
                >
                  {t('export.pdf')}
                </button>
                <button
                  onClick={async () => {
                    try {
                      const token = localStorage.getItem('token');
                      const locale = localStorage.getItem('i18nextLng') || 'en';
                      const response = await fetch(
                        `${process.env.REACT_APP_BACKEND_URL}/api/prep-list/export?date=${targetDate}&format=xlsx&locale=${locale}`,
                        {
                          headers: {
                            'Authorization': `Bearer ${token}`
                          }
                        }
                      );
                      
                      if (response.ok) {
                        const blob = await response.blob();
                        const url = window.URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = url;
                        a.download = `DailyPreparations_${targetDate}.xlsx`;
                        document.body.appendChild(a);
                        a.click();
                        window.URL.revokeObjectURL(url);
                        document.body.removeChild(a);
                        toast.success(t('export.success') || 'Export successful');
                      } else {
                        const requestId = response.headers.get('x-request-id') || 'unknown';
                        console.error('Export failed. RequestId:', requestId);
                        const error = await response.json().catch(() => ({ detail: 'Export failed' }));
                        toast.error(`${error.detail || t('export.error')} (Request ID: ${requestId})`);
                      }
                    } catch (error) {
                      console.error('Export error:', error);
                      toast.error(t('export.error') || 'Export failed');
                    }
                  }}
                  className="px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 flex items-center gap-2"
                >
                  {t('export.xlsx')}
                </button>
              </div>
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
            <label className="text-sm font-medium">{t('prepList.targetDate')}:</label>
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
                placeholder={t('prepList.search')}
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
              <option value="all">{t('prepList.filter.all')}</option>
              <option value="toMake">{t('prepList.filter.toMake')}</option>
              <option value="available">{t('prepList.filter.available')}</option>
            </select>
          </div>
        </div>
      </div>

      {/* Prep List Table */}
      {prepList && prepList.items && prepList.items.length > 0 ? (
        <>
          {filteredItems.length > 0 ? (
            <div className="bg-white rounded-lg shadow overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-50 sticky top-0">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        {t('prepList.preparation')}
                      </th>
                      <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                        {t('prepList.forecast')}
                      </th>
                      <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                        {t('prepList.available')}
                      </th>
                      <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                        {t('prepList.toMake')}
                      </th>
                      <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                        {t('prepList.actualQty')}
                      </th>
                      <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                        {t('prepList.unit')}
                      </th>
                      <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                        {t('prepList.forecastSource')}
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        {t('prepList.notes')}
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {filteredItems.map((item, index) => {
                      const urgency = getUrgency(item);
                      const urgencyColor = getUrgencyColor(urgency);
                      const isOverridden = item.forecastSource === 'manual_override';
                      
                      return (
                        <tr 
                          key={index}
                          className={`hover:bg-gray-50 ${urgency === 'high' ? 'bg-red-50' : ''}`}
                          data-testid={`prep-item-${index}`}
                        >
                          <td className="px-4 py-3">
                            <div className="flex items-center gap-2">
                              <span className="font-medium">{item.preparationName || item.preparationId}</span>
                              {isOverridden && (
                                <span className="px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded">
                                  {t('prepList.overridden')}
                                </span>
                              )}
                            </div>
                          </td>
                          <td className="px-4 py-3 text-center text-gray-900">
                            {item.forecastQty?.toFixed(2) || '0.00'}
                          </td>
                          <td className="px-4 py-3 text-center text-gray-900">
                            {item.availableQty?.toFixed(2) || '0.00'}
                          </td>
                          <td className="px-4 py-3 text-center">
                            {canEdit ? (
                              <input
                                type="number"
                                step="0.01"
                                value={item.overrideQty !== undefined ? item.overrideQty : item.toMakeQty}
                                onChange={(e) => handleOverride(index, 'toMakeQty', parseFloat(e.target.value) || 0)}
                                className="w-20 px-2 py-1 border border-gray-300 rounded text-center"
                                data-testid={`to-make-qty-${index}`}
                              />
                            ) : (
                              <span className="text-gray-900">{item.toMakeQty?.toFixed(2) || '0.00'}</span>
                            )}
                            {urgency === 'high' && (
                              <AlertCircle className="inline-block ml-2 h-4 w-4 text-red-500" />
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
                              data-testid={`actual-qty-${index}`}
                            />
                          </td>
                          <td className="px-4 py-3 text-center text-gray-600">
                            {item.unit}
                          </td>
                          <td className="px-4 py-3 text-center">
                            <span className={`px-2 py-1 text-xs rounded ${urgencyColor}`}>
                              {t(`prepList.source.${item.forecastSource}`) || item.forecastSource}
                            </span>
                          </td>
                          <td className="px-4 py-3">
                            <input
                              type="text"
                              value={item.notes || ''}
                              onChange={(e) => handleNotes(index, e.target.value)}
                              placeholder={t('prepList.notes')}
                              className="w-full px-2 py-1 border border-gray-300 rounded"
                              data-testid={`notes-${index}`}
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
              <ClipboardList className="h-16 w-16 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                {t('prepList.noItemsToMake') || 'No items to make'}
              </h3>
              <p className="text-gray-500 mb-4">
                {t('prepList.noItemsToMakeDesc') || 'No items to make for the selected date. All preps are already covered.'}
              </p>
              <button
                onClick={() => setFilterView('all')}
                className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                {t('prepList.switchToAll') || 'Switch to All to view the full list'}
              </button>
            </div>
          )}
        </>
      ) : (
        <div className="bg-white rounded-lg shadow p-12 text-center">
          <ClipboardList className="h-16 w-16 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            {t('prepList.noData')}
          </h3>
          <p className="text-gray-500 mb-4">
            {t('prepList.generateFirst')}
          </p>
          <button
            onClick={handleGenerate}
            disabled={loading || !targetDate}
            className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {t('prepList.generate')}
          </button>
        </div>
      )}

      {/* Summary */}
      {prepList && prepList.items && prepList.items.length > 0 && (
        <div className="mt-6 bg-blue-50 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">
                Total Preparations: <span className="font-semibold text-gray-900">{prepList.items.length}</span>
              </p>
              <p className="text-sm text-gray-600">
                To Make: <span className="font-semibold text-gray-900">
                  {prepList.items.filter(item => item.toMakeQty > 0).length}
                </span>
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-600">
                Target Date: <span className="font-semibold text-gray-900">{targetDate}</span>
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default PrepList;
