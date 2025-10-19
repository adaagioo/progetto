import React, { useState, useEffect, useContext } from 'react';
import { useCurrency } from '../contexts/CurrencyContext';
import { useTranslation } from 'react-i18next';
import axios from 'axios';
import { API, AuthContext } from '../App';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Plus, Trash2, Edit, AlertCircle } from 'lucide-react';
import { toast } from 'sonner';

// EU-14 Official Allergens
const ALLERGENS = [
  'Cereals containing gluten',
  'Crustaceans',
  'Eggs',
  'Fish',
  'Peanuts',
  'Soybeans',
  'Milk',
  'Nuts',
  'Celery',
  'Mustard',
  'Sesame seeds',
  'Sulphur dioxide and sulphites',
  'Lupin',
  'Molluscs'
];

function Ingredients() {
  const { t } = useTranslation();
  const { user } = useContext(AuthContext);
  const { format } = useCurrency();
  const [ingredients, setIngredients] = useState([]);
  const [suppliers, setSuppliers] = useState([]);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [formData, setFormData] = useState({
    name: '',
    unit: 'g',
    packSize: '',
    packCost: '',
    supplier: '',
    preferredSupplierId: '',
    allergen: '',
    allergens: [],
    minStockQty: '',
    category: 'food',
    wastePct: '0',
    shelfLife: { value: '', unit: 'days' }
  });

  useEffect(() => {
    fetchIngredients();
    fetchSuppliers();
  }, []);

  const fetchSuppliers = async () => {
    try {
      const response = await axios.get(`${API}/suppliers`);
      setSuppliers(response.data);
    } catch (error) {
      console.error('Failed to load suppliers:', error);
    }
  };

  const fetchIngredients = async () => {
    try {
      const response = await axios.get(`${API}/ingredients`);
      setIngredients(response.data);
    } catch (error) {
      toast.error('Failed to load ingredients');
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    const payload = {
      ...formData,
      packSize: parseFloat(formData.packSize),
      packCost: parseFloat(formData.packCost),
      minStockQty: parseFloat(formData.minStockQty),
      wastePct: parseFloat(formData.wastePct),
      shelfLife: formData.shelfLife.value ? {
        value: parseInt(formData.shelfLife.value),
        unit: formData.shelfLife.unit
      } : null
    };

    try {
      if (editingId) {
        await axios.put(`${API}/ingredients/${editingId}`, payload);
        toast.success(t('ingredients.success.updated') || 'Ingredient updated successfully');
      } else {
        await axios.post(`${API}/ingredients`, payload);
        toast.success(t('ingredients.success.created') || 'Ingredient created successfully');
      }
      fetchIngredients();
      resetForm();
      setIsDialogOpen(false);
    } catch (error) {
      toast.error(error.response?.data?.detail || t('ingredients.error.save') || 'Failed to save ingredient');
    }
  };

  const handleEdit = (ingredient) => {
    setEditingId(ingredient.id);
    setFormData({
      name: ingredient.name,
      unit: ingredient.unit,
      packSize: ingredient.packSize.toString(),
      packCost: ingredient.packCost.toString(),
      supplier: ingredient.supplier || '',
      preferredSupplierId: ingredient.preferredSupplierId || '',
      allergen: ingredient.allergen || '',
      allergens: ingredient.allergens || [],
      minStockQty: ingredient.minStockQty.toString(),
      category: ingredient.category || 'food',
      wastePct: (ingredient.wastePct || 0).toString(),
      shelfLife: ingredient.shelfLife || { value: '', unit: 'days' }
    });
    setIsDialogOpen(true);
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Are you sure you want to delete this ingredient?')) return;

    try {
      await axios.delete(`${API}/ingredients/${id}`);
      toast.success('Ingredient deleted');
      fetchIngredients();
    } catch (error) {
      toast.error('Failed to delete ingredient');
    }
  };

  const resetForm = () => {
    setFormData({
      name: '',
      unit: 'g',
      packSize: '',
      packCost: '',
      supplier: '',
      allergen: '',
      allergens: [],
      minStockQty: '',
      category: 'food',
      wastePct: '0',
      shelfLife: { value: '', unit: 'days' }
    });
    setEditingId(null);
  };

  const toggleAllergen = (allergen) => {
    setFormData(prev => ({
      ...prev,
      allergens: prev.allergens.includes(allergen)
        ? prev.allergens.filter(a => a !== allergen)
        : [...prev.allergens, allergen]
    }));
  };

  return (
    <div className="space-y-6" data-testid="ingredients-page">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold gradient-text mb-2">
            Ingredients
          </h1>
          <p className="text-base text-gray-600">{t('ingredients.subtitle')}</p>
        </div>

        <Dialog open={isDialogOpen} onOpenChange={(open) => {
          setIsDialogOpen(open);
          if (!open) resetForm();
        }}>
          <DialogTrigger asChild>
            <Button className="btn-primary text-white" data-testid="add-ingredient-button">
              <Plus className="w-4 h-4 mr-2" />
              Add Ingredient
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-md max-h-[90vh] overflow-y-auto" data-testid="ingredient-dialog">
            <DialogHeader>
              <DialogTitle>{editingId ? 'Edit Ingredient' : 'New Ingredient'}</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="name">Name *</Label>
                <Input
                  id="name"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  required
                  data-testid="ingredient-name-input"
                  className="input-focus"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="unit">Unit *</Label>
                  <Select
                    value={formData.unit}
                    onValueChange={(value) => setFormData({ ...formData, unit: value })}
                  >
                    <SelectTrigger data-testid="ingredient-unit-select">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="g">grams (g)</SelectItem>
                      <SelectItem value="ml">milliliters (ml)</SelectItem>
                      <SelectItem value="pcs">pieces (pcs)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="packSize">Pack Size *</Label>
                  <Input
                    id="packSize"
                    type="number"
                    step="0.01"
                    value={formData.packSize}
                    onChange={(e) => setFormData({ ...formData, packSize: e.target.value })}
                    required
                    data-testid="ingredient-packsize-input"
                    className="input-focus"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="packCost">Pack Cost ($) *</Label>
                <Input
                  id="packCost"
                  type="number"
                  step="0.01"
                  value={formData.packCost}
                  onChange={(e) => setFormData({ ...formData, packCost: e.target.value })}
                  required
                  data-testid="ingredient-packcost-input"
                  className="input-focus"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="minStockQty">Min Stock Quantity *</Label>
                <Input
                  id="minStockQty"
                  type="number"
                  step="0.01"
                  value={formData.minStockQty}
                  onChange={(e) => setFormData({ ...formData, minStockQty: e.target.value })}
                  required
                  data-testid="ingredient-minstock-input"
                  className="input-focus"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="preferredSupplier">{t('ingredients.preferredSupplier') || 'Preferred Supplier'}</Label>
                <Select
                  value={formData.preferredSupplierId || ''}
                  onValueChange={(value) => setFormData({ ...formData, preferredSupplierId: value })}
                >
                  <SelectTrigger data-testid="ingredient-supplier-select">
                    <SelectValue placeholder={t('ingredients.selectSupplier') || 'Select Supplier'} />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">{t('ingredients.noSupplier') || 'No supplier'}</SelectItem>
                    {suppliers.map(supplier => (
                      <SelectItem key={supplier.id} value={supplier.id}>
                        {supplier.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="category">{t('ingredients.form.category') || 'Category'}</Label>
                <Select
                  value={formData.category}
                  onValueChange={(value) => setFormData({ ...formData, category: value })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="food">{t('receiving.category.food') || 'Food'}</SelectItem>
                    <SelectItem value="beverage">{t('receiving.category.beverage') || 'Beverage'}</SelectItem>
                    <SelectItem value="nofood">{t('receiving.category.nofood') || 'Non-Food'}</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="wastePct">{t('ingredients.form.wastePct') || 'Waste %'} ({formData.wastePct}%)</Label>
                <input
                  id="wastePct"
                  type="range"
                  min="0"
                  max="100"
                  step="1"
                  value={formData.wastePct}
                  onChange={(e) => setFormData({ ...formData, wastePct: e.target.value })}
                  className="w-full"
                />
                <p className="text-xs text-muted-foreground">
                  {t('ingredients.form.wasteHint') || 'Percentage lost to trimming/spoilage'}
                </p>
              </div>

              <div className="space-y-2">
                <Label>{t('ingredients.form.allergens') || 'Allergens'}</Label>
                <div className="grid grid-cols-3 gap-2 max-h-40 overflow-y-auto border rounded p-2">
                  {ALLERGENS.map(allergen => (
                    <label key={allergen} className="flex items-center gap-2 text-sm cursor-pointer">
                      <input
                        type="checkbox"
                        checked={formData.allergens.includes(allergen)}
                        onChange={() => toggleAllergen(allergen)}
                        className="rounded"
                      />
                      {allergen}
                    </label>
                  ))}
                </div>
              </div>

              <div className="space-y-2">
                <Label>{t('ingredients.form.shelfLife') || 'Shelf Life'}</Label>
                <div className="grid grid-cols-2 gap-2">
                  <Input
                    type="number"
                    placeholder={t('common.value') || 'Value'}
                    value={formData.shelfLife.value}
                    onChange={(e) => setFormData({ 
                      ...formData, 
                      shelfLife: { ...formData.shelfLife, value: e.target.value }
                    })}
                    className="input-focus"
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

              <Button type="submit" className="w-full btn-primary text-white" data-testid="save-ingredient-button">
                {editingId ? (t('common.update') || 'Update') : (t('common.create') || 'Create')} {t('ingredients.title') || 'Ingredient'}
              </Button>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {ingredients.map((ingredient) => (
          <Card key={ingredient.id} className="glass-morphism border-0 card-hover" data-testid="ingredient-card">
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span className="text-lg">{ingredient.name}</span>
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => handleEdit(ingredient)}
                    data-testid="edit-ingredient-button"
                  >
                    <Edit className="w-4 h-4 text-emerald-600" />
                  </Button>
                  {user?.role === 'admin' && (
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => handleDelete(ingredient.id)}
                      data-testid="delete-ingredient-button"
                    >
                      <Trash2 className="w-4 h-4 text-red-500" />
                    </Button>
                  )}
                </div>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600">{t('ingredients.unitCost') || 'Unit Cost'}:</span>
                <span className="font-semibold text-emerald-600">{format.number(ingredient.unitCost, 4)}/{ingredient.unit}</span>
              </div>
              {ingredient.wastePct > 0 && (
                <div className="flex justify-between">
                  <span className="text-gray-600">{t('ingredients.effectiveCost') || 'Effective Cost'}:</span>
                  <span className="font-semibold text-orange-600">
                    {format.number(ingredient.effectiveUnitCost, 4)}/{ingredient.unit}
                    <span className="text-xs ml-1">({ingredient.wastePct}% {t('ingredients.waste') || 'waste'})</span>
                  </span>
                </div>
              )}
              <div className="flex justify-between">
                <span className="text-gray-600">{t('ingredients.pack') || 'Pack'}:</span>
                <span className="font-medium">{ingredient.packSize} {ingredient.unit} @ {format.number(ingredient.packCost)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">{t('ingredients.minStock') || 'Min Stock'}:</span>
                <span className="font-medium">{ingredient.minStockQty} {ingredient.unit}</span>
              </div>
              {ingredient.supplier && (
                <div className="flex justify-between">
                  <span className="text-gray-600">{t('ingredients.supplier') || 'Supplier'}:</span>
                  <span className="font-medium">{ingredient.supplier}</span>
                </div>
              )}
              {ingredient.category && (
                <div className="flex justify-between">
                  <span className="text-gray-600">{t('ingredients.category') || 'Category'}:</span>
                  <span className="font-medium capitalize">{ingredient.category}</span>
                </div>
              )}
              {ingredient.shelfLife && (
                <div className="flex justify-between">
                  <span className="text-gray-600">{t('ingredients.shelfLife') || 'Shelf Life'}:</span>
                  <span className="font-medium">{ingredient.shelfLife.value} {ingredient.shelfLife.unit}</span>
                </div>
              )}
              {ingredient.allergens && ingredient.allergens.length > 0 && (
                <div className="pt-2 border-t">
                  <div className="flex items-start gap-1">
                    <AlertCircle className="h-4 w-4 text-red-600 mt-0.5" />
                    <div className="flex-1">
                      <span className="text-xs font-medium text-red-600">{t('ingredients.allergens') || 'Allergens'}:</span>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {ingredient.allergens.map(allergen => (
                          <span key={allergen} className="text-xs bg-red-100 text-red-800 px-2 py-0.5 rounded">
                            {allergen}
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
      </div>

      {ingredients.length === 0 && (
        <Card className="glass-morphism border-0">
          <CardContent className="flex flex-col items-center justify-center py-12">
            <p className="text-gray-500 mb-4">{`${t('ingredients.noData')}`}</p>
            <Button className="btn-primary text-white" onClick={() => setIsDialogOpen(true)}>
              <Plus className="w-4 h-4 mr-2" />
              Add Your First Ingredient
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

export default Ingredients;