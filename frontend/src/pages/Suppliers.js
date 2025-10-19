import React, { useState, useEffect, useContext } from 'react';
import { useTranslation } from 'react-i18next';
import axios from 'axios';
import { API, AuthContext } from '../App';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Plus, Trash2, Edit, Upload, Download, FileText } from 'lucide-react';
import { toast } from 'sonner';
import OCRUploadButton from '../components/OCRUploadButton';

function Suppliers() {
  const { t } = useTranslation();
  const { user } = useContext(AuthContext);
  const [suppliers, setSuppliers] = useState([]);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [uploadingFor, setUploadingFor] = useState(null);
  const [showOCRPriceList, setShowOCRPriceList] = useState(false);
  const [ocrSupplierId, setOCRSupplierId] = useState(null);
  const [ocrParsedItems, setOCRParsedItems] = useState([]);
  const [formData, setFormData] = useState({
    name: '',
    contactName: '',
    contactPhone: '',
    contactEmail: '',
    notes: ''
  });

  useEffect(() => {
    fetchSuppliers();
  }, []);

  const fetchSuppliers = async () => {
    try {
      const response = await axios.get(`${API}/suppliers`);
      setSuppliers(response.data);
    } catch (error) {
      toast.error(t('suppliers.error.load') || 'Failed to load suppliers');
    }
  };

  const handleOCRParsed = (data) => {
    setOCRParsedItems(data.items || []);
    setShowOCRPriceList(true);
    toast.success(t('suppliers.ocrParsed') || 'Price list parsed successfully');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    const payload = {
      name: formData.name,
      contacts: {
        name: formData.contactName || null,
        phone: formData.contactPhone || null,
        email: formData.contactEmail || null
      },
      notes: formData.notes || null
    };

    try {
      if (editingId) {
        await axios.put(`${API}/suppliers/${editingId}`, payload);
        toast.success(t('suppliers.success.updated') || 'Supplier updated successfully');
      } else {
        await axios.post(`${API}/suppliers`, payload);
        toast.success(t('suppliers.success.created') || 'Supplier created successfully');
      }
      fetchSuppliers();
      resetForm();
      setIsDialogOpen(false);
    } catch (error) {
      toast.error(error.response?.data?.detail || t('suppliers.error.save') || 'Failed to save supplier');
    }
  };

  const handleEdit = (supplier) => {
    setEditingId(supplier.id);
    setFormData({
      name: supplier.name,
      contactName: supplier.contacts?.name || '',
      contactPhone: supplier.contacts?.phone || '',
      contactEmail: supplier.contacts?.email || '',
      notes: supplier.notes || ''
    });
    setIsDialogOpen(true);
  };

  const handleDelete = async (id) => {
    if (!window.confirm(t('suppliers.confirm.delete') || 'Are you sure you want to delete this supplier?')) return;

    try {
      await axios.delete(`${API}/suppliers/${id}`);
      toast.success(t('suppliers.success.deleted') || 'Supplier deleted');
      fetchSuppliers();
    } catch (error) {
      toast.error(t('suppliers.error.delete') || 'Failed to delete supplier');
    }
  };

  const resetForm = () => {
    setFormData({
      name: '',
      contactName: '',
      contactPhone: '',
      contactEmail: '',
      notes: ''
    });
    setEditingId(null);
  };

  const handleFileUpload = async (supplierId, event, fileType = 'general') => {
    const file = event.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);
    formData.append('fileType', fileType);

    try {
      setUploadingFor(supplierId);
      await axios.post(`${API}/suppliers/${supplierId}/files`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      const message = fileType === 'price_list' 
        ? (t('suppliers.priceListUploaded') || 'Price list uploaded successfully')
        : (t('suppliers.success.fileUploaded') || 'File uploaded successfully');
      toast.success(message);
      fetchSuppliers();
    } catch (error) {
      toast.error(error.response?.data?.detail || t('suppliers.error.upload') || 'Failed to upload file');
    } finally {
      setUploadingFor(null);
      event.target.value = '';
    }
  };

  const handleFileDelete = async (supplierId, fileId, fileName) => {
    if (!window.confirm(t('suppliers.confirm.deleteFile', { fileName }) || `Delete file ${fileName}?`)) return;

    try {
      await axios.delete(`${API}/suppliers/${supplierId}/files/${fileId}`);
      toast.success(t('suppliers.success.fileDeleted') || 'File deleted');
      fetchSuppliers();
    } catch (error) {
      toast.error(t('suppliers.error.fileDelete') || 'Failed to delete file');
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
      toast.error(t('suppliers.error.fileDownload') || 'Failed to download file');
    }
  };

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">{t('suppliers.title') || 'Suppliers'}</h1>
        <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
          <DialogTrigger asChild>
            <Button onClick={resetForm}>
              <Plus className="mr-2 h-4 w-4" />
              {t('suppliers.add') || 'Add Supplier'}
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>
                {editingId ? (t('suppliers.edit') || 'Edit Supplier') : (t('suppliers.add') || 'Add Supplier')}
              </DialogTitle>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <Label htmlFor="name">{t('suppliers.form.name') || 'Supplier Name'} *</Label>
                <Input
                  id="name"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  required
                />
              </div>

              <div className="grid grid-cols-3 gap-4">
                <div>
                  <Label htmlFor="contactName">{t('suppliers.form.contactName') || 'Contact Name'}</Label>
                  <Input
                    id="contactName"
                    value={formData.contactName}
                    onChange={(e) => setFormData({ ...formData, contactName: e.target.value })}
                  />
                </div>
                <div>
                  <Label htmlFor="contactPhone">{t('suppliers.form.contactPhone') || 'Phone'}</Label>
                  <Input
                    id="contactPhone"
                    value={formData.contactPhone}
                    onChange={(e) => setFormData({ ...formData, contactPhone: e.target.value })}
                  />
                </div>
                <div>
                  <Label htmlFor="contactEmail">{t('suppliers.form.contactEmail') || 'Email'}</Label>
                  <Input
                    id="contactEmail"
                    type="email"
                    value={formData.contactEmail}
                    onChange={(e) => setFormData({ ...formData, contactEmail: e.target.value })}
                  />
                </div>
              </div>

              <div>
                <Label htmlFor="notes">{t('suppliers.form.notes') || 'Notes'}</Label>
                <textarea
                  id="notes"
                  className="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                  value={formData.notes}
                  onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                />
              </div>

              <div className="flex justify-end gap-2">
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
        {suppliers.map((supplier) => (
          <Card key={supplier.id}>
            <CardHeader>
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <CardTitle>{supplier.name}</CardTitle>
                  {supplier.contacts && (
                    <div className="text-sm text-muted-foreground mt-2 space-y-1">
                      {supplier.contacts.name && <div>{t('suppliers.form.contactName') || 'Contact'}: {supplier.contacts.name}</div>}
                      {supplier.contacts.phone && <div>{t('suppliers.form.contactPhone') || 'Phone'}: {supplier.contacts.phone}</div>}
                      {supplier.contacts.email && <div>{t('suppliers.form.contactEmail') || 'Email'}: {supplier.contacts.email}</div>}
                    </div>
                  )}
                </div>
                <div className="flex gap-2">
                  <Button size="sm" variant="outline" onClick={() => handleEdit(supplier)}>
                    <Edit className="h-4 w-4" />
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => handleDelete(supplier.id)}>
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {supplier.notes && (
                <div className="mb-4 text-sm text-muted-foreground">
                  <strong>{t('suppliers.form.notes') || 'Notes'}:</strong> {supplier.notes}
                </div>
              )}

              <div className="border-t pt-4">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-medium">{t('suppliers.files') || 'Files'} ({supplier.files?.length || 0})</h3>
                  <div className="flex gap-2">
                    <input
                      type="file"
                      id={`file-upload-${supplier.id}`}
                      className="hidden"
                      onChange={(e) => handleFileUpload(supplier.id, e, 'general')}
                      disabled={uploadingFor === supplier.id}
                    />
                    <input
                      type="file"
                      id={`price-list-upload-${supplier.id}`}
                      className="hidden"
                      accept=".pdf,.xlsx,.xls,.doc,.docx,.jpg,.jpeg,.png"
                      onChange={(e) => handleFileUpload(supplier.id, e, 'price_list')}
                      disabled={uploadingFor === supplier.id}
                    />
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => document.getElementById(`price-list-upload-${supplier.id}`).click()}
                      disabled={uploadingFor === supplier.id}
                      data-testid="upload-price-list-button"
                    >
                      <Upload className="mr-2 h-4 w-4" />
                      {t('suppliers.uploadPriceList') || 'Upload Price List'}
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => document.getElementById(`file-upload-${supplier.id}`).click()}
                      disabled={uploadingFor === supplier.id}
                    >
                      <Upload className="mr-2 h-4 w-4" />
                      {uploadingFor === supplier.id ? (t('suppliers.uploading') || 'Uploading...') : (t('suppliers.upload') || 'Upload File')}
                    </Button>
                  </div>
                </div>

                {supplier.files && supplier.files.length > 0 && (
                  <div className="space-y-2">
                    {supplier.files.map((file) => (
                      <div key={file.id} className="flex items-center justify-between p-2 border rounded hover:bg-muted/50">
                        <div className="flex items-center gap-2 flex-1 min-w-0">
                          <FileText className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                          <span className="text-sm truncate">{file.filename}</span>
                          {file.fileType === 'price_list' && (
                            <span className="px-2 py-0.5 text-xs bg-green-100 text-green-800 rounded flex-shrink-0">
                              {t('suppliers.priceList') || 'Price List'}
                            </span>
                          )}
                          <span className="text-xs text-muted-foreground flex-shrink-0">
                            ({(file.size / 1024).toFixed(1)} KB)
                          </span>
                        </div>
                        <div className="flex gap-2 flex-shrink-0">
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => handleFileDownload(file.id, file.filename)}
                            title={t('suppliers.downloadPriceList') || 'Download'}
                          >
                            <Download className="h-4 w-4" />
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => handleFileDelete(supplier.id, file.id, file.filename)}
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
        ))}
      </div>
    </div>
  );
}

export default Suppliers;
