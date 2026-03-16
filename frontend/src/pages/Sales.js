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
import { Plus, Trash2, ShoppingCart, AlertCircle, Package } from 'lucide-react';
import { toast } from 'sonner';

function Sales() {
  const { t } = useTranslation();
  const { user } = useContext(AuthContext);
  const { formatMinor } = useCurrency();
  const [sales, setSales] = useState([]);
  const [recipes, setRecipes] = useState([]);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [viewingDeductions, setViewingDeductions] = useState(null);
  const [formData, setFormData] = useState({
    date: new Date().toISOString().split('T')[0],
    lines: [],
    revenue: '',
    notes: ''
  });
  const [currentLine, setCurrentLine] = useState({
    recipeId: '',
    qty: ''
  });

  useEffect(() => {
    fetchSales();
    fetchRecipes();
  }, []);

  const fetchSales = async () => {
    try {
      const response = await axios.get(`${API}/sales`);
      setSales(response.data);
    } catch (error) {
      toast.error(t('sales.error.load') || 'Failed to load sales');
    }
  };

  const fetchRecipes = async () => {
    try {
      const response = await axios.get(`${API}/recipes`);
      setRecipes(response.data);
    } catch (error) {
      toast.error(t('recipes.error.load') || 'Failed to load recipes');
    }
  };

  // RBAC: Check if user can edit
  const canEdit = user?.roleKey === 'owner' || user?.roleKey === 'admin' || user?.roleKey === 'manager';

  const addLineToSale = () => {
    if (!currentLine.recipeId || !currentLine.qty || currentLine.qty <= 0) {
      toast.error(t('sales.error.invalidLine') || 'Please select recipe and valid quantity');
      return;
    }

    setFormData({
      ...formData,
      lines: [...formData.lines, { ...currentLine, qty: parseInt(currentLine.qty) }]
    });

    setCurrentLine({ recipeId: '', qty: '' });
  };

  const removeLine = (index) => {
    setFormData({
      ...formData,
      lines: formData.lines.filter((_, i) => i !== index)
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (formData.lines.length === 0) {
      toast.error(t('sales.error.noLines') || 'Please add at least one item');
      return;
    }

    const payload = {
      date: formData.date,
      lines: formData.lines,
      revenue: formData.revenue ? parseFloat(formData.revenue) * 100 : null, // Convert to minor units
      notes: formData.notes || null
    };

    try {
      await axios.post(`${API}/sales`, payload);
      toast.success(t('sales.success.created') || 'Sales record created successfully');
      fetchSales();
      resetForm();
      setIsDialogOpen(false);
    } catch (error) {
      toast.error(error.response?.data?.detail || t('sales.error.save') || 'Failed to save sales');
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm(t('sales.confirm.delete') || 'Are you sure you want to delete this sales record?')) return;

    try {
      await axios.delete(`${API}/sales/${id}`);
      toast.success(t('sales.success.deleted') || 'Sales record deleted');
      fetchSales();
    } catch (error) {
      toast.error(t('sales.error.delete') || 'Failed to delete sales record');
    }
  };

  const resetForm = () => {
    setFormData({
      date: new Date().toISOString().split('T')[0],
      lines: [],
      revenue: '',
      notes: ''
    });
    setCurrentLine({ recipeId: '', qty: '' });
  };

  const getRecipeName = (id) => {
    const recipe = recipes.find(r => r.id === id);
    return recipe ? recipe.name : t('common.unknown') || 'Unknown';
  };

  const calculateSaleTotal = (saleLines) => {
    let total = 0;
    saleLines.forEach(line => {
      const recipe = recipes.find(r => r.id === line.recipeId);
      if (recipe) {
        total += recipe.price * line.qty;
      }
    });
    return total;
  };

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold">{t('sales.title') || 'Sales'}</h1>
          <p className="text-sm text-muted-foreground mt-1">
            {t('sales.subtitle') || 'Record daily sales and track stock deductions'}
          </p>
        </div>

        {canEdit && (
          <Dialog open={isDialogOpen} onOpenChange={(open) => {
            setIsDialogOpen(open);
            if (!open) resetForm();
          }}>
            <DialogTrigger asChild>
              <Button data-testid="add-sales-btn">
                <Plus className="mr-2 h-4 w-4" />
                {t('sales.add') || 'Add Sale'}
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
              <DialogHeader>
                <DialogTitle>{t('sales.new') || 'New Sales Record'}</DialogTitle>
              </DialogHeader>
              <form onSubmit={handleSubmit} className="space-y-4">
                {/* Date and Revenue */}
                <div className="grid grid-cols-2 gap-4">
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
                  <div>
                    <Label htmlFor="revenue">{t('sales.revenue') || 'Total Revenue'}</Label>
                    <Input
                      id="revenue"
                      type="number"
                      step="0.01"
                      placeholder="0.00"
                      value={formData.revenue}
                      onChange={(e) => setFormData({ ...formData, revenue: e.target.value })}
                    />
                  </div>
                </div>

                {/* Add Recipe Lines */}
                <div className="border-t pt-4">
                  <h3 className="font-semibold mb-3">{t('sales.items') || 'Sale Items'}</h3>
                  <div className="grid grid-cols-12 gap-2 mb-3">
                    <div className="col-span-7">
                      <Label className="text-xs">{t('recipes.name') || 'Recipe'}</Label>
                      <Select
                        value={currentLine.recipeId}
                        onValueChange={(value) => setCurrentLine({ ...currentLine, recipeId: value })}
                      >
                        <SelectTrigger className="h-9">
                          <SelectValue placeholder={t('sales.selectRecipe') || 'Select recipe...'} />
                        </SelectTrigger>
                        <SelectContent>
                          {recipes.map(recipe => (
                            <SelectItem key={recipe.id} value={recipe.id}>
                              {recipe.name} ({formatMinor(recipe.price)})
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="col-span-3">
                      <Label className="text-xs">{t('common.qty') || 'Quantity'}</Label>
                      <Input
                        className="h-9"
                        type="number"
                        min="1"
                        placeholder="1"
                        value={currentLine.qty}
                        onChange={(e) => setCurrentLine({ ...currentLine, qty: e.target.value })}
                      />
                    </div>
                    <div className="col-span-2 flex items-end">
                      <Button type="button" size="sm" onClick={addLineToSale} className="w-full">
                        <Plus className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>

                  {/* Lines List */}
                  <div className="space-y-2">
                    {formData.lines.map((line, index) => (
                      <Card key={index} className="p-3">
                        <div className="flex justify-between items-center">
                          <div className="flex-1">
                            <span className="font-medium">{getRecipeName(line.recipeId)}</span>
                            <span className="text-sm text-muted-foreground ml-2">
                              × {line.qty} {t('recipes.portions') || 'portions'}
                            </span>
                          </div>
                          <div className="flex items-center gap-3">
                            <span className="text-sm font-semibold text-emerald-600">
                              {formatMinor(calculateSaleTotal([line]))}
                            </span>
                            <Button
                              type="button"
                              size="sm"
                              variant="ghost"
                              onClick={() => removeLine(index)}
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </div>
                        </div>
                      </Card>
                    ))}
                  </div>

                  {formData.lines.length === 0 && (
                    <div className="text-center py-6 text-muted-foreground text-sm">
                      {t('sales.noItems') || 'No items added yet'}
                    </div>
                  )}

                  {/* Total */}
                  {formData.lines.length > 0 && (
                    <div className="border-t mt-3 pt-3 flex justify-between items-center">
                      <span className="font-semibold">{t('common.total') || 'Total'}:</span>
                      <span className="text-lg font-bold text-emerald-600">
                        {formatMinor(calculateSaleTotal(formData.lines))}
                      </span>
                    </div>
                  )}
                </div>

                {/* Notes */}
                <div>
                  <Label htmlFor="notes">{t('common.notes') || 'Notes'}</Label>
                  <Textarea
                    id="notes"
                    rows={2}
                    placeholder={t('sales.notesPlaceholder') || 'Optional notes...'}
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
                    {t('common.create') || 'Create Sale'}
                  </Button>
                </div>
              </form>
            </DialogContent>
          </Dialog>
        )}
      </div>

      {/* Sales List */}
      <div className="grid gap-4">
        {sales.map((sale) => (
          <Card key={sale.id}>
            <CardHeader>
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <CardTitle className="flex items-center gap-2">
                    <ShoppingCart className="h-5 w-5" />
                    {new Date(sale.date).toLocaleDateString()}
                    {sale.revenue && (
                      <span className="text-sm font-normal text-muted-foreground ml-2">
                        ({formatMinor(sale.revenue)})
                      </span>
                    )}
                  </CardTitle>
                  <div className="text-sm text-muted-foreground mt-1">
                    {sale.lines.length} {t('sales.items') || 'items'}
                  </div>
                </div>
                {canEdit && (
                  <Button size="sm" variant="outline" onClick={() => handleDelete(sale.id)} data-testid={`delete-sale-${sale.id}`}>
                    <Trash2 className="h-4 w-4" />
                  </Button>
                )}
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {sale.lines.map((line, idx) => (
                  <div key={idx} className="flex justify-between items-center p-2 bg-muted/30 rounded">
                    <span>{getRecipeName(line.recipeId)}</span>
                    <span className="font-medium">× {line.qty}</span>
                  </div>
                ))}
              </div>

              {sale.notes && (
                <div className="mt-3 pt-3 border-t">
                  <p className="text-sm text-muted-foreground">{sale.notes}</p>
                </div>
              )}

              {/* Stock Deductions Audit */}
              {sale.stockDeductions && sale.stockDeductions.length > 0 && (
                <div className="mt-3 pt-3 border-t">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setViewingDeductions(viewingDeductions === sale.id ? null : sale.id)}
                  >
                    <Package className="h-4 w-4 mr-1" />
                    {viewingDeductions === sale.id 
                      ? (t('sales.hideDeductions') || 'Hide Stock Deductions')
                      : (t('sales.viewDeductions') || 'View Stock Deductions')}
                  </Button>

                  {viewingDeductions === sale.id && (
                    <div className="mt-3 space-y-1">
                      {sale.stockDeductions.map((deduction, idx) => (
                        <div key={idx} className="text-xs p-2 bg-blue-50 rounded flex justify-between">
                          <span>
                            {deduction.type === 'preparation' ? '📦' : '🥕'} {deduction.itemName}
                          </span>
                          <span className="font-medium">
                            -{deduction.qtyDeducted} {deduction.unit}
                            {deduction.shortage && (
                              <span className="text-red-600 ml-1">(shortage: {deduction.shortage})</span>
                            )}
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

        {sales.length === 0 && (
          <div className="text-center py-12 text-muted-foreground">
            <ShoppingCart className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p>{t('sales.noData') || 'No sales records yet'}</p>
            <p className="text-sm mt-1">{t('sales.addFirst') || 'Create your first sale'}</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default Sales;
