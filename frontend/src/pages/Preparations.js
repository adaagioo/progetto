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
import { Checkbox } from '../components/ui/checkbox';
import { Plus, Trash2, Edit, AlertCircle, DollarSign, Package, X } from 'lucide-react';
import { toast } from 'sonner';

function Preparations() {
  const { t } = useTranslation();
  const { user } = useContext(AuthContext);
  const { formatMinor } = useCurrency();
  const [searchParams, setSearchParams] = useSearchParams();
  const [preparations, setPreparations] = useState([]);
  const [ingredients, setIngredients] = useState([]);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [searchQuery, setSearchQuery] = useState(searchParams.get('search') || '');
  const [debouncedSearch, setDebouncedSearch] = useState(searchParams.get('search') || '');
  const [selectedItems, setSelectedItems] = useState([]);
  const [showBulkDeleteDialog, setShowBulkDeleteDialog] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    items: [{ ingredientId: '', qty: '', unit: 'g' }],
    yield: { value: '', unit: 'portions' },
    shelfLife: { value: '', unit: 'days' },
    instructions: '',
    notes: ''
  });

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
    fetchPreparations();
    fetchIngredients();
  }, []);

  const fetchPreparations = async () => {
    try {
      const response = await axios.get(`${API}/preparations`);
      setPreparations(response.data);
    } catch (error) {
      toast.error(t('preparations.error.load') || 'Failed to load preparations');
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

  const handleSubmit = async (e) => {
    e.preventDefault();

    // Validate items
    const validItems = formData.items.filter(item => 
      item.ingredientId && item.qty
    );

    if (validItems.length === 0) {
      toast.error(t('preparations.error.noItems') || 'Please add at least one ingredient');
      return;
    }

    const payload = {
      name: formData.name,
      items: validItems.map(item => ({
        ingredientId: item.ingredientId,
        qty: parseFloat(item.qty),
        unit: item.unit
      })),
      yield_: formData.yield.value ? {
        value: parseFloat(formData.yield.value),
        unit: formData.yield.unit
      } : null,
      shelfLife: formData.shelfLife.value ? {
        value: parseInt(formData.shelfLife.value),
        unit: formData.shelfLife.unit
      } : null,
      notes: formData.notes || null
    };

    try {
      if (editingId) {
        await axios.put(`${API}/preparations/${editingId}`, payload);
        toast.success(t('preparations.success.updated') || 'Preparation updated successfully');
      } else {
        await axios.post(`${API}/preparations`, payload);
        toast.success(t('preparations.success.created') || 'Preparation created successfully');
      }
      fetchPreparations();
      resetForm();
      setIsDialogOpen(false);
    } catch (error) {
      toast.error(error.response?.data?.detail || t('preparations.error.save') || 'Failed to save preparation');
    }
  };

  const handleEdit = (prep) => {
    setEditingId(prep.id);
    setFormData({
      name: prep.name,
      items: prep.items.map(item => ({
        ingredientId: item.ingredientId,
        qty: item.qty.toString(),
        unit: item.unit
      })),
      yield: prep.yield_ || { value: '', unit: 'portions' },
      shelfLife: prep.shelfLife || { value: '', unit: 'days' },
      instructions: prep.instructions || '',
      notes: prep.notes || ''
    });
    setIsDialogOpen(true);
  };

  const handleDelete = async (id) => {
    if (!window.confirm(t('preparations.confirm.delete') || 'Are you sure you want to delete this preparation?')) return;

    try {
      await axios.delete(`${API}/preparations/${id}`);
      toast.success(t('preparations.success.deleted') || 'Preparation deleted');
      fetchPreparations();
    } catch (error) {
      toast.error(t('preparations.error.delete') || 'Failed to delete preparation');
    }
  };

  const resetForm = () => {
    setFormData({
      name: '',
      items: [{ ingredientId: '', qty: '', unit: 'g' }],
      yield: { value: '', unit: 'portions' },
      shelfLife: { value: '', unit: 'days' },
      instructions: '',
      notes: ''
    });
    setEditingId(null);
  };

  const addItem = () => {
    setFormData({
      ...formData,
      items: [...formData.items, { ingredientId: '', qty: '', unit: 'g' }]
    });
  };

  const removeItem = (index) => {
    const newItems = formData.items.filter((_, i) => i !== index);
    setFormData({ ...formData, items: newItems.length > 0 ? newItems : [{ ingredientId: '', qty: '', unit: 'g' }] });
  };

  const updateItem = (index, field, value) => {
    const newItems = [...formData.items];
    newItems[index][field] = value;
    
    // Auto-set unit from ingredient
    if (field === 'ingredientId') {
      const ingredient = ingredients.find(i => i.id === value);
      if (ingredient) {
        newItems[index].unit = ingredient.unit;
      }
    }
    
    setFormData({ ...formData, items: newItems });
  };

  const getIngredientName = (id) => {
    const ing = ingredients.find(i => i.id === id);
    return ing ? ing.name : 'Unknown';
  };

  // RBAC: Check if user can edit (admin or manager)
  const canEdit = user?.roleKey === 'admin' || user?.roleKey === 'manager';

  // Filter preparations based on search
  const filteredPreparations = React.useMemo(() => {
    return preparations.filter(prep => {
      const matchesSearch = debouncedSearch === '' ||
        prep.name.toLowerCase().includes(debouncedSearch.toLowerCase());
      return matchesSearch;
    });
  }, [preparations, debouncedSearch]);

  // Bulk select handlers
  const toggleSelectAll = () => {
    if (selectedItems.length === filteredPreparations.length && filteredPreparations.length > 0) {
      setSelectedItems([]);
    } else {
      setSelectedItems(filteredPreparations.map(p => p.id));
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
      // Check dependencies for all selected preparations
      const dependencyChecks = await Promise.all(
        selectedItems.map(async (id) => {
          try {
            const response = await axios.get(`${API}/preparations/${id}/dependencies`);
            return { id, ...response.data };
          } catch (error) {
            return { id, hasReferences: false, references: {} };
          }
        })
      );

      // Find preparations with dependencies
      const prepsWithDeps = dependencyChecks.filter(d => d.hasReferences);
      
      if (prepsWithDeps.length > 0) {
        toast.error(
          t('preparations.error.hasDependencies', { count: prepsWithDeps.length }) ||
          `Cannot delete: ${prepsWithDeps.length} preparations are referenced in recipes`
        );
        setShowBulkDeleteDialog(false);
        return;
      }

      // Delete all selected preparations
      await Promise.all(selectedItems.map(id => axios.delete(`${API}/preparations/${id}`)));
      
      toast.success(
        t('preparations.success.bulkDelete', { count: selectedItems.length }) ||
        `${selectedItems.length} preparations deleted successfully`
      );
      setSelectedItems([]);
      setShowBulkDeleteDialog(false);
      fetchPreparations();
    } catch (error) {
      const errorMsg = error.response?.data?.detail || t('preparations.error.bulkDelete') || 'Failed to delete preparations';
      toast.error(errorMsg);
    }
  };

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold">{t('preparations.title') || 'Preparations'}</h1>
          <p className="text-sm text-muted-foreground mt-1">
            {t('preparations.subtitle') || 'Manage sub-recipes and prepared ingredients'}
          </p>
        </div>
        {canEdit && (
          <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
            <DialogTrigger asChild>
              <Button onClick={resetForm} data-testid="add-preparation-btn">
                <Plus className="mr-2 h-4 w-4" />
                {t('preparations.add') || 'Add Preparation'}
              </Button>
            </DialogTrigger>
          <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>
                {editingId ? (t('preparations.edit') || 'Edit Preparation') : (t('preparations.add') || 'Add Preparation')}
              </DialogTitle>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <Label htmlFor="name">{t('preparations.form.name') || 'Name'} *</Label>
                <Input
                  id="name"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder={t('preparations.form.namePlaceholder') || 'e.g., Pizza Dough'}
                  required
                />
              </div>

              <div>
                <div className="flex justify-between items-center mb-2">
                  <Label>{t('preparations.form.ingredients') || 'Ingredients'} *</Label>
                  <Button type="button" size="sm" variant="outline" onClick={addItem}>
                    <Plus className="h-4 w-4 mr-1" />
                    {t('preparations.form.addIngredient') || 'Add Ingredient'}
                  </Button>
                </div>

                <div className="space-y-2">
                  {formData.items.map((item, index) => (
                    <Card key={index} className="p-3">
                      <div className="grid grid-cols-12 gap-2">
                        <div className="col-span-6">
                          <Label className="text-xs">{t('ingredients.title') || 'Ingredient'}</Label>
                          <Select
                            value={item.ingredientId}
                            onValueChange={(value) => updateItem(index, 'ingredientId', value)}
                          >
                            <SelectTrigger className="h-9">
                              <SelectValue placeholder={t('preparations.form.selectIngredient') || 'Select ingredient'} />
                            </SelectTrigger>
                            <SelectContent>
                              {ingredients.map(ing => (
                                <SelectItem key={ing.id} value={ing.id}>{ing.name}</SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>
                        <div className="col-span-3">
                          <Label className="text-xs">{t('preparations.form.qty') || 'Quantity'}</Label>
                          <Input
                            className="h-9"
                            type="number"
                            step="0.01"
                            value={item.qty}
                            onChange={(e) => updateItem(index, 'qty', e.target.value)}
                            required
                          />
                        </div>
                        <div className="col-span-2">
                          <Label className="text-xs">{t('preparations.form.unit') || 'Unit'}</Label>
                          <Input
                            className="h-9"
                            value={item.unit}
                            onChange={(e) => updateItem(index, 'unit', e.target.value)}
                          />
                        </div>
                        <div className="col-span-1 flex items-end">
                          <Button
                            type="button"
                            size="sm"
                            variant="ghost"
                            onClick={() => removeItem(index)}
                            disabled={formData.items.length === 1}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>
                    </Card>
                  ))}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>{t('preparations.form.yield') || 'Yield'}</Label>
                  <div className="grid grid-cols-2 gap-2">
                    <Input
                      type="number"
                      step="0.01"
                      placeholder={t('common.value') || 'Value'}
                      value={formData.yield.value}
                      onChange={(e) => setFormData({ 
                        ...formData, 
                        yield: { ...formData.yield, value: e.target.value }
                      })}
                    />
                    <Input
                      placeholder={t('preparations.form.yieldUnit') || 'Unit'}
                      value={formData.yield.unit}
                      onChange={(e) => setFormData({ 
                        ...formData, 
                        yield: { ...formData.yield, unit: e.target.value }
                      })}
                    />
                  </div>
                </div>

                <div>
                  <Label>{t('preparations.form.shelfLife') || 'Shelf Life'}</Label>
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

              <div>
                <Label htmlFor="instructions">{t('preparations.form.instructions') || 'Preparation Steps'}</Label>
                <textarea
                  id="instructions"
                  className="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                  value={formData.instructions}
                  onChange={(e) => setFormData({ ...formData, instructions: e.target.value })}
                  placeholder={t('preparations.form.instructionsPlaceholder') || 'Step-by-step preparation instructions...'}
                  rows={4}
                />
              </div>

              <div>
                <Label htmlFor="notes">{t('preparations.form.notes') || 'Notes'}</Label>
                <textarea
                  id="notes"
                  className="flex min-h-[60px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                  value={formData.notes}
                  onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                  placeholder={t('preparations.form.notesPlaceholder') || 'Additional notes...'}
                />
              </div>

              <div className="flex justify-end gap-2 pt-4 border-t">
                <Button type="button" variant="outline" onClick={() => setIsDialogOpen(false)}>
                  {t('common.cancel') || 'Cancel'}
                </Button>
                <Button type="submit">
                  {editingId ? (t('common.update') || 'Update') : (t('common.create') || 'Create')}
                </Button>
              </div>
            </form>
          </DialogContent>
          </Dialog>
        )}
      </div>

      {/* Search Bar */}
      <div className="mb-6">
        <Input
          type="text"
          placeholder={t('preparations.search') || 'Search preparations...'}
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full"
        />
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
      {canEdit && filteredPreparations.length > 0 && (
        <div className="flex items-center gap-2 mb-4">
          <Checkbox
            id="select-all-preparations"
            checked={selectedItems.length === filteredPreparations.length && filteredPreparations.length > 0}
            onCheckedChange={toggleSelectAll}
          />
          <Label htmlFor="select-all-preparations" className="text-sm font-medium cursor-pointer">
            {t('common.selectAll') || 'Select All'}
          </Label>
        </div>
      )}

      <div className="grid gap-4">
        {filteredPreparations.map((prep) => (
          <Card key={prep.id}>
            <CardHeader>
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <CardTitle className="flex items-center gap-2">
                    {prep.name}
                    {prep.yield_ && (
                      <span className="text-sm font-normal text-muted-foreground">
                        ({prep.yield_.value} {prep.yield_.unit})
                      </span>
                    )}
                  </CardTitle>
                  <div className="flex items-center gap-4 mt-2 text-sm">
                    <div className="flex items-center gap-1">
                      <DollarSign className="h-4 w-4 text-emerald-600" />
                      <span className="font-semibold text-emerald-600">
                        {formatMinor(prep.cost)}
                      </span>
                    </div>
                    {prep.shelfLife && (
                      <div className="flex items-center gap-1">
                        <Package className="h-4 w-4 text-blue-600" />
                        <span className="text-muted-foreground">
                          {prep.shelfLife.value} {prep.shelfLife.unit}
                        </span>
                      </div>
                    )}
                  </div>
                </div>
                {canEdit && (
                  <div className="flex gap-2">
                    <Button size="sm" variant="outline" onClick={() => handleEdit(prep)} data-testid={`edit-preparation-${prep.id}`}>
                      <Edit className="h-4 w-4" />
                    </Button>
                    <Button size="sm" variant="outline" onClick={() => handleDelete(prep.id)} data-testid={`delete-preparation-${prep.id}`}>
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                )}
              </div>
            </CardHeader>
            <CardContent>
              {prep.notes && (
                <div className="mb-3 text-sm text-muted-foreground">
                  <strong>{t('preparations.form.notes') || 'Notes'}:</strong> {prep.notes}
                </div>
              )}

              <div className="border-t pt-3">
                <h4 className="font-medium text-sm mb-2">{t('preparations.form.ingredients') || 'Ingredients'} ({prep.items.length})</h4>
                <div className="space-y-1">
                  {prep.items.map((item, idx) => (
                    <div key={idx} className="text-sm flex justify-between items-center p-2 bg-muted/30 rounded">
                      <span>{getIngredientName(item.ingredientId)}</span>
                      <span className="font-medium">{item.qty} {item.unit}</span>
                    </div>
                  ))}
                </div>
              </div>

              {prep.allergens && prep.allergens.length > 0 && (
                <div className="border-t pt-3 mt-3">
                  <div className="flex items-start gap-1">
                    <AlertCircle className="h-4 w-4 text-red-600 mt-0.5" />
                    <div className="flex-1">
                      <span className="text-xs font-medium text-red-600">{t('ingredients.allergens') || 'Allergens'}:</span>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {prep.allergens.map(allergen => (
                          <span key={allergen} className="text-xs bg-red-100 text-red-800 px-2 py-0.5 rounded">
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

        {preparations.length === 0 && (
          <div className="text-center py-12 text-muted-foreground">
            <Package className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p>{t('preparations.noData') || 'No preparations yet'}</p>
            <p className="text-sm mt-1">{t('preparations.addFirst') || 'Create your first sub-recipe'}</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default Preparations;
