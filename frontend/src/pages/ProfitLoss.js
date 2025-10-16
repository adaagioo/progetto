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
import { Textarea } from '../components/ui/textarea';
import { Plus, Trash2, TrendingUp } from 'lucide-react';
import { toast } from 'sonner';

function ProfitLoss() {
  const { t } = useTranslation();
  const { user } = useContext(AuthContext);
  const { format } = useCurrency();
  const [plRecords, setPlRecords] = useState([]);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [formData, setFormData] = useState({
    month: '',
    revenue: '',
    cogs: '',
    grossMargin: '',
    notes: ''
  });

  useEffect(() => {
    fetchPL();
  }, []);

  const fetchPL = async () => {
    try {
      const response = await axios.get(`${API}/pl`);
      setPlRecords(response.data);
    } catch (error) {
      toast.error('Failed to load P&L records');
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    try {
      await axios.post(`${API}/pl`, formData);
      toast.success('P&L record created');
      fetchPL();
      resetForm();
      setIsDialogOpen(false);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to save P&L');
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Are you sure you want to delete this P&L record?')) return;

    try {
      await axios.delete(`${API}/pl/${id}`);
      toast.success('P&L record deleted');
      fetchPL();
    } catch (error) {
      toast.error('Failed to delete P&L record');
    }
  };

  const resetForm = () => {
    setFormData({
      month: '',
      revenue: '',
      cogs: '',
      grossMargin: '',
      notes: ''
    });
  };

  return (
    <div className="space-y-6" data-testid="pl-page">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold gradient-text mb-2">
            Profit & Loss
          </h1>
          <p className="text-base text-gray-600">{t('pl.subtitle')}</p>
        </div>

        {user?.role === 'admin' && (
          <Dialog open={isDialogOpen} onOpenChange={(open) => {
            setIsDialogOpen(open);
            if (!open) resetForm();
          }}>
            <DialogTrigger asChild>
              <Button className="btn-primary text-white" data-testid="add-pl-button">
                <Plus className="w-4 h-4 mr-2" />
                Add P&L Snapshot
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-md max-h-[90vh] overflow-y-auto" data-testid="pl-dialog">
              <DialogHeader>
                <DialogTitle>New P&L Snapshot</DialogTitle>
              </DialogHeader>
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="month">Month (YYYY-MM) *</Label>
                  <Input
                    id="month"
                    type="month"
                    value={formData.month}
                    onChange={(e) => setFormData({ ...formData, month: e.target.value })}
                    required
                    data-testid="pl-month-input"
                    className="input-focus"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="revenue">Revenue ($) *</Label>
                  <Input
                    id="revenue"
                    type="number"
                    step="0.01"
                    value={formData.revenue}
                    onChange={(e) => {
                      const rev = parseFloat(e.target.value) || 0;
                      const cogs = parseFloat(formData.cogs) || 0;
                      setFormData({ 
                        ...formData, 
                        revenue: e.target.value,
                        grossMargin: (rev - cogs).toFixed(2)
                      });
                    }}
                    required
                    data-testid="pl-revenue-input"
                    className="input-focus"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="cogs">COGS ($) *</Label>
                  <Input
                    id="cogs"
                    type="number"
                    step="0.01"
                    value={formData.cogs}
                    onChange={(e) => {
                      const cogs = parseFloat(e.target.value) || 0;
                      const rev = parseFloat(formData.revenue) || 0;
                      setFormData({ 
                        ...formData, 
                        cogs: e.target.value,
                        grossMargin: (rev - cogs).toFixed(2)
                      });
                    }}
                    required
                    data-testid="pl-cogs-input"
                    className="input-focus"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="grossMargin">Gross Margin ($)</Label>
                  <Input
                    id="grossMargin"
                    type="number"
                    step="0.01"
                    value={formData.grossMargin}
                    readOnly
                    data-testid="pl-margin-display"
                    className="bg-gray-50"
                  />
                  <p className="text-xs text-gray-500">Auto-calculated: Revenue - COGS</p>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="notes">Notes</Label>
                  <Textarea
                    id="notes"
                    value={formData.notes}
                    onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                    placeholder="Additional notes about this month"
                    data-testid="pl-notes-input"
                    className="input-focus"
                    rows={3}
                  />
                </div>

                <Button type="submit" className="w-full btn-primary text-white" data-testid="save-pl-button">
                  Create Snapshot
                </Button>
              </form>
            </DialogContent>
          </Dialog>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {plRecords.map((pl) => {
          const marginPct = pl.revenue > 0 ? (pl.grossMargin / pl.revenue * 100) : 0;
          const isPositive = pl.grossMargin > 0;

          return (
            <Card key={pl.id} className="glass-morphism border-0 card-hover" data-testid="pl-card">
              <CardHeader>
                <CardTitle className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <TrendingUp className={`w-5 h-5 ${isPositive ? 'text-emerald-500' : 'text-red-500'}`} />
                    <span className="text-lg">{pl.month}</span>
                  </div>
                  {user?.role === 'admin' && (
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => handleDelete(pl.id)}
                      data-testid="delete-pl-button"
                    >
                      <Trash2 className="w-4 h-4 text-red-500" />
                    </Button>
                  )}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-gray-600">Revenue:</span>
                  <span className="text-lg font-semibold text-emerald-600">{format.number(pl.revenue)}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-600">COGS:</span>
                  <span className="text-lg font-semibold text-orange-600">{format.number(pl.cogs)}</span>
                </div>
                <div className="pt-3 border-t">
                  <div className="flex justify-between items-center mb-2">
                    <span className="font-semibold">Gross Margin:</span>
                    <span className={`text-xl font-bold ${isPositive ? 'text-emerald-600' : 'text-red-600'}`}>
                      {format.number(pl.grossMargin)}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-600">Margin %:</span>
                    <span className={`text-sm font-semibold ${isPositive ? 'text-emerald-600' : 'text-red-600'}`}>
                      {marginPct.toFixed(1)}%
                    </span>
                  </div>
                </div>
                {pl.notes && (
                  <div className="pt-2 border-t">
                    <p className="text-xs text-gray-600">{pl.notes}</p>
                  </div>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>

      {plRecords.length === 0 && (
        <Card className="glass-morphism border-0">
          <CardContent className="flex flex-col items-center justify-center py-12">
            <p className="text-gray-500 mb-4">{`${t('pl.noData')}`}</p>
            {user?.role === 'admin' && (
              <Button className="btn-primary text-white" onClick={() => setIsDialogOpen(true)}>
                <Plus className="w-4 h-4 mr-2" />
                Add Your First Snapshot
              </Button>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

export default ProfitLoss;