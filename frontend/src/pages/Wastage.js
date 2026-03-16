import React, { useState, useEffect, useContext } from 'react';
import { useCurrency } from '../contexts/CurrencyContext';
import { useTranslation } from 'react-i18next';
import axios from 'axios';
import { API, AuthContext } from '../App';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Plus, Trash2, AlertTriangle, Package } from 'lucide-react';
import { toast } from 'sonner';

const WASTAGE_REASONS = [
  'Spoilage',
  'Damage',
  'Expiry',
  'Preparation Error',
  'Customer Return',
  'Quality Issue',
  'Over-production',
  'Other'
];

function Wastage() {
  const { t } = useTranslation();
  const { user } = useContext(AuthContext);
  const { formatMinor } = useCurrency();
  const [wastage, setWastage] = useState([]);
  const [ingredients, setIngredients] = useState([]);
  const [preparations, setPreparations] = useState([]);
  const [recipes, setRecipes] = useState([]);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [viewingDeductions, setViewingDeductions] = useState(null);
  const [formData, setFormData] = useState({
    date: new Date().toISOString().split('T')[0],
    type: 'ingredient',
    itemId: '',
    qty: '',
    unit: 'kg',
    reason: '',
    notes: ''
  });

  useEffect(() => {
    fetchWastage();
    fetchIngredients();
    fetchPreparations();
    fetchRecipes();
  }, []);

  const fetchWastage = async () => {
    try {
      const response = await axios.get(`${API}/wastage`);
      setWastage(response.data);
    } catch (error) {
      toast.error(t('wastage.error.load') || 'Failed to load wastage');
    }
  };

  const fetchIngredients = async () => {
    try {
      const response = await axios.get(`${API}/ingredients`);
      setIngredients(response.data);
    } catch (error) {
      console.error('Failed to load ingredients:', error);
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

  const fetchRecipes = async () => {
    try {
      const response = await axios.get(`${API}/recipes`);
      setRecipes(response.data);
    } catch (error) {
      console.error('Failed to load recipes:', error);
    }
  };

  // RBAC: Check if user can edit
  const canEdit = user?.roleKey === 'owner' || user?.roleKey === 'admin' || user?.roleKey === 'manager';

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!formData.itemId || !formData.qty || !formData.reason) {
      toast.error(t('wastage.error.required') || 'Please fill all required fields');
      return;
    }

    const payload = {
      date: formData.date,
      type: formData.type,
      itemId: formData.itemId,
      qty: parseFloat(formData.qty),
      unit: formData.unit,
      reason: formData.reason,
      notes: formData.notes || null
    };

    try {
      await axios.post(`${API}/wastage`, payload);
      toast.success(t('wastage.success.created') || 'Wastage record created successfully');
      fetchWastage();
      resetForm();
      setIsDialogOpen(false);
    } catch (error) {
      toast.error(error.response?.data?.detail || t('wastage.error.save') || 'Failed to save wastage');
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm(t('wastage.confirm.delete') || 'Are you sure you want to delete this wastage record?')) return;

    try {
      await axios.delete(`${API}/wastage/${id}`);
      toast.success(t('wastage.success.deleted') || 'Wastage record deleted');
      fetchWastage();
    } catch (error) {
      toast.error(t('wastage.error.delete') || 'Failed to delete wastage record');
    }
  };

  const resetForm = () => {
    setFormData({
      date: new Date().toISOString().split('T')[0],
      type: 'ingredient',
      itemId: '',
      qty: '',
      unit: 'kg',
      reason: '',
      notes: ''
    });
  };

  const handleTypeChange = (type) => {
    setFormData({
      ...formData,
      type,
      itemId: '',
      unit: type === 'recipe' ? 'portions' : (type === 'preparation' ? 'portions' : 'kg')
    });
  };

  const handleItemChange = (itemId) => {
    setFormData({ ...formData, itemId });
    
    // Auto-set unit based on selected item
    if (formData.type === 'ingredient') {
      const ingredient = ingredients.find(i => i.id === itemId);
      if (ingredient) {
        setFormData(prev => ({ ...prev, unit: ingredient.unit || 'kg', itemId }));
      }
    } else if (formData.type === 'preparation') {
      const prep = preparations.find(p => p.id === itemId);
      if (prep) {
        setFormData(prev => ({ ...prev, unit: prep.unit || 'portions', itemId }));
      }
    }
  };

  const getItemsList = () => {
    if (formData.type === 'ingredient') return ingredients;
    if (formData.type === 'preparation') return preparations;
    if (formData.type === 'recipe') return recipes;
    return [];
  };

  const getWastageTypeIcon = (type) => {
    if (type === 'ingredient') return '🥕';
    if (type === 'preparation') return '📦';
    if (type === 'recipe') return '🍽️';
    return '❓';
  };

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold">{t('wastage.title') || 'Wastage'}</h1>
          <p className="text-sm text-muted-foreground mt-1">
            {t('wastage.subtitle') || 'Record wastage and track losses'}
          </p>
        </div>

        {canEdit && (
          <Dialog open={isDialogOpen} onOpenChange={(open) => {
            setIsDialogOpen(open);
            if (!open) resetForm();
          }}>
            <DialogTrigger asChild>
              <Button data-testid="add-wastage-btn">
                <Plus className="mr-2 h-4 w-4" />
                {t('wastage.add') || 'Add Wastage'}
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
              <DialogHeader>
                <DialogTitle>{t('wastage.new') || 'New Wastage Record'}</DialogTitle>
              </DialogHeader>
              <form onSubmit={handleSubmit} className="space-y-4">
                {/* Date */}
                <div>
                  <Label htmlFor="date">{t('common.date') || 'Date'} *</Label>
                  <Input
                    id="date"
                    type="date"
                    value={formData.date}
                    onChange={(e) => setFormData({ ...formData, date: e.target.value })}
                    required
                  />
                </div>

                {/* Type Selector */}
                <div>
                  <Label>{t('common.type') || 'Type'} *</Label>
                  <Select value={formData.type} onValueChange={handleTypeChange}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="ingredient">
                        🥕 {t('wastage.type.ingredient') || 'Ingredient'}
                      </SelectItem>
                      <SelectItem value="preparation">
                        📦 {t('wastage.type.preparation') || 'Preparation'}
                      </SelectItem>
                      <SelectItem value="recipe">
                        🍽️ {t('wastage.type.recipe') || 'Recipe (Full Dish)'}
                      </SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {/* Item Selector */}
                <div>
                  <Label>{t('wastage.item') || 'Item'} *</Label>
                  <Select value={formData.itemId} onValueChange={handleItemChange}>
                    <SelectTrigger>
                      <SelectValue placeholder={t('wastage.selectItem') || 'Select item...'} />
                    </SelectTrigger>
                    <SelectContent>
                      {getItemsList().map(item => (
                        <SelectItem key={item.id} value={item.id}>
                          {item.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {/* Quantity and Unit */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="qty">{t('common.qty') || 'Quantity'} *</Label>
                    <Input
                      id="qty"
                      type="number"
                      step="0.01"
                      min="0"
                      placeholder="0.00"
                      value={formData.qty}
                      onChange={(e) => setFormData({ ...formData, qty: e.target.value })}
                      required
                    />
                  </div>
                  <div>
                    <Label htmlFor="unit">{t('common.unit') || 'Unit'}</Label>
                    <Input
                      id="unit"
                      value={formData.unit}
                      onChange={(e) => setFormData({ ...formData, unit: e.target.value })}
                      required
                    />
                  </div>
                </div>

                {/* Reason */}
                <div>
                  <Label>{t('wastage.reason') || 'Reason'} *</Label>
                  <Select value={formData.reason} onValueChange={(value) => setFormData({ ...formData, reason: value })}>
                    <SelectTrigger>
                      <SelectValue placeholder={t('wastage.selectReason') || 'Select reason...'} />
                    </SelectTrigger>
                    <SelectContent>
                      {WASTAGE_REASONS.map(reason => (
                        <SelectItem key={reason} value={reason}>
                          {t(`wastage.reasons.${reason.toLowerCase().replace(' ', '_')}`) || reason}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {/* Notes */}
                <div>
                  <Label htmlFor="notes">{t('common.notes') || 'Notes'}</Label>
                  <Textarea
                    id="notes"
                    rows={3}
                    placeholder={t('wastage.notesPlaceholder') || 'Additional details...'}
                    value={formData.notes}
                    onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                  />
                </div>

                {/* Footer */}
                <div className="flex justify-end gap-2 pt-4 border-t">
                  <Button type="button" variant="outline" onClick={() => setIsDialogOpen(false)}>
                    {t('common.cancel') || 'Cancel'}
                  </Button>
                  <Button type="submit">
                    {t('common.create') || 'Create Record'}
                  </Button>
                </div>
              </form>
            </DialogContent>
          </Dialog>
        )}
      </div>

      {/* Wastage List */}
      <div className="grid gap-4">
        {wastage.map((record) => (
          <Card key={record.id}>
            <CardHeader>
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <CardTitle className="flex items-center gap-2">
                    <AlertTriangle className="h-5 w-5 text-orange-600" />
                    {record.itemName || 'Unknown Item'}
                    <span className="text-sm font-normal text-muted-foreground ml-2">
                      {getWastageTypeIcon(record.type)} {record.type}
                    </span>
                  </CardTitle>
                  <div className="text-sm text-muted-foreground mt-1">
                    {new Date(record.date).toLocaleDateString()} • {record.reason}
                  </div>
                </div>
                <div className="text-right">
                  <div className="font-semibold text-orange-600">
                    {record.qty} {record.unit}
                  </div>
                  {record.costImpact && (
                    <div className="text-sm text-muted-foreground">
                      {formatMinor(record.costImpact)}
                    </div>
                  )}
                  {canEdit && (
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => handleDelete(record.id)}
                      className="mt-2"
                      data-testid={`delete-wastage-${record.id}`}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  )}
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {record.notes && (
                <div className="mb-3">
                  <p className="text-sm text-muted-foreground">{record.notes}</p>
                </div>
              )}

              {/* Stock Deductions Audit */}
              {record.stockDeductions && record.stockDeductions.length > 0 && (
                <div className="mt-3 pt-3 border-t">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setViewingDeductions(viewingDeductions === record.id ? null : record.id)}
                  >
                    <Package className="h-4 w-4 mr-1" />
                    {viewingDeductions === record.id 
                      ? (t('wastage.hideDeductions') || 'Hide Stock Deductions')
                      : (t('wastage.viewDeductions') || 'View Stock Deductions')}
                  </Button>

                  {viewingDeductions === record.id && (
                    <div className="mt-3 space-y-1">
                      {record.stockDeductions.map((deduction, idx) => (
                        <div key={idx} className="text-xs p-2 bg-orange-50 rounded flex justify-between">
                          <span>
                            {deduction.type === 'preparation' ? '📦' : '🥕'} {deduction.itemName}
                          </span>
                          <span className="font-medium">
                            -{deduction.qtyDeducted} {deduction.unit}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        ))}

        {wastage.length === 0 && (
          <div className="text-center py-12 text-muted-foreground">
            <AlertTriangle className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p>{t('wastage.noData') || 'No wastage records yet'}</p>
            <p className="text-sm mt-1">{t('wastage.addFirst') || 'Create your first wastage record'}</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default Wastage;
