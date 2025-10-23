import React, { useState, useEffect, useContext, useRef, useCallback } from 'react';
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
import { Checkbox } from '../components/ui/checkbox';
import { Plus, Trash2, Calculator, AlertCircle, Edit, Package, X } from 'lucide-react';
import { toast } from 'sonner';

function RecipesEnhanced() {
  const { t } = useTranslation();
  const { user } = useContext(AuthContext);
  const { format, formatMinor } = useCurrency();
  const [searchParams, setSearchParams] = useSearchParams();
  const [recipes, setRecipes] = useState([]);
  const [ingredients, setIngredients] = useState([]);
  const [preparations, setPreparations] = useState([]);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [searchQuery, setSearchQuery] = useState(searchParams.get('search') || '');
  const [debouncedSearch, setDebouncedSearch] = useState(searchParams.get('search') || '');
  const [selectedAllergenFilter, setSelectedAllergenFilter] = useState(searchParams.get('allergen') || 'all');
  const [selectedItems, setSelectedItems] = useState([]);
  const [showBulkDeleteDialog, setShowBulkDeleteDialog] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    category: '',
    portions: '1',
    targetFoodCostPct: '30',
    price: '',
    items: [],
    shelfLife: { value: '', unit: 'days' },
    instructions: ''
  });
  const [editingItemIndex, setEditingItemIndex] = useState(null);
  const inputRefs = useRef({});

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

  // Update URL when allergen filter changes
  useEffect(() => {
    const newParams = new URLSearchParams(searchParams);
    if (selectedAllergenFilter && selectedAllergenFilter !== 'all') {
      newParams.set('allergen', selectedAllergenFilter);
    } else {
      newParams.delete('allergen');
    }
    setSearchParams(newParams, { replace: true });
  }, [selectedAllergenFilter]);

  useEffect(() => {
    fetchRecipes();
    fetchIngredients();
    fetchPreparations();
  }, []);

  const fetchRecipes = async () => {
    try {
      const response = await axios.get(`${API}/recipes`);
      setRecipes(response.data);
    } catch (error) {
      toast.error(t('recipes.error.load') || 'Failed to load recipes');
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

  const fetchPreparations = async () => {
    try {
      const response = await axios.get(`${API}/preparations`);
      setPreparations(response.data);
    } catch (error) {
      console.error('Failed to load preparations:', error);
    }
  };

  // RBAC: Check if user can edit
  const canEdit = user?.roleKey === 'admin' || user?.roleKey === 'manager';

  // Bulk select handlers
  const toggleSelectAll = () => {
    if (selectedItems.length === filteredRecipes.length && filteredRecipes.length > 0) {
      setSelectedItems([]);
    } else {
      setSelectedItems(filteredRecipes.map(r => r.id));
    }
  };

  const toggleSelectItem = (id) => {
    setSelectedItems(prev =>
      prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]
    );
  };

  // Bulk delete with dependency checking
  const handleBulkDelete = async () => {
    if (selectedItems.length === 0) return;

    try {
      // Check dependencies for all selected recipes
      const dependencyChecks = await Promise.all(
        selectedItems.map(async (id) => {
          try {
            const response = await axios.get(`${API}/recipes/${id}/dependencies`);
            return { id, ...response.data };
          } catch (error) {
            return { id, hasReferences: false, references: {} };
          }
        })
      );

      // Find recipes with dependencies
      const recipesWithDeps = dependencyChecks.filter(d => d.hasReferences);
      
      if (recipesWithDeps.length > 0) {
        const totalSales = recipesWithDeps.reduce((sum, d) => sum + (d.references?.sales || 0), 0);
        toast.error(
          t('recipes.error.hasDependencies', { count: recipesWithDeps.length }) ||
          `Cannot delete: ${recipesWithDeps.length} recipes are referenced in sales records`
        );
        setShowBulkDeleteDialog(false);
        return;
      }

      // Delete all selected recipes
      await Promise.all(selectedItems.map(id => axios.delete(`${API}/recipes/${id}`)));
      
      toast.success(
        t('recipes.success.bulkDelete', { count: selectedItems.length }) ||
        `${selectedItems.length} recipes deleted successfully`
      );
      setSelectedItems([]);
      setShowBulkDeleteDialog(false);
      fetchRecipes();
    } catch (error) {
      const errorMsg = error.response?.data?.detail || t('recipes.error.bulkDelete') || 'Failed to delete recipes';
      toast.error(errorMsg);
    }
  };

  // Get unique allergens from all recipes for filter
  const uniqueAllergens = React.useMemo(() => {
    const allergenSet = new Set();
    recipes.forEach(recipe => {
      if (recipe.allergens && recipe.allergens.length > 0) {
        recipe.allergens.forEach(a => allergenSet.add(a));
      }
    });
    return Array.from(allergenSet).sort();
  }, [recipes]);

  // Filter recipes based on search and allergen filter
  const filteredRecipes = React.useMemo(() => {
    return recipes.filter(recipe => {
      // Search filter (using debounced search)
      const matchesSearch = debouncedSearch === '' || 
        recipe.name.toLowerCase().includes(debouncedSearch.toLowerCase());
      
      // Allergen filter
      const matchesAllergen = selectedAllergenFilter === 'all' ||
        (recipe.allergens && recipe.allergens.includes(selectedAllergenFilter));
      
      return matchesSearch && matchesAllergen;
    });
  }, [recipes, debouncedSearch, selectedAllergenFilter]);

  // Keyboard event handler
  const handleKeyDown = (e, index, field) => {
    // Ctrl/Cmd + Enter: Add new row
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      addNewItemRow();
      return;
    }

    // Escape: Cancel editing
    if (e.key === 'Escape') {
      e.preventDefault();
      setEditingItemIndex(null);
      return;
    }

    // Enter: Move to next field (not submit)
    if (e.key === 'Enter') {
      e.preventDefault();
      moveToNextField(index, field);
      return;
    }

    // Tab is handled by browser naturally
  };

  const moveToNextField = (index, currentField) => {
    const fields = ['type', 'itemId', 'qtyPerPortion', 'unit'];
    const currentFieldIndex = fields.indexOf(currentField);
    
    if (currentFieldIndex < fields.length - 1) {
      // Move to next field in same row
      const nextField = fields[currentFieldIndex + 1];
      const nextRef = inputRefs.current[`${index}-${nextField}`];
      if (nextRef) nextRef.focus();
    } else {
      // Move to first field of next row or add new row
      if (index < formData.items.length - 1) {
        const nextRef = inputRefs.current[`${index + 1}-type`];
        if (nextRef) nextRef.focus();
      }
    }
  };

  const addNewItemRow = () => {
    const newItem = {
      type: 'ingredient',
      itemId: '',
      qtyPerPortion: '',
      unit: 'g'
    };
    setFormData({
      ...formData,
      items: [...formData.items, newItem]
    });
    // Focus will be set after render
    setTimeout(() => {
      const newIndex = formData.items.length;
      const ref = inputRefs.current[`${newIndex}-type`];
      if (ref) ref.focus();
    }, 100);
  };

  const updateItem = (index, field, value) => {
    const newItems = [...formData.items];
    newItems[index][field] = value;
    
    // Auto-set unit when item changes
    if (field === 'itemId') {
      const item = newItems[index].type === 'ingredient' 
        ? ingredients.find(i => i.id === value)
        : preparations.find(p => p.id === value);
      if (item) {
        newItems[index].unit = item.unit || 'g';
      }
    }
    
    setFormData({ ...formData, items: newItems });
  };

  const removeItem = (index) => {
    setFormData({
      ...formData,
      items: formData.items.filter((_, i) => i !== index)
    });
  };

  // Calculate live cost breakdown
  const calculateItemCost = (item) => {
    if (item.type === 'ingredient') {
      const ing = ingredients.find(i => i.id === item.itemId);
      if (ing && item.qtyPerPortion) {
        // Use effectiveUnitCost which includes waste
        const costPerUnit = ing.effectiveUnitCost || ing.unitCost || 0;
        return (costPerUnit / 100) * parseFloat(item.qtyPerPortion);
      }
    } else if (item.type === 'preparation') {
      const prep = preparations.find(p => p.id === item.itemId);
      if (prep && item.qtyPerPortion) {
        // Preparation cost is already computed with waste
        return (prep.cost / 100) * parseFloat(item.qtyPerPortion);
      }
    }
    return 0;
  };

  const calculateTotalCost = () => {
    return formData.items.reduce((total, item) => total + calculateItemCost(item), 0);
  };

  const calculatePerPortionCost = () => {
    const totalCost = calculateTotalCost();
    const portions = parseInt(formData.portions) || 1;
    return totalCost / portions;
  };

  // Get allergens from all items
  const getAllergens = () => {
    const allergenSet = new Set();
    formData.items.forEach(item => {
      if (item.type === 'ingredient') {
        const ing = ingredients.find(i => i.id === item.itemId);
        if (ing && ing.allergens) {
          ing.allergens.forEach(a => allergenSet.add(a));
        }
      } else if (item.type === 'preparation') {
        const prep = preparations.find(p => p.id === item.itemId);
        if (prep && prep.allergens) {
          prep.allergens.forEach(a => allergenSet.add(a));
        }
      }
    });
    return Array.from(allergenSet).sort();
  };

  const getItemName = (item) => {
    if (item.type === 'preparation') {
      const prep = preparations.find(p => p.id === item.itemId);
      return prep ? prep.name : 'Unknown Preparation';
    } else {
      const ing = ingredients.find(i => i.id === item.itemId);
      return ing ? ing.name : 'Unknown Ingredient';
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (formData.items.length === 0) {
      toast.error(t('recipes.error.noItems') || 'Please add at least one item');
      return;
    }

    // Validate all items have required fields
    const invalidItems = formData.items.filter(item => !item.itemId || !item.qtyPerPortion);
    if (invalidItems.length > 0) {
      toast.error(t('recipes.error.incompleteItems') || 'Please complete all item fields');
      return;
    }

    const payload = {
      name: formData.name,
      category: formData.category,
      portions: parseInt(formData.portions),
      targetFoodCostPct: parseFloat(formData.targetFoodCostPct),
      price: parseFloat(formData.price) * 100, // Convert to minor units
      items: formData.items.map(item => ({
        type: item.type,
        itemId: item.itemId,
        qtyPerPortion: parseFloat(item.qtyPerPortion),
        unit: item.unit
      })),
      shelfLife: formData.shelfLife.value ? {
        value: parseInt(formData.shelfLife.value),
        unit: formData.shelfLife.unit
      } : null
    };

    try {
      if (editingId) {
        await axios.put(`${API}/recipes/${editingId}`, payload);
        toast.success(t('recipes.success.updated') || 'Recipe updated successfully');
      } else {
        await axios.post(`${API}/recipes`, payload);
        toast.success(t('recipes.success.created') || 'Recipe created successfully');
      }
      fetchRecipes();
      resetForm();
      setIsDialogOpen(false);
    } catch (error) {
      toast.error(error.response?.data?.detail || t('recipes.error.save') || 'Failed to save recipe');
    }
  };

  const handleEdit = (recipe) => {
    setEditingId(recipe.id);
    setFormData({
      name: recipe.name,
      category: recipe.category,
      portions: recipe.portions.toString(),
      targetFoodCostPct: recipe.targetFoodCostPct.toString(),
      price: (recipe.price / 100).toString(), // Convert from minor units
      items: recipe.items || [],
      shelfLife: recipe.shelfLife || { value: '', unit: 'days' },
      instructions: recipe.instructions || ''
    });
    setIsDialogOpen(true);
  };

  const handleDelete = async (id) => {
    if (!window.confirm(t('recipes.confirm.delete') || 'Are you sure you want to delete this recipe?')) return;

    try {
      await axios.delete(`${API}/recipes/${id}`);
      toast.success(t('recipes.success.deleted') || 'Recipe deleted');
      fetchRecipes();
    } catch (error) {
      toast.error(t('recipes.error.delete') || 'Failed to delete recipe');
    }
  };

  const resetForm = () => {
    setFormData({
      name: '',
      category: '',
      portions: '1',
      targetFoodCostPct: '30',
      price: '',
      items: [],
      shelfLife: { value: '', unit: 'days' },
      instructions: ''
    });
    setEditingId(null);
    setEditingItemIndex(null);
  };

  // Ctrl/Cmd + S handler
  useEffect(() => {
    const handleSave = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault();
        if (isDialogOpen && canEdit) {
          const form = document.querySelector('form');
          if (form) {
            form.requestSubmit();
            toast.success(t('common.saved') || 'Saving...');
          }
        }
      }
    };

    document.addEventListener('keydown', handleSave);
    return () => document.removeEventListener('keydown', handleSave);
  }, [isDialogOpen, canEdit]);

  const totalCost = calculateTotalCost();
  const perPortionCost = calculatePerPortionCost();
  const allergens = getAllergens();

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold">{t('recipes.title') || 'Recipes'}</h1>
          <p className="text-sm text-muted-foreground mt-1">
            {t('recipes.subtitle') || 'Manage your menu items and pricing'}
          </p>
        </div>
        {canEdit && (
          <Dialog open={isDialogOpen} onOpenChange={(open) => {
            setIsDialogOpen(open);
            if (!open) resetForm();
          }}>
            <DialogTrigger asChild>
              <Button onClick={resetForm} data-testid="add-recipe-btn">
                <Plus className="mr-2 h-4 w-4" />
                {t('recipes.add') || 'Add Recipe'}
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
              <DialogHeader>
                <DialogTitle>
                  {editingId ? (t('recipes.edit') || 'Edit Recipe') : (t('recipes.add') || 'Add Recipe')}
                </DialogTitle>
              </DialogHeader>
              <form onSubmit={handleSubmit} className="space-y-4">
                {/* Basic Info */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="name">{t('recipes.name') || 'Recipe Name'} *</Label>
                    <Input
                      id="name"
                      value={formData.name}
                      onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                      required
                    />
                  </div>
                  <div>
                    <Label htmlFor="category">{t('recipes.category') || 'Category'} *</Label>
                    <Input
                      id="category"
                      value={formData.category}
                      onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                      required
                    />
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <Label htmlFor="portions">{t('recipes.portions') || 'Portions'} *</Label>
                    <Input
                      id="portions"
                      type="number"
                      min="1"
                      value={formData.portions}
                      onChange={(e) => setFormData({ ...formData, portions: e.target.value })}
                      required
                    />
                  </div>
                  <div>
                    <Label htmlFor="price">{t('recipes.price') || 'Price'} *</Label>
                    <Input
                      id="price"
                      type="number"
                      step="0.01"
                      value={formData.price}
                      onChange={(e) => setFormData({ ...formData, price: e.target.value })}
                      required
                    />
                  </div>
                  <div>
                    <Label htmlFor="targetFoodCostPct">{t('recipes.targetCost') || 'Target Cost %'}</Label>
                    <Input
                      id="targetFoodCostPct"
                      type="number"
                      step="0.1"
                      value={formData.targetFoodCostPct}
                      onChange={(e) => setFormData({ ...formData, targetFoodCostPct: e.target.value })}
                    />
                  </div>
                </div>

                {/* Items Section */}
                <div className="border-t pt-4">
                  <div className="flex justify-between items-center mb-3">
                    <h3 className="font-semibold">{t('recipes.ingredients') || 'Ingredients & Preparations'}</h3>
                    <Button type="button" size="sm" variant="outline" onClick={addNewItemRow}>
                      <Plus className="h-4 w-4 mr-1" />
                      {t('recipes.addItem') || 'Add Item'} (Ctrl+Enter)
                    </Button>
                  </div>

                  <div className="space-y-2">
                    {formData.items.map((item, index) => (
                      <Card key={index} className="p-3">
                        <div className="grid grid-cols-12 gap-2 items-end">
                          <div className="col-span-2">
                            <Label className="text-xs">{t('common.type') || 'Type'}</Label>
                            <Select
                              value={item.type}
                              onValueChange={(value) => {
                                updateItem(index, 'type', value);
                                updateItem(index, 'itemId', ''); // Reset itemId when type changes
                              }}
                            >
                              <SelectTrigger className="h-9">
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="ingredient">Ingredient</SelectItem>
                                <SelectItem value="preparation">Preparation</SelectItem>
                              </SelectContent>
                            </Select>
                          </div>
                          <div className="col-span-4">
                            <Label className="text-xs">{t('recipes.item') || 'Item'}</Label>
                            <Select
                              value={item.itemId}
                              onValueChange={(value) => updateItem(index, 'itemId', value)}
                            >
                              <SelectTrigger className="h-9">
                                <SelectValue placeholder={t('recipes.selectItem') || 'Select...'} />
                              </SelectTrigger>
                              <SelectContent>
                                {item.type === 'ingredient' 
                                  ? ingredients.map(ing => (
                                      <SelectItem key={ing.id} value={ing.id}>{ing.name}</SelectItem>
                                    ))
                                  : preparations.map(prep => (
                                      <SelectItem key={prep.id} value={prep.id}>{prep.name}</SelectItem>
                                    ))
                                }
                              </SelectContent>
                            </Select>
                          </div>
                          <div className="col-span-2">
                            <Label className="text-xs">{t('recipes.qtyPerPortion') || 'Qty/Portion'}</Label>
                            <Input
                              className="h-9"
                              type="number"
                              step="0.01"
                              value={item.qtyPerPortion}
                              onChange={(e) => updateItem(index, 'qtyPerPortion', e.target.value)}
                              onKeyDown={(e) => handleKeyDown(e, index, 'qtyPerPortion')}
                              ref={(el) => inputRefs.current[`${index}-qtyPerPortion`] = el}
                            />
                          </div>
                          <div className="col-span-2">
                            <Label className="text-xs">{t('common.unit') || 'Unit'}</Label>
                            <Input
                              className="h-9"
                              value={item.unit}
                              onChange={(e) => updateItem(index, 'unit', e.target.value)}
                              onKeyDown={(e) => handleKeyDown(e, index, 'unit')}
                              ref={(el) => inputRefs.current[`${index}-unit`] = el}
                            />
                          </div>
                          <div className="col-span-1 flex items-center">
                            <span className="text-xs font-medium text-emerald-600">
                              {formatMinor(calculateItemCost(item) * 100)}
                            </span>
                          </div>
                          <div className="col-span-1">
                            <Button
                              type="button"
                              size="sm"
                              variant="ghost"
                              onClick={() => removeItem(index)}
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </div>
                        </div>
                      </Card>
                    ))}
                  </div>

                  {formData.items.length === 0 && (
                    <div className="text-center py-4 text-muted-foreground text-sm">
                      {t('recipes.noItems') || 'No items yet. Click "Add Item" or press Ctrl+Enter'}
                    </div>
                  )}
                </div>

                {/* Cost Breakdown */}
                {formData.items.length > 0 && (
                  <div className="border-t pt-3">
                    <h4 className="font-semibold mb-2 text-sm">{t('recipes.costBreakdown') || 'Cost Breakdown'}</h4>
                    <div className="grid grid-cols-3 gap-3 text-sm">
                      <div className="bg-muted/30 p-2 rounded">
                        <div className="text-xs text-muted-foreground">{t('recipes.totalCost') || 'Total Cost'}</div>
                        <div className="font-semibold text-emerald-600">{formatMinor(totalCost * 100)}</div>
                      </div>
                      <div className="bg-muted/30 p-2 rounded">
                        <div className="text-xs text-muted-foreground">{t('recipes.perPortion') || 'Per Portion'}</div>
                        <div className="font-semibold text-emerald-600">{formatMinor(perPortionCost * 100)}</div>
                      </div>
                      <div className="bg-muted/30 p-2 rounded">
                        <div className="text-xs text-muted-foreground">{t('recipes.foodCost') || 'Food Cost %'}</div>
                        <div className="font-semibold">
                          {formData.price ? ((totalCost / parseFloat(formData.price)) * 100).toFixed(1) : 0}%
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* Allergens Display */}
                {allergens.length > 0 && (
                  <div className="border-t pt-3">
                    <div className="flex items-start gap-1">
                      <AlertCircle className="h-4 w-4 text-red-600 mt-0.5" />
                      <div className="flex-1">
                        <span className="text-xs font-medium text-red-600">{t('common.allergens') || 'Allergens'}:</span>
                        <div className="flex flex-wrap gap-1 mt-1">
                          {allergens.map(allergen => (
                            <span key={allergen} className="text-xs bg-red-100 text-red-800 px-2 py-0.5 rounded">
                              {t(`allergens.${allergen.toUpperCase()}`) || allergen}
                            </span>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* Shelf Life */}
                <div className="grid grid-cols-2 gap-4 border-t pt-3">
                  <div>
                    <Label>{t('recipes.shelfLife') || 'Shelf Life'}</Label>
                    <div className="grid grid-cols-2 gap-2">
                      <Input
                        type="number"
                        placeholder={t('common.value') || 'Value'}
                        value={formData.shelfLife.value}
                        onChange={(e) => setFormData({ 
                          ...formData, 
                          shelfLife: { ...formData.shelfLife, value: e.target.value }
                        })}
                      />
                      <Select
                        value={formData.shelfLife.unit}
                        onValueChange={(value) => setFormData({ 
                          ...formData, 
                          shelfLife: { ...formData.shelfLife, unit: value }
                        })}
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="days">{t('common.days') || 'Days'}</SelectItem>
                          <SelectItem value="weeks">{t('common.weeks') || 'Weeks'}</SelectItem>
                          <SelectItem value="months">{t('common.months') || 'Months'}</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                </div>

                {/* Recipe Instructions */}
                <div className="border-t pt-3">
                  <Label htmlFor="instructions">{t('recipes.instructions') || 'Preparation Instructions'}</Label>
                  <textarea
                    id="instructions"
                    className="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 mt-2"
                    value={formData.instructions}
                    onChange={(e) => setFormData({ ...formData, instructions: e.target.value })}
                    placeholder={t('recipes.instructionsPlaceholder') || 'Step-by-step cooking instructions...'}
                    rows={4}
                  />
                </div>

                {/* Footer */}
                <div className="flex justify-end gap-2 pt-4 border-t">
                  <Button type="button" variant="outline" onClick={() => setIsDialogOpen(false)}>
                    {t('common.cancel') || 'Cancel'}
                  </Button>
                  <Button type="submit">
                    {editingId ? (t('common.update') || 'Update') : (t('common.create') || 'Create')} (Ctrl+S)
                  </Button>
                </div>
              </form>
            </DialogContent>
          </Dialog>
        )}
      </div>

      {/* Search and Filter Bar */}
      <div className="flex flex-col sm:flex-row gap-4 mb-6">
        <div className="flex-1">
          <Input
            type="text"
            placeholder={t('common.search') || 'Search recipes...'}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full"
          />
        </div>
        <div className="sm:w-64">
          <Select
            value={selectedAllergenFilter}
            onValueChange={setSelectedAllergenFilter}
          >
            <SelectTrigger>
              <SelectValue placeholder={t('recipes.filterByAllergen') || 'Filter by allergen'} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">{t('common.all') || 'All Recipes'}</SelectItem>
              {uniqueAllergens.map(allergen => (
                <SelectItem key={allergen} value={allergen}>
                  {t(`allergens.${allergen.toUpperCase()}`) || allergen}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

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
      {canEdit && filteredRecipes.length > 0 && (
        <div className="flex items-center gap-2 mb-4">
          <Checkbox
            id="select-all"
            checked={selectedItems.length === filteredRecipes.length && filteredRecipes.length > 0}
            onCheckedChange={toggleSelectAll}
          />
          <Label htmlFor="select-all" className="text-sm font-medium cursor-pointer">
            {t('common.selectAll') || 'Select All'}
          </Label>
        </div>
      )}

      {/* Recipe Cards */}
      <div className="grid gap-4">
        {filteredRecipes.map((recipe) => (
          <Card key={recipe.id}>
            <CardHeader>
              <div className="flex justify-between items-start">
                {canEdit && (
                  <div className="flex items-center mr-4">
                    <Checkbox
                      checked={selectedItems.includes(recipe.id)}
                      onCheckedChange={() => toggleSelectItem(recipe.id)}
                    />
                  </div>
                )}
                <div className="flex-1">
                  <CardTitle className="flex items-center gap-2">
                    {recipe.name}
                    <span className="text-sm font-normal text-muted-foreground">
                      ({recipe.portions} {t('recipes.portions') || 'portions'})
                    </span>
                  </CardTitle>
                  <div className="flex items-center gap-4 mt-2 text-sm">
                    <span className="font-semibold text-emerald-600">
                      {formatMinor(recipe.price)}
                    </span>
                    <span className="text-muted-foreground">{recipe.category}</span>
                  </div>
                </div>
                {canEdit && (
                  <div className="flex gap-2">
                    <Button size="sm" variant="outline" onClick={() => handleEdit(recipe)} data-testid={`edit-recipe-${recipe.id}`}>
                      <Edit className="h-4 w-4" />
                    </Button>
                    <Button size="sm" variant="outline" onClick={() => handleDelete(recipe.id)} data-testid={`delete-recipe-${recipe.id}`}>
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                )}
              </div>
            </CardHeader>
            <CardContent>
              <div className="border-t pt-3">
                <h4 className="font-medium text-sm mb-2">{t('recipes.ingredients') || 'Items'} ({recipe.items?.length || 0})</h4>
                <div className="space-y-1">
                  {recipe.items?.map((item, idx) => (
                    <div key={idx} className="text-sm flex justify-between items-center p-2 bg-muted/30 rounded">
                      <span>
                        <span className="text-xs text-muted-foreground mr-1">
                          [{item.type === 'preparation' ? 'P' : 'I'}]
                        </span>
                        {getItemName(item)}
                      </span>
                      <span className="font-medium">{item.qtyPerPortion} {item.unit}</span>
                    </div>
                  ))}
                </div>
              </div>

              {recipe.allergens && recipe.allergens.length > 0 && (
                <div className="border-t pt-3 mt-3">
                  <div className="flex items-start gap-1">
                    <AlertCircle className="h-4 w-4 text-red-600 mt-0.5" />
                    <div className="flex-1">
                      <span className="text-xs font-medium text-red-600">{t('common.allergens') || 'Allergens'}:</span>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {recipe.allergens.map(allergen => (
                          <span 
                            key={allergen} 
                            className="inline-block text-xs bg-red-100 text-red-800 px-2 py-0.5 rounded max-w-[120px] truncate"
                            title={t(`allergens.${allergen.toUpperCase()}`) || allergen}
                          >
                            {t(`allergens.${allergen.toUpperCase()}`) || allergen}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        ))}

        {filteredRecipes.length === 0 && recipes.length > 0 && (
          <Card>
            <CardContent className="flex flex-col items-center justify-center py-12">
              <p className="text-gray-500 mb-4">{t('common.noResults') || 'No recipes match your filters'}</p>
              <Button 
                variant="outline"
                onClick={() => {
                  setSearchQuery('');
                  setSelectedAllergenFilter('all');
                }}
              >
                {t('common.clearFilters') || 'Clear Filters'}
              </Button>
            </CardContent>
          </Card>
        )}

        {recipes.length === 0 && (
          <div className="text-center py-12 text-muted-foreground">
            <Package className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p>{t('recipes.noData') || 'No recipes yet'}</p>
            <p className="text-sm mt-1">{t('recipes.addFirst') || 'Create your first recipe'}</p>
          </div>
        )}
      </div>

      {/* Bulk Delete Confirmation Dialog */}
      <Dialog open={showBulkDeleteDialog} onOpenChange={setShowBulkDeleteDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('common.confirmDelete') || 'Confirm Delete'}</DialogTitle>
            <DialogDescription>
              {t('recipes.confirmBulkDelete', { count: selectedItems.length }) ||
                `Are you sure you want to delete ${selectedItems.length} selected recipes? This action cannot be undone.`}
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

export default RecipesEnhanced;
