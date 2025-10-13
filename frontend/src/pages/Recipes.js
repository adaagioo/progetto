import React, { useState, useEffect, useContext } from 'react';
import axios from 'axios';
import { API, AuthContext } from '../App';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Plus, Trash2, Calculator, TrendingUp } from 'lucide-react';
import { Slider } from '../components/ui/slider';
import { toast } from 'sonner';

function Recipes() {
  const { user } = useContext(AuthContext);
  const [recipes, setRecipes] = useState([]);
  const [ingredients, setIngredients] = useState([]);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [isCalcDialogOpen, setIsCalcDialogOpen] = useState(false);
  const [selectedRecipe, setSelectedRecipe] = useState(null);
  const [whatIfPrice, setWhatIfPrice] = useState(0);
  const [formData, setFormData] = useState({
    name: '',
    category: '',
    portions: '1',
    targetFoodCostPct: '30',
    price: '',
    items: []
  });
  const [currentItem, setCurrentItem] = useState({
    ingredientId: '',
    qtyPerPortion: '',
    unit: 'g'
  });

  useEffect(() => {
    fetchRecipes();
    fetchIngredients();
  }, []);

  const fetchRecipes = async () => {
    try {
      const response = await axios.get(`${API}/recipes`);
      setRecipes(response.data);
    } catch (error) {
      toast.error('Failed to load recipes');
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

  const addItemToRecipe = () => {
    if (!currentItem.ingredientId || !currentItem.qtyPerPortion) {
      toast.error('Please select ingredient and quantity');
      return;
    }

    setFormData({
      ...formData,
      items: [...formData.items, currentItem]
    });

    setCurrentItem({ ingredientId: '', qtyPerPortion: '', unit: 'g' });
  };

  const removeItem = (index) => {
    setFormData({
      ...formData,
      items: formData.items.filter((_, i) => i !== index)
    });
  };

  const calculateRecipeCost = (recipe) => {
    let totalCost = 0;
    recipe.items.forEach(item => {
      const ingredient = ingredients.find(ing => ing.id === item.ingredientId);
      if (ingredient) {
        totalCost += ingredient.unitCost * item.qtyPerPortion;
      }
    });
    return totalCost;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (formData.items.length === 0) {
      toast.error('Please add at least one ingredient');
      return;
    }

    try {
      await axios.post(`${API}/recipes`, formData);
      toast.success('Recipe created successfully');
      fetchRecipes();
      resetForm();
      setIsDialogOpen(false);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to save recipe');
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Are you sure you want to delete this recipe?')) return;

    try {
      await axios.delete(`${API}/recipes/${id}`);
      toast.success('Recipe deleted');
      fetchRecipes();
    } catch (error) {
      toast.error('Failed to delete recipe');
    }
  };

  const openCalculator = (recipe) => {
    setSelectedRecipe(recipe);
    setWhatIfPrice(recipe.price);
    setIsCalcDialogOpen(true);
  };

  const resetForm = () => {
    setFormData({
      name: '',
      category: '',
      portions: '1',
      targetFoodCostPct: '30',
      price: '',
      items: []
    });
    setCurrentItem({ ingredientId: '', qtyPerPortion: '', unit: 'g' });
  };

  const getIngredientName = (id) => {
    const ing = ingredients.find(i => i.id === id);
    return ing ? ing.name : 'Unknown';
  };

  return (
    <div className="space-y-6" data-testid="recipes-page">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold gradient-text mb-2">
            Recipes
          </h1>
          <p className="text-base text-gray-600">Manage your menu items and pricing</p>
        </div>

        <Dialog open={isDialogOpen} onOpenChange={(open) => {
          setIsDialogOpen(open);
          if (!open) resetForm();
        }}>
          <DialogTrigger asChild>
            <Button className="btn-primary text-white" data-testid="add-recipe-button">
              <Plus className="w-4 h-4 mr-2" />
              Add Recipe
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto" data-testid="recipe-dialog">
            <DialogHeader>
              <DialogTitle>New Recipe</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="name">Recipe Name *</Label>
                  <Input
                    id="name"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    required
                    data-testid="recipe-name-input"
                    className="input-focus"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="category">Category *</Label>
                  <Input
                    id="category"
                    value={formData.category}
                    onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                    required
                    data-testid="recipe-category-input"
                    className="input-focus"
                  />
                </div>
              </div>

              <div className="grid grid-cols-3 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="portions">Portions *</Label>
                  <Input
                    id="portions"
                    type="number"
                    min="1"
                    value={formData.portions}
                    onChange={(e) => setFormData({ ...formData, portions: e.target.value })}
                    required
                    data-testid="recipe-portions-input"
                    className="input-focus"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="price">Price ($) *</Label>
                  <Input
                    id="price"
                    type="number"
                    step="0.01"
                    value={formData.price}
                    onChange={(e) => setFormData({ ...formData, price: e.target.value })}
                    required
                    data-testid="recipe-price-input"
                    className="input-focus"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="targetFoodCostPct">Target Cost %</Label>
                  <Input
                    id="targetFoodCostPct"
                    type="number"
                    step="0.1"
                    value={formData.targetFoodCostPct}
                    onChange={(e) => setFormData({ ...formData, targetFoodCostPct: e.target.value })}
                    data-testid="recipe-target-input"
                    className="input-focus"
                  />
                </div>
              </div>

              <div className="border-t pt-4">
                <h3 className="font-semibold mb-3">Ingredients</h3>
                
                <div className="grid grid-cols-12 gap-2 mb-3">
                  <div className="col-span-6">
                    <Select
                      value={currentItem.ingredientId}
                      onValueChange={(value) => {
                        const ing = ingredients.find(i => i.id === value);
                        setCurrentItem({ ...currentItem, ingredientId: value, unit: ing?.unit || 'g' });
                      }}
                    >
                      <SelectTrigger data-testid="recipe-ingredient-select">
                        <SelectValue placeholder="Select ingredient" />
                      </SelectTrigger>
                      <SelectContent>
                        {ingredients.map(ing => (
                          <SelectItem key={ing.id} value={ing.id}>{ing.name}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="col-span-4">
                    <Input
                      type="number"
                      step="0.01"
                      placeholder="Qty per portion"
                      value={currentItem.qtyPerPortion}
                      onChange={(e) => setCurrentItem({ ...currentItem, qtyPerPortion: e.target.value })}
                      data-testid="recipe-qty-input"
                      className="input-focus"
                    />
                  </div>
                  <div className="col-span-2">
                    <Button type="button" onClick={addItemToRecipe} className="w-full" data-testid="add-item-button">
                      <Plus className="w-4 h-4" />
                    </Button>
                  </div>
                </div>

                <div className="space-y-2 max-h-48 overflow-y-auto">
                  {formData.items.map((item, index) => (
                    <div key={index} className="flex items-center justify-between bg-emerald-50 p-2 rounded" data-testid="recipe-item">
                      <span className="text-sm">
                        {getIngredientName(item.ingredientId)} - {item.qtyPerPortion} {item.unit}
                      </span>
                      <Button
                        type="button"
                        size="sm"
                        variant="ghost"
                        onClick={() => removeItem(index)}
                        data-testid="remove-item-button"
                      >
                        <Trash2 className="w-3 h-3 text-red-500" />
                      </Button>
                    </div>
                  ))}
                </div>
              </div>

              <Button type="submit" className="w-full btn-primary text-white" data-testid="save-recipe-button">
                Create Recipe
              </Button>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {recipes.map((recipe) => {
          const actualCost = calculateRecipeCost(recipe);
          const actualCostPct = (actualCost / recipe.price * 100);
          const isOverTarget = actualCostPct > recipe.targetFoodCostPct;

          return (
            <Card key={recipe.id} className="glass-morphism border-0 card-hover" data-testid="recipe-card">
              <CardHeader>
                <CardTitle className="flex items-center justify-between">
                  <span className="text-lg">{recipe.name}</span>
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => openCalculator(recipe)}
                      data-testid="calculator-button"
                    >
                      <Calculator className="w-4 h-4 text-emerald-600" />
                    </Button>
                    {user?.role === 'admin' && (
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => handleDelete(recipe.id)}
                        data-testid="delete-recipe-button"
                      >
                        <Trash2 className="w-4 h-4 text-red-500" />
                      </Button>
                    )}
                  </div>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-gray-600">Category:</span>
                  <span className="font-medium">{recipe.category}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-600">Price:</span>
                  <span className="text-lg font-bold text-emerald-600">${recipe.price}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-600">Actual Cost:</span>
                  <span className="font-semibold">${actualCost.toFixed(2)}</span>
                </div>
                <div className="pt-2 border-t">
                  <div className="flex justify-between items-center mb-1">
                    <span className="text-sm text-gray-600">Food Cost %:</span>
                    <span className={`font-bold ${isOverTarget ? 'text-red-600' : 'text-emerald-600'}`}>
                      {actualCostPct.toFixed(1)}%
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-600">Target:</span>
                    <span className="text-sm font-medium">{recipe.targetFoodCostPct}%</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {recipes.length === 0 && (
        <Card className="glass-morphism border-0">
          <CardContent className="flex flex-col items-center justify-center py-12">
            <p className="text-gray-500 mb-4">No recipes yet</p>
            <Button className="btn-primary text-white" onClick={() => setIsDialogOpen(true)}>
              <Plus className="w-4 h-4 mr-2" />
              Add Your First Recipe
            </Button>
          </CardContent>
        </Card>
      )}

      {/* What-If Calculator Dialog */}
      <Dialog open={isCalcDialogOpen} onOpenChange={setIsCalcDialogOpen}>
        <DialogContent data-testid="calculator-dialog">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-emerald-500" />
              What-If Price Calculator
            </DialogTitle>
          </DialogHeader>
          {selectedRecipe && (
            <div className="space-y-6">
              <div>
                <h3 className="font-semibold mb-2">{selectedRecipe.name}</h3>
                <p className="text-sm text-gray-600">Current Price: ${selectedRecipe.price}</p>
              </div>

              <div className="space-y-4">
                <div>
                  <Label>Adjust Price: ${whatIfPrice}</Label>
                  <Slider
                    value={[whatIfPrice]}
                    onValueChange={(value) => setWhatIfPrice(value[0])}
                    min={0}
                    max={selectedRecipe.price * 2}
                    step={0.5}
                    className="mt-2"
                    data-testid="price-slider"
                  />
                </div>

                <div className="bg-emerald-50 p-4 rounded-lg space-y-2">
                  <div className="flex justify-between">
                    <span className="text-gray-600">Actual Cost:</span>
                    <span className="font-semibold">${calculateRecipeCost(selectedRecipe).toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">New Food Cost %:</span>
                    <span className="text-lg font-bold text-emerald-600" data-testid="new-food-cost">
                      {((calculateRecipeCost(selectedRecipe) / whatIfPrice) * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Target:</span>
                    <span className="font-medium">{selectedRecipe.targetFoodCostPct}%</span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

export default Recipes;