import React, { useState, useEffect, useContext } from 'react';
import { useCurrency } from '../contexts/CurrencyContext';
import axios from 'axios';
import { API, AuthContext } from '../App';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Textarea } from '../components/ui/textarea';
import { Plus, Trash2, AlertTriangle } from 'lucide-react';
import { toast } from 'sonner';
import { format } from 'date-fns';

function Wastage() {
  const { user } = useContext(AuthContext);
  const [wastage, setWastage] = useState([]);
  const [ingredients, setIngredients] = useState([]);
  const [recipes, setRecipes] = useState([]);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [formData, setFormData] = useState({
    date: new Date().toISOString().split('T')[0],
    type: 'ingredient',
    ingredientId: '',
    recipeId: '',
    qty: '',
    unit: 'g',
    reason: ''
  });

  useEffect(() => {
    fetchWastage();
    fetchIngredients();
    fetchRecipes();
  }, []);

  const fetchWastage = async () => {
    try {
      const response = await axios.get(`${API}/wastage`);
      setWastage(response.data);
    } catch (error) {
      toast.error('Failed to load wastage');
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

  const fetchRecipes = async () => {
    try {
      const response = await axios.get(`${API}/recipes`);
      setRecipes(response.data);
    } catch (error) {
      toast.error('Failed to load recipes');
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    try {
      await axios.post(`${API}/wastage`, formData);
      toast.success('Wastage record created');
      fetchWastage();
      resetForm();
      setIsDialogOpen(false);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to save wastage');
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Are you sure you want to delete this wastage record?')) return;

    try {
      await axios.delete(`${API}/wastage/${id}`);
      toast.success('Wastage record deleted');
      fetchWastage();
    } catch (error) {
      toast.error('Failed to delete wastage record');
    }
  };

  const resetForm = () => {
    setFormData({
      date: new Date().toISOString().split('T')[0],
      type: 'ingredient',
      ingredientId: '',
      recipeId: '',
      qty: '',
      unit: 'g',
      reason: ''
    });
  };

  const getItemName = (wastageItem) => {
    if (wastageItem.type === 'ingredient') {
      const ing = ingredients.find(i => i.id === wastageItem.ingredientId);
      return ing ? ing.name : 'Unknown';
    } else {
      const recipe = recipes.find(r => r.id === wastageItem.recipeId);
      return recipe ? recipe.name : 'Unknown';
    }
  };

  return (
    <div className="space-y-6" data-testid="wastage-page">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold gradient-text mb-2">
            Wastage
          </h1>
          <p className="text-base text-gray-600">Track and reduce food waste</p>
        </div>

        <Dialog open={isDialogOpen} onOpenChange={(open) => {
          setIsDialogOpen(open);
          if (!open) resetForm();
        }}>
          <DialogTrigger asChild>
            <Button className="btn-primary text-white" data-testid="add-wastage-button">
              <Plus className="w-4 h-4 mr-2" />
              Record Wastage
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-md max-h-[90vh] overflow-y-auto" data-testid="wastage-dialog">
            <DialogHeader>
              <DialogTitle>New Wastage Record</DialogTitle>
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
                  data-testid="wastage-date-input"
                  className="input-focus"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="type">Wastage Type *</Label>
                <Select
                  value={formData.type}
                  onValueChange={(value) => setFormData({ ...formData, type: value })}
                >
                  <SelectTrigger data-testid="wastage-type-select">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="ingredient">Ingredient</SelectItem>
                    <SelectItem value="recipe">Recipe / Dish</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {formData.type === 'ingredient' ? (
                <div className="space-y-2">
                  <Label htmlFor="ingredient">Ingredient *</Label>
                  <Select
                    value={formData.ingredientId}
                    onValueChange={(value) => {
                      const ing = ingredients.find(i => i.id === value);
                      setFormData({ ...formData, ingredientId: value, unit: ing?.unit || 'g' });
                    }}
                  >
                    <SelectTrigger data-testid="wastage-ingredient-select">
                      <SelectValue placeholder="Select ingredient" />
                    </SelectTrigger>
                    <SelectContent>
                      {ingredients.map(ing => (
                        <SelectItem key={ing.id} value={ing.id}>{ing.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              ) : (
                <div className="space-y-2">
                  <Label htmlFor="recipe">Recipe *</Label>
                  <Select
                    value={formData.recipeId}
                    onValueChange={(value) => setFormData({ ...formData, recipeId: value })}
                  >
                    <SelectTrigger data-testid="wastage-recipe-select">
                      <SelectValue placeholder="Select recipe" />
                    </SelectTrigger>
                    <SelectContent>
                      {recipes.map(recipe => (
                        <SelectItem key={recipe.id} value={recipe.id}>{recipe.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              )}

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
                    data-testid="wastage-qty-input"
                    className="input-focus"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="unit">Unit</Label>
                  <Input
                    id="unit"
                    value={formData.unit}
                    onChange={(e) => setFormData({ ...formData, unit: e.target.value })}
                    data-testid="wastage-unit-input"
                    className="input-focus"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="reason">Reason</Label>
                <Textarea
                  id="reason"
                  value={formData.reason}
                  onChange={(e) => setFormData({ ...formData, reason: e.target.value })}
                  placeholder="e.g., Expired, Spoiled, Overproduction"
                  data-testid="wastage-reason-input"
                  className="input-focus"
                  rows={3}
                />
              </div>

              <Button type="submit" className="w-full btn-primary text-white" data-testid="save-wastage-button">
                Record Wastage
              </Button>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {wastage.map((waste) => (
          <Card key={waste.id} className="glass-morphism border-0 card-hover" data-testid="wastage-card">
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <AlertTriangle className="w-5 h-5 text-orange-500" />
                  <span className="text-lg">{getItemName(waste)}</span>
                </div>
                {user?.role === 'admin' && (
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => handleDelete(waste.id)}
                    data-testid="delete-wastage-button"
                  >
                    <Trash2 className="w-4 h-4 text-red-500" />
                  </Button>
                )}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600">Date:</span>
                <span className="font-medium">{format(new Date(waste.date), 'MMM dd, yyyy')}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Type:</span>
                <span className="font-medium capitalize">{waste.type}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Quantity:</span>
                <span className="font-semibold text-orange-600">{waste.qty} {waste.unit}</span>
              </div>
              {waste.reason && (
                <div className="pt-2 border-t">
                  <p className="text-xs text-gray-600">
                    <span className="font-semibold">Reason: </span>
                    {waste.reason}
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>

      {wastage.length === 0 && (
        <Card className="glass-morphism border-0">
          <CardContent className="flex flex-col items-center justify-center py-12">
            <p className="text-gray-500 mb-4">No wastage records yet</p>
            <Button className="btn-primary text-white" onClick={() => setIsDialogOpen(true)}>
              <Plus className="w-4 h-4 mr-2" />
              Record First Wastage
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

export default Wastage;