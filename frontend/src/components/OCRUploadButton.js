import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import axios from 'axios';
import { API } from '../App';
import { Button } from './ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from './ui/dialog';
import { Upload, Loader2, FileText, Check } from 'lucide-react';
import { toast } from 'sonner';

/**
 * Reusable OCR Upload Button Component
 * Can be embedded in any module (Receiving, Suppliers, Sales, P&L)
 */
function OCRUploadButton({ 
  onParsed, 
  context = 'receiving', // 'receiving', 'supplier', 'sales', 'pl'
  supplierId = null,
  buttonText = null,
  buttonVariant = 'outline'
}) {
  const { t } = useTranslation();
  const [file, setFile] = useState(null);
  const [processing, setProcessing] = useState(false);
  const [showDialog, setShowDialog] = useState(false);

  const handleFileSelect = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      setFile(selectedFile);
      // Auto-process on selection
      processFile(selectedFile);
    }
  };

  const processFile = async (fileToProcess) => {
    setProcessing(true);
    setShowDialog(true);
    
    try {
      const formData = new FormData();
      formData.append('file', fileToProcess);
      formData.append('lang', 'ita'); // Auto-detect or make selectable

      const response = await axios.post(`${API}/ocr/process`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });

      // Load saved mappings if supplier provided
      let savedMappings = {};
      if (supplierId) {
        try {
          const mappingsResponse = await axios.get(`${API}/ocr/mappings/${supplierId}`);
          const mappings = mappingsResponse.data.mappings || [];
          // Build lookup map: description -> ingredientId
          savedMappings = mappings.reduce((acc, m) => {
            acc[m.description.toLowerCase()] = m.ingredientId;
            if (m.code) {
              acc[m.code.toLowerCase()] = m.ingredientId;
            }
            return acc;
          }, {});
        } catch (err) {
          console.warn('Failed to load saved mappings:', err);
        }
      }

      // Auto-apply saved mappings to parsed items
      const items = response.data.parsed.line_items || [];
      const itemsWithMappings = items.map(item => {
        const desc = item.description?.toLowerCase() || '';
        const code = item.code?.toLowerCase() || '';
        
        // Try to find saved mapping
        const mappedIngredientId = savedMappings[desc] || savedMappings[code];
        
        return {
          ...item,
          ingredientId: mappedIngredientId || '',
          mapped: !!mappedIngredientId,
          autoMapped: !!mappedIngredientId
        };
      });

      const autoMappedCount = itemsWithMappings.filter(i => i.autoMapped).length;
      
      if (autoMappedCount > 0) {
        toast.success(
          t('ocr.autoMappedItems', { count: autoMappedCount }) || 
          `${autoMappedCount} items auto-mapped from saved mappings`
        );
      }

      // Pass parsed data to parent component
      if (onParsed) {
        onParsed({
          ocrResult: response.data.ocr,
          parsedData: response.data.parsed,
          items: itemsWithMappings,
          context
        });
      }

      toast.success(t('ocr.success') || 'Document processed successfully');
      setShowDialog(false);
      setFile(null);
      
    } catch (error) {
      console.error('OCR processing error:', error);
      toast.error(
        error.response?.data?.detail || 
        t('ocr.error.processing') || 
        'Failed to process document'
      );
    } finally {
      setProcessing(false);
    }
  };

  const defaultButtonText = buttonText || t('ocr.uploadInvoice') || 'Upload Invoice (OCR)';

  return (
    <>
      <input
        type="file"
        accept=".jpg,.jpeg,.png,.pdf"
        onChange={handleFileSelect}
        className="hidden"
        id={`ocr-upload-${context}`}
      />
      <label htmlFor={`ocr-upload-${context}`}>
        <Button asChild variant={buttonVariant} className="cursor-pointer">
          <span>
            <FileText className="h-4 w-4 mr-2" />
            {defaultButtonText}
          </span>
        </Button>
      </label>

      <Dialog open={showDialog} onOpenChange={setShowDialog}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>{t('ocr.processing') || 'Processing Document...'}</DialogTitle>
          </DialogHeader>
          <div className="flex flex-col items-center justify-center py-8 space-y-4">
            {processing ? (
              <>
                <Loader2 className="h-12 w-12 animate-spin text-blue-600" />
                <p className="text-sm text-gray-600">
                  {t('ocr.extractingText') || 'Extracting text from document...'}
                </p>
              </>
            ) : (
              <>
                <Check className="h-12 w-12 text-green-600" />
                <p className="text-sm text-gray-600">
                  {t('ocr.complete') || 'Processing complete!'}
                </p>
              </>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}

export default OCRUploadButton;
