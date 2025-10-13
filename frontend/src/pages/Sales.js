import React, { useState, useEffect, useContext } from 'react';
import axios from 'axios';
import { API, AuthContext } from '../App';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Plus, Trash2, ShoppingCart } from 'lucide-react';
import { toast } from 'sonner';
import { format } from 'date-fns';

function Sales() {
  const { user } = useContext(AuthContext);
  const [sales, setSales] = useState([]);
  const [recipes, setRecipes] = useState([]);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [formData, setFormData] = useState({
    date: new Date().toISOString().split('T')[0],
    lines: []
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
      toast.error('Failed to load sales');
    }
  };

  const fetchRecipes = async () => {
    try {
      const response = await axios.get(`${API}/recipes`);
      setRecipes(response.data);
    } catch (error) {
      toast.error('Failed to load recipes');
    }
  };

  const addLineToSale = () => {
    if (!currentLine.recipeId || !currentLine.qty) {
      toast.error('Please select recipe and quantity');
      return;
    }

    setFormData({
      ...formData,
      lines: [...formData.lines, currentLine]
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
      toast.error('Please add at least one item');
      return;
    }

    try {
      await axios.post(`${API}/sales`, formData);
      toast.success('Sales record created');
      fetchSales();
      resetForm();
      setIsDialogOpen(false);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to save sales');
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Are you sure you want to delete this sales record?')) return;

    try {
      await axios.delete(`${API}/sales/${id}`);
      toast.success('Sales record deleted');
      fetchSales();
    } catch (error) {
      toast.error('Failed to delete sales record');
    }
  };

  const resetForm = () => {
    setFormData({
      date: new Date().toISOString().split('T')[0],
      lines: []
    });
    setCurrentLine({ recipeId: '', qty: '' });
  };

  const getRecipeName = (id) => {
    const recipe = recipes.find(r => r.id === id);
    return recipe ? recipe.name : 'Unknown';
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
    <div className="space-y-6" data-testid="sales-page">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold gradient-text mb-2">
            Sales
          </h1>
          <p className="text-base text-gray-600">Record daily sales transactions</p>
        </div>

        <Dialog open={isDialogOpen} onOpenChange={(open) => {
          setIsDialogOpen(open);
          if (!open) resetForm();
        }}>
          <DialogTrigger asChild>
            <Button className="btn-primary text-white" data-testid="add-sales-button">
              <Plus className="w-4 h-4 mr-2" />
              Add Sale
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto" data-testid="sales-dialog">
            <DialogHeader>
              <DialogTitle>New Sales Record</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="date">Date *</Label>
                <Input
                  id="date"
                  type="date"
                  value={formData.date}
                  onChange={(e) => setFormData({ ...formData, date: e.target.value })}
                  required
                  data-testid="sales-date-input"
                  className="input-focus"
                />
              </div>

              <div className="border-t pt-4">
                <h3 className="font-semibold mb-3">Items Sold</h3>
                
                <div className="grid grid-cols-12 gap-2 mb-3">
                  <div className="col-span-8">
                    <Select
                      value={currentLine.recipeId}
                      onValueChange={(value) => setCurrentLine({ ...currentLine, recipeId: value })}
                    >
                      <SelectTrigger data-testid="sales-recipe-select">
                        <SelectValue placeholder="Select recipe" />
                      </SelectTrigger>
                      <SelectContent>
                        {recipes.map(recipe => (
                          <SelectItem key={recipe.id} value={recipe.id}>
                            {recipe.name} - ${recipe.price}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="col-span-2">
                    <Input
                      type="number"
                      min="1"
                      placeholder="Qty"
                      value={currentLine.qty}
                      onChange={(e) => setCurrentLine({ ...currentLine, qty: e.target.value })}
                      data-testid="sales-qty-input"
                      className="input-focus"
                    />
                  </div>
                  <div className="col-span-2">
                    <Button type="button" onClick={addLineToSale} className="w-full" data-testid="add-sales-line-button">
                      <Plus className="w-4 h-4" />
                    </Button>
                  </div>
                </div>

                <div className="space-y-2 max-h-64 overflow-y-auto">
                  {formData.lines.map((line, index) => {
                    const recipe = recipes.find(r => r.id === line.recipeId);
                    const lineTotal = recipe ? recipe.price * line.qty : 0;
                    return (
                      <div key={index} className="flex items-center justify-between bg-emerald-50 p-3 rounded" data-testid="sales-line">
                        <div>
                          <p className="font-medium">{getRecipeName(line.recipeId)}</p>
                          <p className="text-sm text-gray-600">Qty: {line.qty} × ${recipe?.price} = ${lineTotal.toFixed(2)}</p>
                        </div>
                        <Button
                          type="button"
                          size="sm"
                          variant="ghost"
                          onClick={() => removeLine(index)}
                          data-testid="remove-sales-line-button"
                        >
                          <Trash2 className="w-4 h-4 text-red-500" />
                        </Button>
                      </div>
                    );
                  })}
                </div>

                {formData.lines.length > 0 && (
                  <div className="mt-4 pt-4 border-t">
                    <div className="flex justify-between items-center">
                      <span className="text-lg font-semibold">Total:</span>
                      <span className="text-2xl font-bold text-emerald-600" data-testid="sales-total">
                        ${calculateSaleTotal(formData.lines).toFixed(2)}
                      </span>
                    </div>
                  </div>
                )}
              </div>

              <Button type="submit" className="w-full btn-primary text-white" data-testid="save-sales-button">
                Record Sale
              </Button>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {sales.map((sale) => (
          <Card key={sale.id} className="glass-morphism border-0 card-hover" data-testid="sales-card">
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <ShoppingCart className="w-5 h-5 text-emerald-500" />
                  <span className="text-lg">{format(new Date(sale.date), 'MMM dd, yyyy')}</span>
                </div>
                {user?.role === 'admin' && (
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => handleDelete(sale.id)}
                    data-testid="delete-sales-button"
                  >
                    <Trash2 className="w-4 h-4 text-red-500" />
                  </Button>
                )}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="space-y-2">
                {sale.lines.map((line, idx) => (
                  <div key={idx} className="flex justify-between text-sm">
                    <span className="text-gray-600">{getRecipeName(line.recipeId)}</span>
                    <span className="font-medium">×{line.qty}</span>
                  </div>
                ))}
              </div>
              <div className="pt-3 border-t flex justify-between items-center">
                <span className="font-semibold">Total:</span>
                <span className="text-xl font-bold text-emerald-600">
                  ${calculateSaleTotal(sale.lines).toFixed(2)}
                </span>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {sales.length === 0 && (
        <Card className="glass-morphism border-0">
          <CardContent className="flex flex-col items-center justify-center py-12">
            <p className="text-gray-500 mb-4">No sales records yet</p>
            <Button className="btn-primary text-white" onClick={() => setIsDialogOpen(true)}>
              <Plus className="w-4 h-4 mr-2" />
              Add Your First Sale
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

export default Sales;