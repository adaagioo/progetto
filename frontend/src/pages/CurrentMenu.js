import React, { useState, useEffect, useContext } from 'react';
import { AuthContext } from '../App';
import { useTranslation } from 'react-i18next';
import { useCurrency } from '../contexts/CurrencyContext';
import { Button } from '../components/ui/button';
import { Plus, Edit, Trash2, Power, PowerOff, Search, Filter, X, Check, AlertCircle, CheckCircle, XCircle } from 'lucide-react';
import { useSearchParams } from 'react-router-dom';

function useDebounce(value, delay) {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
}

function CurrentMenu() {
  const { t } = useTranslation();
  const { token } = useContext(AuthContext);
  const { formatCurrency } = useCurrency();
  const [searchParams, setSearchParams] = useSearchParams();
  const backendUrl = process.env.REACT_APP_BACKEND_URL;

  const [currentMenu, setCurrentMenu] = useState(null);
  const [menuItems, setMenuItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Filters
  const [searchTerm, setSearchTerm] = useState(searchParams.get('search') || '');
  const [categoryFilter, setCategoryFilter] = useState(searchParams.get('category') || 'all');
  const [activeFilter, setActiveFilter] = useState(searchParams.get('active') || 'all');
  
  // Debounced search
  const debouncedSearchTerm = useDebounce(searchTerm, 300);
  
  // Modals
  const [showCreateMenu, setShowCreateMenu] = useState(false);
  const [showAddItems, setShowAddItems] = useState(false);
  const [showEditMenu, setShowEditMenu] = useState(false);
  
  // Form data
  const [menuForm, setMenuForm] = useState({
    name: '',
    description: '',
    effectiveFrom: new Date().toISOString().split('T')[0],
    effectiveTo: '',
    isActive: true
  });
  
  // Available items to add
  const [availableItems, setAvailableItems] = useState([]);
  const [selectedItems, setSelectedItems] = useState([]);
  const [itemsSearchTerm, setItemsSearchTerm] = useState('');

  // Fetch current menu
  const fetchCurrentMenu = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${backendUrl}/api/menu/current`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to load menu');
      }

      const data = await response.json();
      setCurrentMenu(data.menu);
      setMenuItems(data.items || []);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCurrentMenu();
  }, []);

  // Update URL when filters change
  useEffect(() => {
    const params = {};
    if (debouncedSearchTerm) params.search = debouncedSearchTerm;
    if (categoryFilter !== 'all') params.category = categoryFilter;
    if (activeFilter !== 'all') params.active = activeFilter;
    setSearchParams(params);
  }, [debouncedSearchTerm, categoryFilter, activeFilter]);

  // Filter menu items
  const filteredItems = menuItems.filter((item) => {
    const matchesSearch =
      !debouncedSearchTerm ||
      item.name?.toLowerCase().includes(debouncedSearchTerm.toLowerCase()) ||
      item.displayName?.toLowerCase().includes(debouncedSearchTerm.toLowerCase());

    const matchesCategory =
      categoryFilter === 'all' ||
      (categoryFilter === 'kitchen' && item.recipeType === 'kitchen') ||
      (categoryFilter === 'bar' && item.recipeType === 'bar');

    const matchesActive =
      activeFilter === 'all' ||
      (activeFilter === 'active' && item.isActive) ||
      (activeFilter === 'inactive' && !item.isActive);

    return matchesSearch && matchesCategory && matchesActive;
  });

  // Create menu
  const handleCreateMenu = async () => {
    try {
      const response = await fetch(`${backendUrl}/api/menu`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(menuForm),
      });

      if (!response.ok) {
        let errorMessage = 'Failed to create menu';
        try {
          const error = await response.json();
          errorMessage = error.detail || errorMessage;
        } catch (e) {
          // If response is not JSON, use default message
        }
        throw new Error(errorMessage);
      }

      // Consume the response body
      await response.json();

      setShowCreateMenu(false);
      fetchCurrentMenu();
      alert(t('currentMenu.success.created'));
    } catch (err) {
      alert(t('currentMenu.error.create') + ': ' + err.message);
    }
  };

  // Update menu
  const handleUpdateMenu = async () => {
    try {
      const response = await fetch(`${backendUrl}/api/menu/${currentMenu.id}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(menuForm),
      });

      if (!response.ok) {
        let errorMessage = 'Failed to update menu';
        try {
          const error = await response.json();
          errorMessage = error.detail || errorMessage;
        } catch (e) {
          // If response is not JSON, use default message
        }
        throw new Error(errorMessage);
      }

      // Consume the response body
      await response.json();

      setShowEditMenu(false);
      fetchCurrentMenu();
      alert(t('currentMenu.success.updated'));
    } catch (err) {
      alert(t('currentMenu.error.update') + ': ' + err.message);
    }
  };

  // Delete menu
  const handleDeleteMenu = async () => {
    if (!window.confirm(t('currentMenu.confirm.deleteMenu'))) {
      return;
    }

    try {
      const response = await fetch(`${backendUrl}/api/menu/${currentMenu.id}`, {
        method: 'DELETE',
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        let errorMessage = 'Failed to delete menu';
        try {
          const error = await response.json();
          errorMessage = error.detail || errorMessage;
        } catch (e) {
          // If response is not JSON, use default message
        }
        throw new Error(errorMessage);
      }

      // Consume the response body
      await response.json();

      fetchCurrentMenu();
      alert(t('currentMenu.success.deleted'));
    } catch (err) {
      alert(t('currentMenu.error.delete') + ': ' + err.message);
    }
  };

  // Toggle item active status
  const handleToggleItemActive = async (itemId, currentStatus) => {
    try {
      const response = await fetch(`${backendUrl}/api/menu/${currentMenu.id}/items/${itemId}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ isActive: !currentStatus }),
      });

      if (!response.ok) {
        let errorMessage = 'Failed to update item';
        try {
          const error = await response.json();
          errorMessage = error.detail || errorMessage;
        } catch (e) {
          // If response is not JSON, use default message
        }
        throw new Error(errorMessage);
      }

      // Consume the response body
      await response.json();

      fetchCurrentMenu();
    } catch (err) {
      alert(t('currentMenu.error.update') + ': ' + err.message);
    }
  };

  // Delete item
  const handleDeleteItem = async (itemId) => {
    if (!window.confirm(t('currentMenu.confirm.deleteItem'))) {
      return;
    }

    try {
      const response = await fetch(`${backendUrl}/api/menu/${currentMenu.id}/items/${itemId}`, {
        method: 'DELETE',
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to delete item');
      }

      fetchCurrentMenu();
      alert(t('currentMenu.success.itemDeleted'));
    } catch (err) {
      alert(t('currentMenu.error.delete') + ': ' + err.message);
    }
  };

  // Fetch available items (ingredients, preparations, recipes)
  const fetchAvailableItems = async () => {
    try {
      const [ingredientsRes, preparationsRes, recipesRes] = await Promise.all([
        fetch(`${backendUrl}/api/ingredients`, {
          headers: { Authorization: `Bearer ${token}` },
        }),
        fetch(`${backendUrl}/api/preparations`, {
          headers: { Authorization: `Bearer ${token}` },
        }),
        fetch(`${backendUrl}/api/recipes`, {
          headers: { Authorization: `Bearer ${token}` },
        }),
      ]);

      const ingredients = await ingredientsRes.json();
      const preparations = await preparationsRes.json();
      const recipes = await recipesRes.json();

      const allItems = [
        ...ingredients.map((i) => ({ ...i, refType: 'ingredient' })),
        ...preparations.map((p) => ({ ...p, refType: 'preparation' })),
        ...recipes.map((r) => ({ ...r, refType: 'recipe' })),
      ];

      setAvailableItems(allItems);
    } catch (err) {
      console.error('Failed to load available items:', err);
    }
  };

  // Add items to menu
  const handleAddItems = async () => {
    if (selectedItems.length === 0) {
      alert('Please select at least one item');
      return;
    }

    try {
      const itemsToAdd = selectedItems.map((item) => ({
        refType: item.refType,
        refId: item.id,
        displayName: null,
        price: null,
        tags: [],
        isActive: true,
      }));

      const response = await fetch(`${backendUrl}/api/menu/${currentMenu.id}/items`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(itemsToAdd),
      });

      if (!response.ok) {
        throw new Error('Failed to add items');
      }

      setShowAddItems(false);
      setSelectedItems([]);
      fetchCurrentMenu();
      alert(t('currentMenu.success.itemsAdded'));
    } catch (err) {
      alert(t('currentMenu.error.addItems') + ': ' + err.message);
    }
  };

  // Availability badge
  const getAvailabilityBadge = (status) => {
    if (status === 'available') {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
          <CheckCircle className="w-3 h-3" />
          {t('currentMenu.available')}
        </span>
      );
    }
    if (status === 'low') {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
          <AlertCircle className="w-3 h-3" />
          {t('currentMenu.low')}
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800">
        <XCircle className="w-3 h-3" />
        {t('currentMenu.out')}
      </span>
    );
  };

  // Calculate margin
  const calculateMargin = (cost, price) => {
    if (!price || price <= 0) return { absolute: null, percentage: null };
    const absolute = price - cost;
    const percentage = (absolute / price) * 100;
    return { absolute, percentage };
  };

  if (loading) {
    return (
      <div className="glass-morphism rounded-2xl p-8 text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-600 mx-auto"></div>
        <p className="mt-4 text-gray-600">{t('common.loading')}</p>
      </div>
    );
  }

  return (
    <div>
      {/* Header */}
      <div className="glass-morphism rounded-2xl p-6 mb-6">
        <div className="flex justify-between items-start">
          <div>
            <h1 className="text-3xl font-bold gradient-text mb-2">{t('currentMenu.title')}</h1>
            <p className="text-gray-600">{t('currentMenu.subtitle')}</p>
          </div>
          {!currentMenu && (
            <Button
              onClick={() => {
                setMenuForm({
                  name: '',
                  description: '',
                  effectiveFrom: new Date().toISOString().split('T')[0],
                  effectiveTo: '',
                  isActive: true,
                });
                setShowCreateMenu(true);
              }}
              className="bg-gradient-to-r from-emerald-500 to-teal-600 text-white"
            >
              <Plus className="w-4 h-4 mr-2" />
              {t('currentMenu.createMenu')}
            </Button>
          )}
        </div>

        {currentMenu && (
          <div className="mt-4 flex gap-4 items-center">
            <div className="flex-1">
              <h2 className="text-xl font-semibold text-gray-800">{currentMenu.name}</h2>
              {currentMenu.description && (
                <p className="text-sm text-gray-600">{currentMenu.description}</p>
              )}
              <p className="text-xs text-gray-500 mt-1">
                {t('currentMenu.effectiveFrom')}: {currentMenu.effectiveFrom}
                {currentMenu.effectiveTo && ` - ${currentMenu.effectiveTo}`}
              </p>
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setMenuForm({
                    name: currentMenu.name,
                    description: currentMenu.description || '',
                    effectiveFrom: currentMenu.effectiveFrom,
                    effectiveTo: currentMenu.effectiveTo || '',
                    isActive: currentMenu.isActive,
                  });
                  setShowEditMenu(true);
                }}
              >
                <Edit className="w-4 h-4 mr-2" />
                {t('currentMenu.editMenu')}
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  fetchAvailableItems();
                  setShowAddItems(true);
                }}
              >
                <Plus className="w-4 h-4 mr-2" />
                {t('currentMenu.addItems')}
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={handleDeleteMenu}
                className="text-red-600 hover:bg-red-50"
              >
                <Trash2 className="w-4 h-4 mr-2" />
                {t('currentMenu.delete')}
              </Button>
            </div>
          </div>
        )}
      </div>

      {/* No active menu state */}
      {!currentMenu && (
        <div className="glass-morphism rounded-2xl p-12 text-center">
          <div className="max-w-md mx-auto">
            <div className="w-16 h-16 bg-gradient-to-br from-emerald-100 to-teal-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <Filter className="w-8 h-8 text-emerald-600" />
            </div>
            <h3 className="text-xl font-semibold text-gray-800 mb-2">{t('currentMenu.noActiveMenu')}</h3>
            <p className="text-gray-600 mb-6">{t('currentMenu.noActiveMenuDesc')}</p>
          </div>
        </div>
      )}

      {/* Menu items */}
      {currentMenu && (
        <>
          {/* Filters */}
          <div className="glass-morphism rounded-2xl p-4 mb-6">
            <div className="flex flex-col md:flex-row gap-4">
              <div className="flex-1">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
                  <input
                    type="text"
                    placeholder={t('currentMenu.searchItems')}
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="w-full pl-10 pr-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  />
                </div>
              </div>
              <div className="flex gap-2">
                <select
                  value={categoryFilter}
                  onChange={(e) => setCategoryFilter(e.target.value)}
                  className="px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500"
                >
                  <option value="all">{t('currentMenu.filter.all')}</option>
                  <option value="kitchen">{t('currentMenu.filter.kitchen')}</option>
                  <option value="bar">{t('currentMenu.filter.bar')}</option>
                </select>
                <select
                  value={activeFilter}
                  onChange={(e) => setActiveFilter(e.target.value)}
                  className="px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500"
                >
                  <option value="all">{t('currentMenu.filter.all')}</option>
                  <option value="active">{t('currentMenu.filter.active')}</option>
                  <option value="inactive">{t('currentMenu.filter.inactive')}</option>
                </select>
              </div>
            </div>
          </div>

          {/* Items table */}
          <div className="glass-morphism rounded-2xl overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gradient-to-r from-emerald-50 to-teal-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">
                      {t('currentMenu.item')}
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">
                      {t('currentMenu.source')}
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">
                      {t('currentMenu.category')}
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">
                      {t('currentMenu.availability')}
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-700 uppercase tracking-wider">
                      {t('currentMenu.cost')}
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-700 uppercase tracking-wider">
                      {t('currentMenu.price')}
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-700 uppercase tracking-wider">
                      {t('currentMenu.margin')}
                    </th>
                    <th className="px-6 py-3 text-center text-xs font-medium text-gray-700 uppercase tracking-wider">
                      {t('currentMenu.active')}
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-700 uppercase tracking-wider">
                      {t('common.actions')}
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {filteredItems.map((item) => {
                    const margin = calculateMargin(item.computedCost, item.price);
                    return (
                      <tr key={item.id} className="hover:bg-emerald-50/50 transition-colors">
                        <td className="px-6 py-4">
                          <div className="font-medium text-gray-900">
                            {item.displayName || item.name}
                          </div>
                          {item.allergens && item.allergens.length > 0 && (
                            <div className="flex flex-wrap gap-1 mt-1">
                              {item.allergens.map((allergen) => (
                                <span
                                  key={allergen}
                                  className="inline-block px-2 py-0.5 rounded-full text-xs bg-red-100 text-red-800"
                                >
                                  {t(`allergens.${allergen.toUpperCase()}`)}
                                </span>
                              ))}
                            </div>
                          )}
                        </td>
                        <td className="px-6 py-4 text-sm text-gray-600 capitalize">{item.refType}</td>
                        <td className="px-6 py-4 text-sm text-gray-600">
                          {item.recipeType ? t(`recipes.${item.recipeType}`) : item.category}
                        </td>
                        <td className="px-6 py-4">{getAvailabilityBadge(item.availabilityStatus)}</td>
                        <td className="px-6 py-4 text-right text-sm text-gray-900">
                          {formatCurrency(item.computedCost || 0)}
                        </td>
                        <td className="px-6 py-4 text-right text-sm text-gray-900">
                          {item.price ? formatCurrency(item.price) : '—'}
                        </td>
                        <td className="px-6 py-4 text-right text-sm">
                          {margin.absolute !== null ? (
                            <div>
                              <div className="font-medium text-gray-900">
                                {formatCurrency(margin.absolute)}
                              </div>
                              <div
                                className={`text-xs ${
                                  margin.percentage > 0 ? 'text-green-600' : 'text-red-600'
                                }`}
                              >
                                {margin.percentage.toFixed(1)}%
                              </div>
                            </div>
                          ) : (
                            '—'
                          )}
                        </td>
                        <td className="px-6 py-4 text-center">
                          <button
                            onClick={() => handleToggleItemActive(item.id, item.isActive)}
                            className={`p-1 rounded-lg transition-colors ${
                              item.isActive
                                ? 'text-green-600 hover:bg-green-50'
                                : 'text-gray-400 hover:bg-gray-50'
                            }`}
                          >
                            {item.isActive ? <Power className="w-5 h-5" /> : <PowerOff className="w-5 h-5" />}
                          </button>
                        </td>
                        <td className="px-6 py-4 text-right">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleDeleteItem(item.id)}
                            className="text-red-600 hover:bg-red-50"
                          >
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>

              {filteredItems.length === 0 && (
                <div className="p-12 text-center text-gray-500">
                  {t('common.noResults')}
                </div>
              )}
            </div>
          </div>
        </>
      )}

      {/* Create Menu Modal */}
      {showCreateMenu && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl p-6 max-w-md w-full mx-4">
            <h2 className="text-2xl font-bold gradient-text mb-4">{t('currentMenu.createMenu')}</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {t('currentMenu.menuName')}
                </label>
                <input
                  type="text"
                  value={menuForm.name}
                  onChange={(e) => setMenuForm({ ...menuForm, name: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {t('currentMenu.description')}
                </label>
                <textarea
                  value={menuForm.description}
                  onChange={(e) => setMenuForm({ ...menuForm, description: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  rows={3}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {t('currentMenu.effectiveFrom')}
                </label>
                <input
                  type="date"
                  value={menuForm.effectiveFrom}
                  onChange={(e) => setMenuForm({ ...menuForm, effectiveFrom: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {t('currentMenu.effectiveTo')}
                </label>
                <input
                  type="date"
                  value={menuForm.effectiveTo}
                  onChange={(e) => setMenuForm({ ...menuForm, effectiveTo: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={menuForm.isActive}
                  onChange={(e) => setMenuForm({ ...menuForm, isActive: e.target.checked })}
                  className="w-4 h-4 text-emerald-600"
                />
                <label className="text-sm font-medium text-gray-700">{t('currentMenu.isActive')}</label>
              </div>
            </div>
            <div className="flex gap-3 mt-6">
              <Button onClick={() => setShowCreateMenu(false)} variant="outline" className="flex-1">
                {t('common.cancel')}
              </Button>
              <Button
                onClick={handleCreateMenu}
                className="flex-1 bg-gradient-to-r from-emerald-500 to-teal-600 text-white"
              >
                {t('common.create')}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Edit Menu Modal */}
      {showEditMenu && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl p-6 max-w-md w-full mx-4">
            <h2 className="text-2xl font-bold gradient-text mb-4">{t('currentMenu.editMenu')}</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {t('currentMenu.menuName')}
                </label>
                <input
                  type="text"
                  value={menuForm.name}
                  onChange={(e) => setMenuForm({ ...menuForm, name: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {t('currentMenu.description')}
                </label>
                <textarea
                  value={menuForm.description}
                  onChange={(e) => setMenuForm({ ...menuForm, description: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  rows={3}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {t('currentMenu.effectiveFrom')}
                </label>
                <input
                  type="date"
                  value={menuForm.effectiveFrom}
                  onChange={(e) => setMenuForm({ ...menuForm, effectiveFrom: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {t('currentMenu.effectiveTo')}
                </label>
                <input
                  type="date"
                  value={menuForm.effectiveTo}
                  onChange={(e) => setMenuForm({ ...menuForm, effectiveTo: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={menuForm.isActive}
                  onChange={(e) => setMenuForm({ ...menuForm, isActive: e.target.checked })}
                  className="w-4 h-4 text-emerald-600"
                />
                <label className="text-sm font-medium text-gray-700">{t('currentMenu.isActive')}</label>
              </div>
            </div>
            <div className="flex gap-3 mt-6">
              <Button onClick={() => setShowEditMenu(false)} variant="outline" className="flex-1">
                {t('common.cancel')}
              </Button>
              <Button
                onClick={handleUpdateMenu}
                className="flex-1 bg-gradient-to-r from-emerald-500 to-teal-600 text-white"
              >
                {t('common.save')}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Add Items Modal */}
      {showAddItems && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl p-6 max-w-3xl w-full max-h-[80vh] overflow-y-auto">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-2xl font-bold gradient-text">{t('currentMenu.selectItems')}</h2>
              <button onClick={() => setShowAddItems(false)} className="text-gray-400 hover:text-gray-600">
                <X className="w-6 h-6" />
              </button>
            </div>

            <div className="mb-4">
              <input
                type="text"
                placeholder={t('currentMenu.searchItems')}
                value={itemsSearchTerm}
                onChange={(e) => setItemsSearchTerm(e.target.value)}
                className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500"
              />
            </div>

            <div className="space-y-2 max-h-96 overflow-y-auto mb-4">
              {availableItems
                .filter((item) =>
                  item.name.toLowerCase().includes(itemsSearchTerm.toLowerCase())
                )
                .map((item) => {
                  const isSelected = selectedItems.some((s) => s.id === item.id);
                  return (
                    <div
                      key={`${item.refType}-${item.id}`}
                      onClick={() => {
                        if (isSelected) {
                          setSelectedItems(selectedItems.filter((s) => s.id !== item.id));
                        } else {
                          setSelectedItems([...selectedItems, item]);
                        }
                      }}
                      className={`p-4 border rounded-lg cursor-pointer transition-colors ${
                        isSelected
                          ? 'border-emerald-500 bg-emerald-50'
                          : 'border-gray-200 hover:border-emerald-300'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                          <div className="font-medium text-gray-900">{item.name}</div>
                          <div className="text-sm text-gray-500 capitalize">{item.refType}</div>
                        </div>
                        {isSelected && <Check className="w-5 h-5 text-emerald-600" />}
                      </div>
                    </div>
                  );
                })}
            </div>

            <div className="flex gap-3">
              <Button onClick={() => setShowAddItems(false)} variant="outline" className="flex-1">
                {t('common.cancel')}
              </Button>
              <Button
                onClick={handleAddItems}
                className="flex-1 bg-gradient-to-r from-emerald-500 to-teal-600 text-white"
                disabled={selectedItems.length === 0}
              >
                {t('common.add')} ({selectedItems.length})
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default CurrentMenu;
