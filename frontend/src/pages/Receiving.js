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
import { Popover, PopoverContent, PopoverTrigger } from '../components/ui/popover';
import { Plus, Trash2, Edit, Upload, Download, FileText, X, History, TrendingUp } from 'lucide-react';
import { toast } from 'sonner';
import OCRUploadButton from '../components/OCRUploadButton';

function Receiving() {
  const { t } = useTranslation();
  const { user } = useContext(AuthContext);
  const { formatMinor } = useCurrency();
  const [receivings, setReceivings] = useState([]);
  const [suppliers, setSuppliers] = useState([]);
  const [ingredients, setIngredients] = useState([]);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [uploadingFor, setUploadingFor] = useState(null);
  const [showMappingDialog, setShowMappingDialog] = useState(false);
  const [parsedRows, setParsedRows] = useState([]);
  const [priceHistory, setPriceHistory] = useState({});  // { ingredientId: { loading, data } }
  const [ingredientTargetMemory, setIngredientTargetMemory] = useState({});  // { ingredientId: 'food'|'beverage'|'nofood' }
  
  const [formData, setFormData] = useState({
    supplierId: '',
    category: 'food',
    arrivedAt: new Date().toISOString().split('T')[0],
    notes: '',
    lines: [{ 
      ingredientId: '', 
      description: '', 
      qty: '', 
      unit: 'kg', 
      unitPrice: '', 
      packFormat: '', 
      expiryDate: '',
      targetInventory: 'food'  // Target inventory location: food, beverage, nofood
    }]
  });

  useEffect(() => {
    fetchReceivings();
    fetchSuppliers();
    fetchIngredients();
    
    // Load ingredient target memory from localStorage
    try {
      const savedMemory = localStorage.getItem('ingredientTargetMemory');
      if (savedMemory) {
        setIngredientTargetMemory(JSON.parse(savedMemory));
      }
    } catch (e) {
      console.error('Failed to load target memory:', e);
    }
  }, []);

  const fetchReceivings = async () => {
    try {
      const response = await axios.get(`${API}/receiving`);
      setReceivings(response.data);
    } catch (error) {
      toast.error(t('receiving.error.load') || 'Failed to load receiving records');
    }
  };

  const fetchSuppliers = async () => {
    try {
      const response = await axios.get(`${API}/suppliers`);
      setSuppliers(response.data);
    } catch (error) {
      toast.error(t('suppliers.error.load') || 'Failed to load suppliers');
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

  const fetchPriceHistory = async (ingredientId) => {
    if (!ingredientId) return;
    
    // Set loading state
    setPriceHistory(prev => ({
      ...prev,
      [ingredientId]: { loading: true, data: null }
    }));
    
    try {
      const response = await axios.get(`${API}/ingredients/${ingredientId}/price-history?limit=5`);
      setPriceHistory(prev => ({
        ...prev,
        [ingredientId]: { loading: false, data: response.data }
      }));
    } catch (error) {
      console.error('Failed to load price history:', error);
      setPriceHistory(prev => ({
        ...prev,
        [ingredientId]: { loading: false, data: null, error: true }
      }));
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    // Validate lines
    const validLines = formData.lines.filter(line => 
      line.description && line.qty && line.unitPrice
    );

    if (validLines.length === 0) {
      toast.error(t('receiving.error.noLines') || 'Please add at least one line item');
      return;
    }

    // Convert unitPrice to minor units (cents)
    const payload = {
      supplierId: formData.supplierId,
      category: formData.category,
      arrivedAt: formData.arrivedAt,
      notes: formData.notes || null,
      lines: validLines.map(line => ({
        ingredientId: line.ingredientId || null,
        description: line.description,
        qty: parseFloat(line.qty),
        unit: line.unit,
        unitPrice: Math.round(parseFloat(line.unitPrice) * 100), // Convert to cents
        packFormat: line.packFormat || null,
        expiryDate: line.expiryDate || null
      }))
    };

    try {
      if (editingId) {
        await axios.put(`${API}/receiving/${editingId}`, payload);
        toast.success(t('receiving.success.updated') || 'Receiving updated successfully');
      } else {
        await axios.post(`${API}/receiving`, payload);
        toast.success(t('receiving.success.created') || 'Receiving created successfully');
      }
      fetchReceivings();
      resetForm();
      setIsDialogOpen(false);
    } catch (error) {
      toast.error(error.response?.data?.detail || t('receiving.error.save') || 'Failed to save receiving');
    }
  };

  const handleEdit = (receiving) => {
    setEditingId(receiving.id);
    setFormData({
      supplierId: receiving.supplierId,
      category: receiving.category,
      arrivedAt: receiving.arrivedAt,
      notes: receiving.notes || '',
      lines: receiving.lines.map(line => ({
        ingredientId: line.ingredientId || '',
        description: line.description,
        qty: line.qty.toString(),
        unit: line.unit,
        unitPrice: (line.unitPrice / 100).toFixed(2), // Convert from cents to dollars
        packFormat: line.packFormat || '',
        expiryDate: line.expiryDate || '',
        targetInventory: line.targetInventory || 'food'
      }))
    });
    setIsDialogOpen(true);
  };

  const handleDelete = async (id) => {
    if (!window.confirm(t('receiving.confirm.delete') || 'Are you sure you want to delete this receiving?')) return;

    try {
      await axios.delete(`${API}/receiving/${id}`);
      toast.success(t('receiving.success.deleted') || 'Receiving deleted');
      fetchReceivings();
    } catch (error) {
      toast.error(t('receiving.error.delete') || 'Failed to delete receiving');
    }
  };

  const resetForm = () => {
    setFormData({
      supplierId: '',
      category: 'food',
      arrivedAt: new Date().toISOString().split('T')[0],
      notes: '',
      lines: [{ ingredientId: '', description: '', qty: '', unit: 'kg', unitPrice: '', packFormat: '', expiryDate: '', targetInventory: 'food' }]
    });
    setEditingId(null);
    setUploadingFor(null);
    setShowMappingDialog(false);
    setParsedRows([]);
  };

  const handleOCRParsed = (ocrData) => {
    // Prefill form with OCR data
    const { parsedData, items } = ocrData;
    
    // Set supplier if detected
    if (parsedData.supplier_name) {
      const matchedSupplier = suppliers.find(s => 
        s.name.toLowerCase().includes(parsedData.supplier_name.toLowerCase())
      );
      if (matchedSupplier) {
        setFormData(prev => ({ ...prev, supplierId: matchedSupplier.id }));
      }
    }
    
    // Set date if extracted
    if (parsedData.date) {
      setFormData(prev => ({ ...prev, arrivedAt: parsedData.date }));
    }
    
    // Set line items
    if (items && items.length > 0) {
      const lines = items.map(item => ({
        ingredientId: item.ingredientId || '',
        description: item.description || '',
        qty: item.qty?.toString() || '',
        unit: item.unit || 'kg',
        unitPrice: item.price?.toString() || '',
        packFormat: '',
        expiryDate: '',
        targetInventory: 'food'
      }));
      setFormData(prev => ({ ...prev, lines }));
      
      toast.success(
        `${items.length} ${t('ocr.itemsLoaded') || 'items loaded from invoice'}`
      );
    }
  };

  const addLine = () => {
    setFormData({
      ...formData,
      lines: [...formData.lines, { ingredientId: '', description: '', qty: '', unit: 'kg', unitPrice: '', packFormat: '', expiryDate: '', targetInventory: 'food' }]
    });
  };

  const removeLine = (index) => {
    const newLines = formData.lines.filter((_, i) => i !== index);
    setFormData({ ...formData, lines: newLines });
  };

  const updateLine = (index, field, value) => {
    const newLines = [...formData.lines];
    newLines[index][field] = value;
    
    // Auto-fill supplier and price when ingredient is selected
    if (field === 'ingredientId' && value) {
      const selectedIngredient = ingredients.find(ing => ing.id === value);
      if (selectedIngredient) {
        // Auto-fill description if empty
        if (!newLines[index].description) {
          newLines[index].description = selectedIngredient.name;
        }
        // Auto-fill unit if empty
        if (!newLines[index].unit || newLines[index].unit === 'kg') {
          newLines[index].unit = selectedIngredient.unit;
        }
        // Auto-fill unit price from packCost (convert from minor units)
        if (!newLines[index].unitPrice) {
          newLines[index].unitPrice = (selectedIngredient.packCost / 100).toFixed(2);
        }
        // Auto-fill packFormat from packSize
        if (!newLines[index].packFormat && selectedIngredient.packSize) {
          newLines[index].packFormat = `${selectedIngredient.packSize} ${selectedIngredient.unit}`;
        }
        
        // Auto-fill target inventory from memory or ingredient category
        if (ingredientTargetMemory[value]) {
          newLines[index].targetInventory = ingredientTargetMemory[value];
        } else if (selectedIngredient.category) {
          newLines[index].targetInventory = selectedIngredient.category;
        }
        
        // Auto-fill supplier if ingredient has preferred supplier
        if (selectedIngredient.preferredSupplierId && !formData.supplierId) {
          setFormData(prev => ({ 
            ...prev, 
            supplierId: selectedIngredient.preferredSupplierId,
            lines: newLines
          }));
          // Show toast to inform user
          toast.success(t('receiving.supplierAutofilled') || 'Supplier auto-filled from ingredient');
          return; // Exit early since we're updating the entire form
        }
      }
    }
    
    // Save target inventory memory when manually changed
    if (field === 'targetInventory' && newLines[index].ingredientId) {
      const ingredientId = newLines[index].ingredientId;
      setIngredientTargetMemory(prev => ({
        ...prev,
        [ingredientId]: value
      }));
      // Persist to localStorage for cross-session memory
      try {
        const savedMemory = JSON.parse(localStorage.getItem('ingredientTargetMemory') || '{}');
        savedMemory[ingredientId] = value;
        localStorage.setItem('ingredientTargetMemory', JSON.stringify(savedMemory));
      } catch (e) {
        console.error('Failed to save target memory:', e);
      }
    }
    
    setFormData({ ...formData, lines: newLines });
  };

  const handleFileUpload = async (receivingId, event) => {
    const file = event.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    try {
      setUploadingFor(receivingId);
      await axios.post(`${API}/receiving/${receivingId}/files`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      toast.success(t('receiving.success.fileUploaded') || 'File uploaded successfully');
      fetchReceivings();
    } catch (error) {
      toast.error(error.response?.data?.detail || t('receiving.error.fileUpload') || 'Failed to upload file');
    } finally {
      setUploadingFor(null);
      event.target.value = '';
    }
  };

  const handleFileDelete = async (receivingId, fileId, fileName) => {
    if (!window.confirm(t('receiving.confirm.deleteFile', { fileName }) || `Delete file ${fileName}?`)) return;

    try {
      await axios.delete(`${API}/receiving/${receivingId}/files/${fileId}`);
      toast.success(t('receiving.success.fileDeleted') || 'File deleted');
      fetchReceivings();
    } catch (error) {
      toast.error(t('receiving.error.fileDelete') || 'Failed to delete file');
    }
  };

  const handleFileDownload = async (fileId, fileName) => {
    try {
      const response = await axios.get(`${API}/files/${fileId}`, {
        responseType: 'blob'
      });
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', fileName);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      toast.error(t('receiving.error.fileDownload') || 'Failed to download file');
    }
  };

  // Stub: Parse uploaded file (future: implement OCR/parsing logic)
  const parseUploadedFile = (file) => {
    // Stub implementation - return mock parsed data
    return [
      { description: 'Tomatoes', qty: 10, unit: 'kg', unitPrice: 2.50 },
      { description: 'Olive Oil', qty: 5, unit: 'L', unitPrice: 15.00 },
    ];
  };

  const openMappingDialog = () => {
    // Stub: In real implementation, this would parse the uploaded file
    const stubData = parseUploadedFile(null);
    setParsedRows(stubData);
    setShowMappingDialog(true);
  };

  const applyMappedRows = () => {
    // Apply mapped rows to form lines
    setFormData({
      ...formData,
      lines: parsedRows.map(row => ({
        ingredientId: '',
        description: row.description,
        qty: row.qty.toString(),
        unit: row.unit,
        unitPrice: row.unitPrice.toString(),
        packFormat: '',
        expiryDate: ''
      }))
    });
    setShowMappingDialog(false);
    toast.success(t('receiving.success.mapped') || 'Rows mapped successfully');
  };

  const getCategoryBadgeColor = (category) => {
    switch (category) {
      case 'food': return 'bg-green-100 text-green-800';
      case 'beverage': return 'bg-blue-100 text-blue-800';
      case 'nofood': return 'bg-gray-100 text-gray-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">{t('receiving.title') || 'Receiving'}</h1>
        <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
          <DialogTrigger asChild>
            <Button onClick={resetForm}>
              <Plus className="mr-2 h-4 w-4" />
              {t('receiving.add') || 'Add Receiving'}
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <div className="flex items-center justify-between">
                <DialogTitle>
                  {editingId ? (t('receiving.edit') || 'Edit Receiving') : (t('receiving.add') || 'Add Receiving')}
                </DialogTitle>
                {!editingId && (
                  <OCRUploadButton 
                    onParsed={handleOCRParsed}
                    context="receiving"
                    supplierId={formData.supplierId}
                    buttonVariant="outline"
                  />
                )}
              </div>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="supplierId">{t('receiving.form.supplier') || 'Supplier'} *</Label>
                  <Select 
                    value={formData.supplierId} 
                    onValueChange={(value) => setFormData({ ...formData, supplierId: value })}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder={t('receiving.form.selectSupplier') || 'Select supplier'} />
                    </SelectTrigger>
                    <SelectContent>
                      {suppliers.map(supplier => (
                        <SelectItem key={supplier.id} value={supplier.id}>{supplier.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <Label htmlFor="category">{t('receiving.form.category') || 'Category'} *</Label>
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
              </div>

              {/* Price Lists Section */}
              {formData.supplierId && (() => {
                const selectedSupplier = suppliers.find(s => s.id === formData.supplierId);
                const priceLists = selectedSupplier?.files?.filter(f => f.fileType === 'price_list') || [];
                
                return priceLists.length > 0 ? (
                  <div className="bg-blue-50 border border-blue-200 rounded-md p-3">
                    <div className="flex items-center gap-2 mb-2">
                      <FileText className="h-4 w-4 text-blue-600" />
                      <h4 className="text-sm font-medium text-blue-900">
                        {t('receiving.priceLists') || 'Price Lists'}
                      </h4>
                    </div>
                    <div className="space-y-1">
                      {priceLists.map((file) => (
                        <div key={file.id} className="flex items-center justify-between">
                          <span className="text-xs text-blue-800">{file.filename}</span>
                          <div className="flex gap-1">
                            {file.downloadUrl && (
                              <a
                                href={file.downloadUrl}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-xs text-blue-600 hover:text-blue-800 flex items-center gap-1"
                              >
                                <Download className="h-3 w-3" />
                                {t('common.download') || 'Download'}
                              </a>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : null;
              })()}

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="arrivedAt">{t('receiving.form.arrivedAt') || 'Arrived Date'} *</Label>
                  <Input
                    id="arrivedAt"
                    type="date"
                    value={formData.arrivedAt}
                    onChange={(e) => setFormData({ ...formData, arrivedAt: e.target.value })}
                    required
                  />
                </div>
              </div>

              <div>
                <Label htmlFor="notes">{t('receiving.form.notes') || 'Notes'}</Label>
                <textarea
                  id="notes"
                  className="flex min-h-[60px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                  value={formData.notes}
                  onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                />
              </div>

              <div className="border-t pt-4">
                <div className="flex justify-between items-center mb-3">
                  <h3 className="font-medium">{t('receiving.form.lines') || 'Line Items'}</h3>
                  <Button type="button" size="sm" variant="outline" onClick={addLine}>
                    <Plus className="h-4 w-4 mr-1" />
                    {t('receiving.form.addLine') || 'Add Line'}
                  </Button>
                </div>

                <div className="space-y-3">
                  {formData.lines.map((line, index) => (
                    <Card key={index} className="p-3">
                      <div className="grid grid-cols-12 gap-2">
                        <div className="col-span-2">
                          <Label className="text-xs">{t('receiving.form.ingredient') || 'Ingredient'}</Label>
                          <Select 
                            value={line.ingredientId} 
                            onValueChange={(value) => updateLine(index, 'ingredientId', value)}
                          >
                            <SelectTrigger className="h-9">
                              <SelectValue placeholder={t('receiving.form.optional') || 'Optional'} />
                            </SelectTrigger>
                            <SelectContent>
                              {ingredients.map(ing => (
                                <SelectItem key={ing.id} value={ing.id}>{ing.name}</SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>
                        <div className="col-span-2">
                          <Label className="text-xs">{t('receiving.form.description') || 'Description'} *</Label>
                          <Input
                            className="h-9"
                            value={line.description}
                            onChange={(e) => updateLine(index, 'description', e.target.value)}
                            required
                          />
                        </div>
                        <div className="col-span-2">
                          <Label className="text-xs">{t('receiving.form.qty') || 'Qty'} *</Label>
                          <Input
                            className="h-9"
                            type="number"
                            step="0.01"
                            value={line.qty}
                            onChange={(e) => updateLine(index, 'qty', e.target.value)}
                            required
                          />
                        </div>
                        <div className="col-span-1">
                          <Label className="text-xs">{t('receiving.form.unit') || 'Unit'}</Label>
                          <Input
                            className="h-9"
                            value={line.unit}
                            onChange={(e) => updateLine(index, 'unit', e.target.value)}
                          />
                        </div>
                        <div className="col-span-2">
                          <Label htmlFor={`line-${index}-target`} className="text-xs">
                            {t('receiving.targetInventory') || 'Target Inventory'} *
                          </Label>
                          <Select
                            value={line.targetInventory || 'food'}
                            onValueChange={(value) => updateLine(index, 'targetInventory', value)}
                          >
                            <SelectTrigger className="h-9">
                              <SelectValue placeholder={t('receiving.selectTarget') || 'Select target'} />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="food">{t('receiving.category.food') || 'Food'}</SelectItem>
                              <SelectItem value="beverage">{t('receiving.category.beverage') || 'Beverage'}</SelectItem>
                              <SelectItem value="nofood">{t('receiving.category.nofood') || 'Non-Food'}</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                        <div className="col-span-2">
                          <Label htmlFor={`line-${index}-price`} className="text-xs flex items-center gap-1">
                            {t('receiving.form.unitPrice') || 'Price'} *
                            {line.ingredientId && (
                              <Popover>
                                <PopoverTrigger asChild>
                                  <button
                                    type="button"
                                    className="text-blue-600 hover:text-blue-800"
                                    onClick={() => fetchPriceHistory(line.ingredientId)}
                                  >
                                    <History className="h-3 w-3" />
                                  </button>
                                </PopoverTrigger>
                                <PopoverContent className="w-80">
                                  <div className="space-y-2">
                                    <h4 className="font-medium text-sm flex items-center gap-2">
                                      <TrendingUp className="h-4 w-4" />
                                      {t('receiving.priceHistory') || 'Price History'}
                                    </h4>
                                    {priceHistory[line.ingredientId]?.loading && (
                                      <p className="text-xs text-gray-500">{t('common.loading') || 'Loading...'}</p>
                                    )}
                                    {priceHistory[line.ingredientId]?.error && (
                                      <p className="text-xs text-red-600">{t('receiving.error.priceHistory') || 'Failed to load history'}</p>
                                    )}
                                    {priceHistory[line.ingredientId]?.data?.history?.length === 0 && (
                                      <p className="text-xs text-gray-500">{t('receiving.noHistory') || 'No price history available'}</p>
                                    )}
                                    {priceHistory[line.ingredientId]?.data?.history?.length > 0 && (
                                      <div className="space-y-2 max-h-60 overflow-y-auto">
                                        {priceHistory[line.ingredientId].data.history.map((item, idx) => (
                                          <div key={idx} className="border-b pb-2 last:border-0">
                                            <div className="flex justify-between items-start">
                                              <div className="text-xs">
                                                <div className="font-medium">{formatMinor(Math.round(item.unitPrice * 100))}</div>
                                                <div className="text-gray-500">{new Date(item.date).toLocaleDateString()}</div>
                                                {item.supplierName && (
                                                  <div className="text-gray-500">{item.supplierName}</div>
                                                )}
                                              </div>
                                              <div className="text-xs text-right text-gray-600">
                                                <div>{item.qty} {item.unit}</div>
                                                {item.packFormat && (
                                                  <div className="text-gray-400">{item.packFormat}</div>
                                                )}
                                              </div>
                                            </div>
                                          </div>
                                        ))}
                                      </div>
                                    )}
                                  </div>
                                </PopoverContent>
                              </Popover>
                            )}
                          </Label>
                          <Input
                            className="h-9"
                            type="number"
                            step="0.01"
                            value={line.unitPrice}
                            onChange={(e) => updateLine(index, 'unitPrice', e.target.value)}
                            required
                          />
                        </div>
                        <div className="col-span-1 flex items-end">
                          <Button 
                            type="button" 
                            size="sm" 
                            variant="ghost" 
                            onClick={() => removeLine(index)}
                            disabled={formData.lines.length === 1}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>
                    </Card>
                  ))}
                </div>
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
      </div>

      <div className="grid gap-4">
        {receivings.map((receiving) => {
          const supplier = suppliers.find(s => s.id === receiving.supplierId);
          return (
            <Card key={receiving.id}>
              <CardHeader>
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <CardTitle className="flex items-center gap-2">
                      {supplier?.name || t('receiving.unknownSupplier') || 'Unknown Supplier'}
                      <span className={`text-xs px-2 py-1 rounded ${getCategoryBadgeColor(receiving.category)}`}>
                        {t(`receiving.category.${receiving.category}`) || receiving.category}
                      </span>
                      {receiving.importedFromOCR && (
                        <span className="text-xs px-2 py-1 rounded bg-purple-100 text-purple-800 flex items-center gap-1">
                          <FileText className="h-3 w-3" />
                          {t('receiving.ocrImported') || 'OCR Import'}
                        </span>
                      )}
                    </CardTitle>
                    <div className="text-sm text-muted-foreground mt-1">
                      {t('receiving.arrivedAt') || 'Arrived'}: {new Date(receiving.arrivedAt).toLocaleDateString()}
                    </div>
                    <div className="text-sm font-medium mt-1">
                      {t('receiving.total') || 'Total'}: {formatMinor(receiving.total)}
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <Button size="sm" variant="outline" onClick={() => handleEdit(receiving)}>
                      <Edit className="h-4 w-4" />
                    </Button>
                    <Button size="sm" variant="outline" onClick={() => handleDelete(receiving.id)}>
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                {receiving.notes && (
                  <div className="mb-3 text-sm text-muted-foreground">
                    <strong>{t('receiving.form.notes') || 'Notes'}:</strong> {receiving.notes}
                  </div>
                )}

                <div className="border-t pt-3 mb-3">
                  <h4 className="font-medium text-sm mb-2">{t('receiving.form.lines') || 'Line Items'} ({receiving.lines.length})</h4>
                  <div className="space-y-1">
                    {receiving.lines.map((line, idx) => (
                      <div key={idx} className="text-sm flex justify-between items-center p-2 bg-muted/30 rounded">
                        <span>{line.description} - {line.qty} {line.unit}</span>
                        <span className="font-medium">{formatMinor(line.unitPrice)}/{line.unit}</span>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="border-t pt-3">
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="font-medium text-sm">{t('receiving.files') || 'Files'} ({receiving.files?.length || 0})</h4>
                    <div>
                      <input
                        type="file"
                        id={`file-upload-${receiving.id}`}
                        className="hidden"
                        onChange={(e) => handleFileUpload(receiving.id, e)}
                        disabled={uploadingFor === receiving.id}
                      />
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => document.getElementById(`file-upload-${receiving.id}`).click()}
                        disabled={uploadingFor === receiving.id}
                      >
                        <Upload className="mr-2 h-4 w-4" />
                        {uploadingFor === receiving.id ? (t('receiving.uploading') || 'Uploading...') : (t('receiving.upload') || 'Upload')}
                      </Button>
                    </div>
                  </div>

                  {receiving.files && receiving.files.length > 0 && (
                    <div className="space-y-1">
                      {receiving.files.map((file) => (
                        <div key={file.id} className="flex items-center justify-between p-2 border rounded text-sm hover:bg-muted/50">
                          <div className="flex items-center gap-2 flex-1 min-w-0">
                            <FileText className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                            <span className="truncate">{file.filename}</span>
                            <span className="text-xs text-muted-foreground flex-shrink-0">
                              ({(file.size / 1024).toFixed(1)} KB)
                            </span>
                          </div>
                          <div className="flex gap-1 flex-shrink-0">
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => handleFileDownload(file.id, file.filename)}
                            >
                              <Download className="h-4 w-4" />
                            </Button>
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => handleFileDelete(receiving.id, file.id, file.filename)}
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          );
        })}

        {receivings.length === 0 && (
          <div className="text-center py-12 text-muted-foreground">
            {t('receiving.noData') || 'No receiving records yet'}
          </div>
        )}
      </div>
    </div>
  );
}

export default Receiving;
