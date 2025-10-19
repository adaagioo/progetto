import React, { useState, useContext } from 'react';
import { useTranslation } from 'react-i18next';
import axios from 'axios';
import { API, AuthContext } from '../App';
import { useCurrency } from '../contexts/CurrencyContext';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Upload, FileText, Check, X, AlertCircle, Loader2, Eye } from 'lucide-react';
import { toast } from 'sonner';

function DocumentImport() {
  const { t } = useTranslation();
  const { user } = useContext(AuthContext);
  const { formatMinor } = useCurrency();
  
  const [file, setFile] = useState(null);
  const [processing, setProcessing] = useState(false);
  const [ocrResult, setOcrResult] = useState(null);
  const [parsedData, setParsedData] = useState(null);
  const [suppliers, setSuppliers] = useState([]);
  const [ingredients, setIngredients] = useState([]);
  const [selectedSupplier, setSelectedSupplier] = useState('');
  const [lineItems, setLineItems] = useState([]);
  const [importing, setImporting] = useState(false);
  const [step, setStep] = useState('upload'); // upload, review, import

  React.useEffect(() => {
    fetchSuppliers();
    fetchIngredients();
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
      console.error('Failed to load ingredients:', error);
    }
  };

  const handleFileSelect = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      setFile(selectedFile);
      setOcrResult(null);
      setParsedData(null);
      setStep('upload');
    }
  };

  const processDocument = async () => {
    if (!file) {
      toast.error(t('ocr.error.noFile') || 'Please select a file');
      return;
    }

    setProcessing(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('lang', 'eng'); // Could be made selectable

      const response = await axios.post(`${API}/ocr/process`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });

      setOcrResult(response.data.ocr);
      setParsedData(response.data.parsed);
      
      // Initialize line items with parsed data
      const items = response.data.parsed.line_items || [];
      setLineItems(items.map(item => ({
        ...item,
        ingredientId: '',
        mapped: false
      })));

      // Try to auto-match supplier
      const supplierName = response.data.parsed.supplier_name;
      if (supplierName) {
        const matchedSupplier = suppliers.find(s => 
          s.name.toLowerCase().includes(supplierName.toLowerCase()) ||
          supplierName.toLowerCase().includes(s.name.toLowerCase())
        );
        if (matchedSupplier) {
          setSelectedSupplier(matchedSupplier.id);
          toast.success(t('ocr.supplierMatched') || `Supplier matched: ${matchedSupplier.name}`);
        }
      }

      setStep('review');
      toast.success(t('ocr.success') || 'Document processed successfully');
    } catch (error) {
      console.error('OCR processing error:', error);
      toast.error(error.response?.data?.detail || t('ocr.error.processing') || 'Failed to process document');
    } finally {
      setProcessing(false);
    }
  };

  const suggestIngredient = (description) => {
    // Simple fuzzy matching
    const query = description.toLowerCase();
    return ingredients.find(ing => {
      const name = ing.name.toLowerCase();
      return name.includes(query) || query.includes(name);
    });
  };

  const mapLineItem = (index, ingredientId) => {
    const updated = [...lineItems];
    updated[index].ingredientId = ingredientId;
    updated[index].mapped = !!ingredientId;
    
    // Auto-fill unit from ingredient if available
    if (ingredientId) {
      const ingredient = ingredients.find(i => i.id === ingredientId);
      if (ingredient && !updated[index].unit) {
        updated[index].unit = ingredient.unit;
      }
    }
    
    setLineItems(updated);
  };

  const updateLineItem = (index, field, value) => {
    const updated = [...lineItems];
    updated[index][field] = value;
    setLineItems(updated);
  };

  const importDocument = async () => {
    // Validation
    if (!selectedSupplier) {
      toast.error(t('ocr.error.noSupplier') || 'Please select a supplier');
      return;
    }

    const mappedItems = lineItems.filter(item => item.ingredientId);
    if (mappedItems.length === 0) {
      toast.error(t('ocr.error.noMappedItems') || 'Please map at least one item to an ingredient');
      return;
    }

    setImporting(true);
    try {
      const payload = {
        supplierId: selectedSupplier,
        date: parsedData.date,
        invoiceNumber: parsedData.invoice_number,
        documentType: parsedData.document_type,
        category: 'food',
        lineItems: mappedItems.map(item => ({
          ingredientId: item.ingredientId,
          description: item.description,
          qty: parseFloat(item.qty) || 0,
          unit: item.unit || 'kg',
          unitPrice: parseFloat(item.price) || 0,
          packFormat: item.packFormat || ''
        }))
      };

      await axios.post(`${API}/ocr/create-receiving`, payload);
      
      toast.success(t('ocr.importSuccess') || 'Receiving record created successfully');
      
      // Reset form
      setFile(null);
      setOcrResult(null);
      setParsedData(null);
      setLineItems([]);
      setSelectedSupplier('');
      setStep('upload');
      
    } catch (error) {
      console.error('Import error:', error);
      toast.error(error.response?.data?.detail || t('ocr.error.import') || 'Failed to create receiving');
    } finally {
      setImporting(false);
    }
  };

  const mappedCount = lineItems.filter(item => item.mapped).length;
  const confidence = ocrResult?.confidence || 0;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">{t('ocr.title') || 'Document Import'}</h1>
          <p className="text-gray-600 mt-1">{t('ocr.subtitle') || 'Import invoices and price lists using OCR'}</p>
        </div>
      </div>

      {/* Step 1: Upload */}
      {step === 'upload' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Upload className="h-5 w-5" />
              {t('ocr.uploadDocument') || 'Upload Document'}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center">
              <Upload className="h-12 w-12 mx-auto text-gray-400 mb-4" />
              <p className="text-sm text-gray-600 mb-4">
                {t('ocr.uploadInstructions') || 'Upload an invoice or price list (JPG, PNG, PDF)'}
              </p>
              <input
                type="file"
                accept=".jpg,.jpeg,.png,.pdf"
                onChange={handleFileSelect}
                className="hidden"
                id="file-upload"
              />
              <label htmlFor="file-upload">
                <Button asChild className="cursor-pointer">
                  <span>{t('common.selectFile') || 'Select File'}</span>
                </Button>
              </label>
            </div>

            {file && (
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <FileText className="h-8 w-8 text-blue-600" />
                    <div>
                      <p className="font-medium">{file.name}</p>
                      <p className="text-sm text-gray-600">{(file.size / 1024).toFixed(2)} KB</p>
                    </div>
                  </div>
                  <Button onClick={() => setFile(null)} variant="ghost" size="sm">
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            )}

            <Button 
              onClick={processDocument} 
              disabled={!file || processing}
              className="w-full"
            >
              {processing ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  {t('ocr.processing') || 'Processing...'}
                </>
              ) : (
                <>
                  <Eye className="h-4 w-4 mr-2" />
                  {t('ocr.processDocument') || 'Process Document'}
                </>
              )}
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Step 2: Review & Map */}
      {step === 'review' && parsedData && (
        <div className="space-y-6">
          {/* OCR Quality */}
          <Card>
            <CardHeader>
              <CardTitle>{t('ocr.results') || 'OCR Results'}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div>
                  <Label className="text-xs text-gray-500">{t('ocr.confidence') || 'Confidence'}</Label>
                  <p className="text-lg font-semibold">{confidence}%</p>
                </div>
                <div>
                  <Label className="text-xs text-gray-500">{t('ocr.documentType') || 'Type'}</Label>
                  <p className="text-lg font-semibold capitalize">{parsedData.document_type}</p>
                </div>
                <div>
                  <Label className="text-xs text-gray-500">{t('ocr.invoiceNumber') || 'Invoice #'}</Label>
                  <p className="text-lg font-semibold">{parsedData.invoice_number || 'N/A'}</p>
                </div>
                <div>
                  <Label className="text-xs text-gray-500">{t('common.date') || 'Date'}</Label>
                  <p className="text-lg font-semibold">{parsedData.date || 'N/A'}</p>
                </div>
              </div>

              {confidence < 50 && (
                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 flex items-start gap-2">
                  <AlertCircle className="h-5 w-5 text-yellow-600 mt-0.5" />
                  <div>
                    <p className="font-medium text-yellow-800">{t('ocr.lowConfidence') || 'Low Confidence'}</p>
                    <p className="text-sm text-yellow-700">
                      {t('ocr.lowConfidenceMessage') || 'The OCR confidence is low. Please review extracted data carefully.'}
                    </p>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Supplier Selection */}
          <Card>
            <CardHeader>
              <CardTitle>{t('ocr.selectSupplier') || 'Select Supplier'}</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {parsedData.supplier_name && (
                  <p className="text-sm text-gray-600">
                    {t('ocr.detectedSupplier') || 'Detected'}: <span className="font-medium">{parsedData.supplier_name}</span>
                  </p>
                )}
                <Select value={selectedSupplier} onValueChange={setSelectedSupplier}>
                  <SelectTrigger>
                    <SelectValue placeholder={t('ocr.chooseSupplier') || 'Choose supplier...'} />
                  </SelectTrigger>
                  <SelectContent>
                    {suppliers.map(supplier => (
                      <SelectItem key={supplier.id} value={supplier.id}>
                        {supplier.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </CardContent>
          </Card>

          {/* Line Items Mapping */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span>{t('ocr.mapItems') || 'Map Line Items'}</span>
                <span className="text-sm font-normal text-gray-600">
                  {mappedCount}/{lineItems.length} {t('ocr.mapped') || 'mapped'}
                </span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {lineItems.map((item, index) => {
                  const suggestion = !item.ingredientId && suggestIngredient(item.description);
                  
                  return (
                    <div key={index} className={`border rounded-lg p-4 ${item.mapped ? 'border-green-300 bg-green-50' : 'border-gray-300'}`}>
                      <div className="grid gap-4">
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <p className="font-medium">{item.description}</p>
                            <p className="text-sm text-gray-600">
                              {item.qty} {item.unit} × {formatMinor(Math.round((item.price || 0) * 100))}
                            </p>
                          </div>
                          {item.mapped && (
                            <Check className="h-5 w-5 text-green-600" />
                          )}
                        </div>

                        <div className="grid grid-cols-2 gap-3">
                          <div>
                            <Label className="text-xs">{t('ocr.mapToIngredient') || 'Map to Ingredient'} *</Label>
                            <Select 
                              value={item.ingredientId || ''} 
                              onValueChange={(value) => mapLineItem(index, value)}
                            >
                              <SelectTrigger className={suggestion ? 'border-blue-300' : ''}>
                                <SelectValue placeholder={t('ocr.selectIngredient') || 'Select...'} />
                              </SelectTrigger>
                              <SelectContent>
                                {suggestion && (
                                  <>
                                    <SelectItem value={suggestion.id} className="bg-blue-50 font-medium">
                                      ✨ {suggestion.name} (suggested)
                                    </SelectItem>
                                    <div className="border-b my-1" />
                                  </>
                                )}
                                {ingredients.map(ing => (
                                  <SelectItem key={ing.id} value={ing.id}>
                                    {ing.name}
                                  </SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                          </div>

                          <div>
                            <Label className="text-xs">{t('receiving.form.unitPrice') || 'Unit Price'}</Label>
                            <Input
                              type="number"
                              step="0.01"
                              value={item.price || ''}
                              onChange={(e) => updateLineItem(index, 'price', e.target.value)}
                            />
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })}

                {lineItems.length === 0 && (
                  <p className="text-center text-gray-500 py-8">
                    {t('ocr.noItemsFound') || 'No line items found in document'}
                  </p>
                )}
              </div>

              <div className="mt-6 flex gap-3">
                <Button onClick={() => setStep('upload')} variant="outline" className="flex-1">
                  {t('common.back') || 'Back'}
                </Button>
                <Button 
                  onClick={importDocument} 
                  disabled={mappedCount === 0 || !selectedSupplier || importing}
                  className="flex-1"
                >
                  {importing ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      {t('ocr.importing') || 'Importing...'}
                    </>
                  ) : (
                    <>
                      <Check className="h-4 w-4 mr-2" />
                      {t('ocr.createReceiving') || 'Create Receiving'}
                    </>
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}

export default DocumentImport;
