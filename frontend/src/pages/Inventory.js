import React, { useState, useEffect, useContext } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useCurrency } from '../contexts/CurrencyContext';
import { useTranslation } from 'react-i18next';
import axios from 'axios';
import { API, AuthContext } from '../App';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogDescription, DialogFooter } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Plus, Trash2, Package, DollarSign, TrendingUp, X } from 'lucide-react';
import { toast } from 'sonner';
import { format } from 'date-fns';

function Inventory() {
  const { t } = useTranslation();
  const { user } = useContext(AuthContext);
  const { formatMinor } = useCurrency();
  const [searchParams, setSearchParams] = useSearchParams();
  const [inventory, setInventory] = useState([]);
  const [ingredients, setIngredients] = useState([]);
  const [valuation, setValuation] = useState([]);
  const [valuationSummary, setValuationSummary] = useState(null);
  const [adjustments, setAdjustments] = useState([]);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [isAdjustmentDialogOpen, setIsAdjustmentDialogOpen] = useState(false);
  const [showValuation, setShowValuation] = useState(true);
  
  // Get filters from URL
  const categoryFilter = searchParams.get('category');
  const filterType = searchParams.get('filter'); // lowStock, expiring
  
  const [formData, setFormData] = useState({
    ingredientId: '',
    qty: '',
    unit: 'g',
    countType: 'opening',
    batchExpiry: '',
    location: ''
  });

  const [adjustmentFormData, setAdjustmentFormData] = useState({
    ingredientId: '',
    qtyAdjustment: '',
    reason: ''
  });

  const [searchQuery, setSearchQuery] = useState(searchParams.get('search') || '');
  const [debouncedSearch, setDebouncedSearch] = useState(searchParams.get('search') || '');
  const [selectedItems, setSelectedItems] = useState([]);
  const [showBulkDeleteDialog, setShowBulkDeleteDialog] = useState(false);

  // Debounce search input (200ms)
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchQuery);
      // Update URL
      const newParams = new URLSearchParams(searchParams);
      if (searchQuery) {
        newParams.set('search', searchQuery);
      } else {
        newParams.delete('search');
      }
      setSearchParams(newParams, { replace: true });
    }, 200);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  useEffect(() => {
    fetchInventory();
    fetchIngredients();
    fetchValuation();
    fetchAdjustments();
  }, []);

  const fetchInventory = async () => {
    try {
      const response = await axios.get(`${API}/inventory`);
      setInventory(response.data);
    } catch (error) {
      toast.error(t('inventory.error.load') || 'Failed to load inventory');
    }
  };

  const fetchIngredients = async () => {
    try {
      const response = await axios.get(`${API}/ingredients`);
      setIngredients(response.data);
    } catch (error) {
      toast.error(t('ingredients.error.load') || 'Failed to load ingredients');
    }
  };

  const fetchValuation = async () => {
    try {
      const [valuationRes, summaryRes] = await Promise.all([
        axios.get(`${API}/inventory/valuation`),
        axios.get(`${API}/inventory/valuation/summary`)
      ]);
      setValuation(valuationRes.data);
      setValuationSummary(summaryRes.data);
    } catch (error) {
      console.error('Failed to load valuation:', error);
    }
  };

  const fetchAdjustments = async () => {
    try {
      const response = await axios.get(`${API}/inventory/adjustments`);
      setAdjustments(response.data);
    } catch (error) {
      console.error('Failed to load adjustments:', error);
    }
  };

  // RBAC: Check if user can edit
  const canEdit = user?.roleKey === 'admin' || user?.roleKey === 'manager';

  // Filter inventory based on search and URL filters
  const filteredInventory = React.useMemo(() => {
    return inventory.filter(item => {
      // Search filter
      const ingredient = ingredients.find(ing => ing.id === item.ingredientId);
      const matchesSearch = debouncedSearch === '' ||
        (ingredient?.name && ingredient.name.toLowerCase().includes(debouncedSearch.toLowerCase())) ||
        (item.location && item.location.toLowerCase().includes(debouncedSearch.toLowerCase()));

      // Category filter from URL
      const matchesCategory = !categoryFilter || item.category === categoryFilter;

      // Filter type (lowStock, expiring) - keep existing logic
      let matchesFilterType = true;
      if (filterType === 'lowStock') {
        // You can add low stock logic here if needed
        matchesFilterType = true;
      } else if (filterType === 'expiring') {
        // You can add expiring logic here if needed
        matchesFilterType = true;
      }

      return matchesSearch && matchesCategory && matchesFilterType;
    });
  }, [inventory, debouncedSearch, categoryFilter, filterType, ingredients]);

  // Bulk select handlers
  const toggleSelectAll = () => {
    if (selectedItems.length === filteredInventory.length && filteredInventory.length > 0) {
      setSelectedItems([]);
    } else {
      setSelectedItems(filteredInventory.map(item => item.id));
    }
  };

  const toggleSelectItem = (id) => {
    setSelectedItems(prev =>
      prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]
    );
  };

  // Bulk delete (deletes inventory records, NOT master ingredients)
  const handleBulkDelete = async () => {
    if (selectedItems.length === 0) return;

    try {
      // Delete all selected inventory records
      await Promise.all(selectedItems.map(id => axios.delete(`${API}/inventory/${id}`)));

      toast.success(
        t('inventory.success.bulkDelete', { count: selectedItems.length }) ||
        `${selectedItems.length} inventory records deleted successfully`
      );
      setSelectedItems([]);
      setShowBulkDeleteDialog(false);
      fetchInventory();
      fetchValuation(); // Refresh valuation after deleting inventory
    } catch (error) {
      const errorMsg = error.response?.data?.detail || t('inventory.error.bulkDelete') || 'Failed to delete inventory records';
      toast.error(errorMsg);
    }
  };

  const handleCategoryFilter = (category) => {
    const newParams = new URLSearchParams(searchParams);
    if (categoryFilter === category) {
      // Toggle off if clicking same category
      newParams.delete('category');
    } else {
      newParams.set('category', category);
    }
    setSearchParams(newParams);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    try {
      await axios.post(`${API}/inventory`, formData);
      toast.success('Inventory record created');
      fetchInventory();
      resetForm();
      setIsDialogOpen(false);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to save inventory');
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Are you sure you want to delete this inventory record?')) return;

    try {
      await axios.delete(`${API}/inventory/${id}`);
      toast.success('Inventory record deleted');
      fetchInventory();
    } catch (error) {
      toast.error('Failed to delete inventory record');
    }
  };

  const resetForm = () => {
    setFormData({
      ingredientId: '',
      qty: '',
      unit: 'g',
      countType: 'opening',
      batchExpiry: '',
      location: ''
    });
  };

  const handleAdjustmentSubmit = async (e) => {
    e.preventDefault();

    try {
      await axios.post(`${API}/inventory/adjustments`, {
        ingredientId: adjustmentFormData.ingredientId,
        qtyAdjustment: parseFloat(adjustmentFormData.qtyAdjustment),
        reason: adjustmentFormData.reason
      });
      toast.success(t('inventory.success.adjusted') || 'Adjustment created successfully');
      fetchInventory();
      fetchValuation();
      fetchAdjustments();
      resetAdjustmentForm();
      setIsAdjustmentDialogOpen(false);
    } catch (error) {
      toast.error(error.response?.data?.detail || t('inventory.error.adjust') || 'Failed to create adjustment');
    }
  };

  const resetAdjustmentForm = () => {
    setAdjustmentFormData({
      ingredientId: '',
      qtyAdjustment: '',
      reason: ''
    });
  };

  const getIngredientName = (id) => {
    const ing = ingredients.find(i => i.id === id);
    return ing ? ing.name : 'Unknown';
  };

  const getIngredient = (id) => {
    return ingredients.find(i => i.id === id);
  };

  const clearFilters = () => {
    setSearchParams({});
  };

  // Filter inventory based on URL params
  const getFilteredInventory = () => {
    let filtered = [...inventory];

    // Category filter (from valuation cards)
    if (categoryFilter) {
      filtered = filtered.filter(inv => {
        const ingredient = getIngredient(inv.ingredientId);
        return ingredient?.category === categoryFilter;
      });
    }

    // Low stock filter
    if (filterType === 'lowStock') {
      filtered = filtered.filter(inv => {
        const ingredient = getIngredient(inv.ingredientId);
        if (!ingredient) return false;
        
        // Calculate current stock
        const currentStock = filtered
          .filter(i => i.ingredientId === inv.ingredientId)
          .reduce((sum, i) => {
            if (i.countType === 'opening' || i.countType === 'adjustment' || i.countType === 'receiving') {
              return sum + i.qty;
            } else if (i.countType === 'closing') {
              return i.qty;
            }
            return sum;
          }, 0);
        
        return currentStock < ingredient.minStockQty;
      });
    }

    // Expiring filter
    if (filterType === 'expiring') {
      filtered = filtered.filter(inv => {
        if (!inv.batchExpiry) return false;
        const expiry = new Date(inv.batchExpiry);
        const now = new Date();
        const daysUntil = Math.ceil((expiry - now) / (1000 * 60 * 60 * 24));
        return daysUntil <= 3 && daysUntil >= 0;
      });
    }

    return filtered;
  };

  const filteredInventory = getFilteredInventory();

  const isExpiringSoon = (expiryDate) => {
    if (!expiryDate) return null;
    try {
      const expiry = new Date(expiryDate);
      const now = new Date();
      const daysUntil = Math.ceil((expiry - now) / (1000 * 60 * 60 * 24));
      
      if (daysUntil <= 1 && daysUntil >= 0) return 'text-red-600';
      if (daysUntil <= 2) return 'text-orange-600';
      if (daysUntil <= 3) return 'text-amber-600';
      return 'text-gray-600';
    } catch {
      return 'text-gray-600';
    }
  };

  return (
    <div className="space-y-6" data-testid="inventory-page">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold gradient-text mb-2">
            {t('inventory.title') || 'Inventory'}
          </h1>
          <p className="text-base text-gray-600">{t('inventory.subtitle')}</p>
        </div>

        <div className="flex gap-2">
          {user?.role === 'admin' && (
            <Dialog open={isAdjustmentDialogOpen} onOpenChange={(open) => {
              setIsAdjustmentDialogOpen(open);
              if (!open) resetAdjustmentForm();
            }}>
              <DialogTrigger asChild>
                <Button variant="outline">
                  <TrendingUp className="w-4 h-4 mr-2" />
                  {t('inventory.adjust') || 'Adjust'}
                </Button>
              </DialogTrigger>
              <DialogContent className="max-w-md">
                <DialogHeader>
                  <DialogTitle>{t('inventory.adjustmentTitle') || 'Manual Adjustment'}</DialogTitle>
                </DialogHeader>
                <form onSubmit={handleAdjustmentSubmit} className="space-y-4">
                  <div>
                    <Label htmlFor="adjustIngredient">{t('inventory.form.ingredient') || 'Ingredient'} *</Label>
                    <Select
                      value={adjustmentFormData.ingredientId}
                      onValueChange={(value) => setAdjustmentFormData({ ...adjustmentFormData, ingredientId: value })}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder={t('inventory.form.selectIngredient') || 'Select ingredient'} />
                      </SelectTrigger>
                      <SelectContent>
                        {ingredients.map(ing => (
                          <SelectItem key={ing.id} value={ing.id}>{ing.name}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label htmlFor="qtyAdjustment">{t('inventory.form.qtyAdjustment') || 'Quantity Adjustment'} *</Label>
                    <Input
                      id="qtyAdjustment"
                      type="number"
                      step="0.01"
                      value={adjustmentFormData.qtyAdjustment}
                      onChange={(e) => setAdjustmentFormData({ ...adjustmentFormData, qtyAdjustment: e.target.value })}
                      placeholder={t('inventory.form.adjustmentPlaceholder') || 'Positive or negative'}
                      required
                    />
                    <p className="text-xs text-muted-foreground mt-1">
                      {t('inventory.form.adjustmentHint') || 'Use negative values to reduce stock'}
                    </p>
                  </div>
                  <div>
                    <Label htmlFor="adjustReason">{t('inventory.form.reason') || 'Reason'} *</Label>
                    <textarea
                      id="adjustReason"
                      className="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                      value={adjustmentFormData.reason}
                      onChange={(e) => setAdjustmentFormData({ ...adjustmentFormData, reason: e.target.value })}
                      required
                    />
                  </div>
                  <div className="flex justify-end gap-2">
                    <Button type="button" variant="outline" onClick={() => setIsAdjustmentDialogOpen(false)}>
                      {t('common.cancel') || 'Cancel'}
                    </Button>
                    <Button type="submit">
                      {t('common.create') || 'Create'}
                    </Button>
                  </div>
                </form>
              </DialogContent>
            </Dialog>
          )}

          <Dialog open={isDialogOpen} onOpenChange={(open) => {
            setIsDialogOpen(open);
            if (!open) resetForm();
          }}>
            <DialogTrigger asChild>
              <Button className="btn-primary text-white" data-testid="add-inventory-button">
                <Plus className="w-4 h-4 mr-2" />
                {t('inventory.add') || 'Add Movement'}
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-md max-h-[90vh] overflow-y-auto" data-testid="inventory-dialog">
              <DialogHeader>
                <DialogTitle>New Inventory Movement</DialogTitle>
              </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="ingredient">Ingredient *</Label>
                <Select
                  value={formData.ingredientId}
                  onValueChange={(value) => {
                    const ing = ingredients.find(i => i.id === value);
                    setFormData({ ...formData, ingredientId: value, unit: ing?.unit || 'g' });
                  }}
                >
                  <SelectTrigger data-testid="inventory-ingredient-select">
                    <SelectValue placeholder="Select ingredient" />
                  </SelectTrigger>
                  <SelectContent>
                    {ingredients.map(ing => (
                      <SelectItem key={ing.id} value={ing.id}>{ing.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="qty">Quantity *</Label>
                  <Input
                    id="qty"
                    type="number"
                    step="0.01"
                    value={formData.qty}
                    onChange={(e) => setFormData({ ...formData, qty: e.target.value })}
                    required
                    data-testid="inventory-qty-input"
                    className="input-focus"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="countType">Count Type *</Label>
                  <Select
                    value={formData.countType}
                    onValueChange={(value) => setFormData({ ...formData, countType: value })}
                  >
                    <SelectTrigger data-testid="inventory-counttype-select">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="opening">Opening</SelectItem>
                      <SelectItem value="closing">Closing</SelectItem>
                      <SelectItem value="adjustment">Adjustment</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="batchExpiry">Batch Expiry Date</Label>
                <Input
                  id="batchExpiry"
                  type="date"
                  value={formData.batchExpiry}
                  onChange={(e) => setFormData({ ...formData, batchExpiry: e.target.value })}
                  data-testid="inventory-expiry-input"
                  className="input-focus"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="location">Location</Label>
                <Input
                  id="location"
                  value={formData.location}
                  onChange={(e) => setFormData({ ...formData, location: e.target.value })}
                  placeholder="e.g., Walk-in cooler, Shelf A"
                  data-testid="inventory-location-input"
                  className="input-focus"
                />
              </div>

              <Button type="submit" className="w-full btn-primary text-white" data-testid="save-inventory-button">
                Record Movement
              </Button>
            </form>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* Valuation Summary Cards */}
      {valuationSummary && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card 
            className="glass-morphism border-0 cursor-pointer hover:shadow-lg transition-shadow"
            onClick={() => handleCategoryFilter('food')}
          >
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                {t('inventory.valuation.food') || 'Food Inventory'}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-600">
                {formatMinor(valuationSummary.categories.food)}
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                {t('inventory.clickToFilter') || 'Click to filter'}
              </p>
            </CardContent>
          </Card>
          
          <Card 
            className="glass-morphism border-0 cursor-pointer hover:shadow-lg transition-shadow"
            onClick={() => handleCategoryFilter('beverage')}
          >
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                {t('inventory.valuation.beverage') || 'Beverage Inventory'}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-blue-600">
                {formatMinor(valuationSummary.categories.beverage)}
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                {t('inventory.clickToFilter') || 'Click to filter'}
              </p>
            </CardContent>
          </Card>
          
          <Card 
            className="glass-morphism border-0 cursor-pointer hover:shadow-lg transition-shadow"
            onClick={() => handleCategoryFilter('nofood')}
          >
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                {t('inventory.valuation.nofood') || 'Non-Food Inventory'}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-gray-600">
                {formatMinor(valuationSummary.categories.nofood)}
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                {t('inventory.clickToFilter') || 'Click to filter'}
              </p>
            </CardContent>
          </Card>
          
          <Card className="glass-morphism border-0 bg-gradient-to-br from-emerald-500 to-teal-600 text-white">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-white/90">
                {t('inventory.valuation.total') || 'Total Inventory Value'}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {formatMinor(valuationSummary.total)}
              </div>
              <p className="text-xs text-white/80 mt-1">
                {valuationSummary.itemCount} {t('inventory.valuation.items') || 'items'}
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Search Bar */}
      <div className="mb-6">
        <Input
          type="text"
          placeholder={t('inventory.search') || 'Search inventory...'}
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="max-w-md"
        />
      </div>

      {/* Active Filters Display */}
      {(categoryFilter || filterType) && (
        <div className="flex items-center gap-2 p-3 bg-blue-50 border border-blue-200 rounded-lg">
          <span className="text-sm font-medium text-blue-900">
            {t('inventory.activeFilters') || 'Active Filters'}:
          </span>
          {categoryFilter && (
            <span className="inline-flex items-center gap-1 px-2 py-1 bg-blue-100 text-blue-800 rounded text-sm">
              {t(`receiving.category.${categoryFilter}`) || categoryFilter}
            </span>
          )}
          {filterType === 'lowStock' && (
            <span className="inline-flex items-center gap-1 px-2 py-1 bg-amber-100 text-amber-800 rounded text-sm">
              {t('dashboard.lowStock') || 'Low Stock'}
            </span>
          )}
          {filterType === 'expiring' && (
            <span className="inline-flex items-center gap-1 px-2 py-1 bg-orange-100 text-orange-800 rounded text-sm">
              {t('dashboard.expiringSoon') || 'Expiring Soon'}
            </span>
          )}
          <Button
            size="sm"
            variant="ghost"
            onClick={clearFilters}
            className="ml-auto"
          >
            <X className="h-4 w-4 mr-1" />
            {t('common.clearFilters') || 'Clear Filters'}
          </Button>
        </div>
      )}

      {/* Bulk Actions Bar */}
      {canEdit && selectedItems.length > 0 && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="font-medium text-blue-900">
              {selectedItems.length} {t('common.selected') || 'selected'}
            </span>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setSelectedItems([])}
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
          <Button
            variant="destructive"
            size="sm"
            onClick={() => setShowBulkDeleteDialog(true)}
          >
            <Trash2 className="h-4 w-4 mr-2" />
            {t('common.deleteSelected') || 'Delete Selected'}
          </Button>
        </div>
      )}

      {/* Select All Checkbox */}
      {canEdit && filteredInventory.length > 0 && (
        <div className="flex items-center gap-2 mb-4">
          <input
            type="checkbox"
            id="select-all-inventory"
            checked={selectedItems.length === filteredInventory.length && filteredInventory.length > 0}
            onChange={toggleSelectAll}
            className="h-4 w-4"
          />
          <Label htmlFor="select-all-inventory" className="text-sm font-medium cursor-pointer">
            {t('common.selectAll') || 'Select All'}
          </Label>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredInventory.map((inv) => (
          <Card key={inv.id} className="glass-morphism border-0 card-hover" data-testid="inventory-card">
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                {canEdit && (
                  <input
                    type="checkbox"
                    checked={selectedItems.includes(inv.id)}
                    onChange={() => toggleSelectItem(inv.id)}
                    className="h-4 w-4 mr-2"
                    onClick={(e) => e.stopPropagation()}
                  />
                )}
                <div className="flex items-center gap-2">
                  <Package className="w-5 h-5 text-emerald-500" />
                  <span className="text-lg">{getIngredientName(inv.ingredientId)}</span>
                </div>
                {user?.role === 'admin' && (
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => handleDelete(inv.id)}
                    data-testid="delete-inventory-button"
                  >
                    <Trash2 className="w-4 h-4 text-red-500" />
                  </Button>
                )}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600">Quantity:</span>
                <span className="font-semibold text-emerald-600">{inv.qty} {inv.unit}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Type:</span>
                <span className="font-medium capitalize">{inv.countType}</span>
              </div>
              {inv.batchExpiry && (
                <div className="flex justify-between">
                  <span className="text-gray-600">Expires:</span>
                  <span className={`font-medium ${isExpiringSoon(inv.batchExpiry)}`}>
                    {format(new Date(inv.batchExpiry), 'MMM dd, yyyy')}
                  </span>
                </div>
              )}
              {inv.location && (
                <div className="flex justify-between">
                  <span className="text-gray-600">Location:</span>
                  <span className="font-medium">{inv.location}</span>
                </div>
              )}
              <div className="pt-2 border-t text-xs text-gray-500">
                {format(new Date(inv.createdAt), 'MMM dd, yyyy HH:mm')}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {filteredInventory.length === 0 && inventory.length > 0 && (
        <Card className="glass-morphism border-0">
          <CardContent className="flex flex-col items-center justify-center py-12">
            <p className="text-gray-500 mb-4">{t('common.noResults') || 'No inventory records match your filters'}</p>
            <Button
              variant="outline"
              onClick={() => {
                setSearchQuery('');
                setDebouncedSearch('');
                setSearchParams(new URLSearchParams());
              }}
            >
              {t('common.clearFilters') || 'Clear Filters'}
            </Button>
          </CardContent>
        </Card>
      )}

      {inventory.length === 0 && (
        <Card className="glass-morphism border-0">
          <CardContent className="flex flex-col items-center justify-center py-12">
            <p className="text-gray-500 mb-4">{`${t('inventory.noData')}`}</p>
            <Button className="btn-primary text-white" onClick={() => setIsDialogOpen(true)}>
              <Plus className="w-4 h-4 mr-2" />
              Add Your First Movement
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Bulk Delete Confirmation Dialog */}
      <Dialog open={showBulkDeleteDialog} onOpenChange={setShowBulkDeleteDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('common.confirmDelete') || 'Confirm Delete'}</DialogTitle>
            <DialogDescription>
              {t('inventory.confirmBulkDelete', { count: selectedItems.length }) ||
                `Are you sure you want to delete ${selectedItems.length} selected inventory records? This will not delete master ingredients. This action cannot be undone.`}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowBulkDeleteDialog(false)}>
              {t('common.cancel') || 'Cancel'}
            </Button>
            <Button variant="destructive" onClick={handleBulkDelete}>
              {t('common.delete') || 'Delete'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

export default Inventory;