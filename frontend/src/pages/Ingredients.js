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
import { Plus, Trash2, Edit } from 'lucide-react';
import { toast } from 'sonner';

function Ingredients() {
  const { user } = useContext(AuthContext);
  const { format } = useCurrency();
  const [ingredients, setIngredients] = useState([]);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [formData, setFormData] = useState({
    name: '',
    unit: 'g',
    packSize: '',
    packCost: '',
    supplier: '',
    allergen: '',
    minStockQty: ''
  });

  useEffect(() => {
    fetchIngredients();
  }, []);

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

    try {
      if (editingId) {
        await axios.put(`${API}/ingredients/${editingId}`, formData);
        toast.success('Ingredient updated successfully');
      } else {
        await axios.post(`${API}/ingredients`, formData);
        toast.success('Ingredient created successfully');
      }
      fetchIngredients();
      resetForm();
      setIsDialogOpen(false);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to save ingredient');
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
      allergen: ingredient.allergen || '',
      minStockQty: ingredient.minStockQty.toString()
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
      minStockQty: ''
    });
    setEditingId(null);
  };

  return (
    <div className="space-y-6" data-testid="ingredients-page">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold gradient-text mb-2">
            Ingredients
          </h1>
          <p className="text-base text-gray-600">Manage your ingredient inventory</p>
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
                <Label htmlFor="supplier">Supplier</Label>
                <Input
                  id="supplier"
                  value={formData.supplier}
                  onChange={(e) => setFormData({ ...formData, supplier: e.target.value })}
                  data-testid="ingredient-supplier-input"
                  className="input-focus"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="allergen">Allergen</Label>
                <Input
                  id="allergen"
                  value={formData.allergen}
                  onChange={(e) => setFormData({ ...formData, allergen: e.target.value })}
                  data-testid="ingredient-allergen-input"
                  className="input-focus"
                />
              </div>

              <Button type="submit" className="w-full btn-primary text-white" data-testid="save-ingredient-button">
                {editingId ? 'Update' : 'Create'} Ingredient
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
                <span className="text-gray-600">Unit Cost:</span>
                <span className="font-semibold text-emerald-600">{format.number(ingredient.unitCost, 4)}/{ingredient.unit}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Pack:</span>
                <span className="font-medium">{ingredient.packSize} {ingredient.unit} @ {format.number(ingredient.packCost)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Min Stock:</span>
                <span className="font-medium">{ingredient.minStockQty} {ingredient.unit}</span>
              </div>
              {ingredient.supplier && (
                <div className="flex justify-between">
                  <span className="text-gray-600">Supplier:</span>
                  <span className="font-medium">{ingredient.supplier}</span>
                </div>
              )}
              {ingredient.allergen && (
                <div className="pt-2 border-t">
                  <span className="text-xs text-red-600 font-medium">⚠ {ingredient.allergen}</span>
                </div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>

      {ingredients.length === 0 && (
        <Card className="glass-morphism border-0">
          <CardContent className="flex flex-col items-center justify-center py-12">
            <p className="text-gray-500 mb-4">No ingredients yet</p>
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