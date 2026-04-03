import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { API } from '../App';
import { useTranslation } from 'react-i18next';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Switch } from '../components/ui/switch';
import { Badge } from '../components/ui/badge';
import { Plus, Edit, Trash2, UserCheck, UserX, Key, AlertCircle, Copy, Check } from 'lucide-react';
import { toast } from 'sonner';
import { getErrorMessage } from '../utils/errorHandler';

function UsersTab() {
  const { t } = useTranslation();
  const [users, setUsers] = useState([]);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [editingUser, setEditingUser] = useState(null);
  const [tempPassword, setTempPassword] = useState(null);
  const [copiedPassword, setCopiedPassword] = useState(false);
  const [formData, setFormData] = useState({
    email: '',
    displayName: '',
    roleKey: 'manager',
    locale: 'en-US',
    sendInvite: true
  });
  const [editFormData, setEditFormData] = useState({
    displayName: '',
    roleKey: '',
    locale: '',
    isDisabled: false
  });

  useEffect(() => {
    fetchUsers();
  }, []);

  const fetchUsers = async () => {
    try {
      const response = await axios.get(`${API}/users`);
      setUsers(response.data);
    } catch (error) {
      if (error.response?.status === 403) {
        toast.error(t('users.error.adminOnly') || 'Admin access required');
      } else {
        toast.error(t('users.error.load') || 'Failed to load users');
      }
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    try {
      const response = await axios.post(`${API}/users`, formData);
      
      if (response.data.tempPassword) {
        setTempPassword(response.data.tempPassword);
        toast.success(t('users.success.created') || 'User created successfully');
      } else {
        toast.success(t('users.success.inviteSent') || 'Invite email sent');
        setIsDialogOpen(false);
      }
      
      fetchUsers();
      resetForm();
    } catch (error) {
      toast.error(getErrorMessage(error, t('users.error.create') || 'Failed to create user'));
    }
  };

  const handleEdit = (user) => {
    setEditingUser(user);
    setEditFormData({
      displayName: user.displayName,
      roleKey: user.roleKey,
      locale: user.locale,
      isDisabled: user.isDisabled || false
    });
    setIsEditDialogOpen(true);
  };

  const handleUpdate = async (e) => {
    e.preventDefault();

    try {
      await axios.put(`${API}/users/${editingUser.id}`, editFormData);
      toast.success(t('users.success.updated') || 'User updated successfully');
      fetchUsers();
      setIsEditDialogOpen(false);
      setEditingUser(null);
    } catch (error) {
      toast.error(getErrorMessage(error, t('users.error.update') || 'Failed to update user'));
    }
  };

  const handleDelete = async (userId, userEmail) => {
    if (!window.confirm(t('users.confirm.delete') || `Are you sure you want to disable ${userEmail}?`)) return;

    try {
      await axios.delete(`${API}/users/${userId}`);
      toast.success(t('users.success.deleted') || 'User disabled successfully');
      fetchUsers();
    } catch (error) {
      toast.error(getErrorMessage(error, t('users.error.delete') || 'Failed to disable user'));
    }
  };

  const handleResetPassword = async (userId, userEmail) => {
    if (!window.confirm(t('users.confirm.resetPassword') || `Send password reset email to ${userEmail}?`)) return;

    try {
      await axios.post(`${API}/users/${userId}/reset-password`);
      toast.success(t('users.success.resetPassword') || 'Password reset email sent');
    } catch (error) {
      toast.error(getErrorMessage(error, t('users.error.resetPassword') || 'Failed to send reset email'));
    }
  };

  const handleToggleDisabled = async (userId, currentStatus) => {
    try {
      await axios.put(`${API}/users/${userId}`, { isDisabled: !currentStatus });
      toast.success(!currentStatus ? t('users.success.disabled') : t('users.success.enabled') || 'User status updated');
      fetchUsers();
    } catch (error) {
      toast.error(getErrorMessage(error, t('users.error.update') || 'Failed to update user'));
    }
  };

  const resetForm = () => {
    setFormData({
      email: '',
      displayName: '',
      roleKey: 'manager',
      locale: 'en-US',
      sendInvite: true
    });
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    setCopiedPassword(true);
    setTimeout(() => setCopiedPassword(false), 2000);
    toast.success(t('common.copied') || 'Copied to clipboard');
  };

  const closeTempPasswordDialog = () => {
    setTempPassword(null);
    setIsDialogOpen(false);
    setCopiedPassword(false);
  };

  const getRoleBadge = (roleKey) => {
    const variants = {
      admin: 'bg-purple-100 text-purple-800',
      manager: 'bg-blue-100 text-blue-800',
      waiter: 'bg-green-100 text-green-800'
    };
    return variants[roleKey] || 'bg-gray-100 text-gray-800';
  };

  return (
    <div className="space-y-4">
      <Card className="glass-morphism border-0">
        <CardHeader>
          <div className="flex justify-between items-start">
            <div>
              <CardTitle>{t('users.title') || 'Users & Access'}</CardTitle>
              <CardDescription>{t('users.subtitle') || 'Manage users in your restaurant'}</CardDescription>
            </div>
            <Dialog open={isDialogOpen} onOpenChange={(open) => {
              setIsDialogOpen(open);
              if (!open && !tempPassword) resetForm();
            }}>
              <DialogTrigger asChild>
                <Button data-testid="add-user-btn">
                  <Plus className="h-4 w-4 mr-2" />
                  {t('users.add') || 'Add User'}
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>{t('users.new') || 'New User'}</DialogTitle>
                </DialogHeader>
                
                {tempPassword ? (
                  <div className="space-y-4">
                    <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
                      <div className="flex items-start gap-2">
                        <Check className="h-5 w-5 text-green-600 mt-0.5" />
                        <div className="flex-1">
                          <p className="font-semibold text-green-900">{t('users.userCreated') || 'User created successfully!'}</p>
                          <p className="text-sm text-green-700 mt-1">{t('users.tempPasswordInfo') || 'Share this temporary password with the user:'}</p>
                        </div>
                      </div>
                    </div>
                    
                    <div className="space-y-2">
                      <Label>{t('users.tempPassword') || 'Temporary Password'}</Label>
                      <div className="flex gap-2">
                        <Input value={tempPassword} readOnly className="font-mono" />
                        <Button
                          type="button"
                          size="icon"
                          variant="outline"
                          onClick={() => copyToClipboard(tempPassword)}
                        >
                          {copiedPassword ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                        </Button>
                      </div>
                      <p className="text-xs text-muted-foreground">
                        {t('users.tempPasswordWarning') || 'This password will not be shown again. Make sure to copy it.'}
                      </p>
                    </div>
                    
                    <Button onClick={closeTempPasswordDialog} className="w-full">
                      {t('common.close') || 'Close'}
                    </Button>
                  </div>
                ) : (
                  <form onSubmit={handleSubmit} className="space-y-4">
                    <div>
                      <Label htmlFor="email">{t('users.email') || 'Email'} *</Label>
                      <Input
                        id="email"
                        type="email"
                        value={formData.email}
                        onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                        required
                      />
                    </div>
                    
                    <div>
                      <Label htmlFor="displayName">{t('users.displayName') || 'Display Name'} *</Label>
                      <Input
                        id="displayName"
                        value={formData.displayName}
                        onChange={(e) => setFormData({ ...formData, displayName: e.target.value })}
                        required
                      />
                    </div>
                    
                    <div>
                      <Label>{t('users.role') || 'Role'} *</Label>
                      <Select value={formData.roleKey} onValueChange={(value) => setFormData({ ...formData, roleKey: value })}>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="admin">{t('users.roles.admin') || 'Admin'}</SelectItem>
                          <SelectItem value="manager">{t('users.roles.manager') || 'Manager'}</SelectItem>
                          <SelectItem value="waiter">{t('users.roles.waiter') || 'Staff'}</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    
                    <div>
                      <Label>{t('users.locale') || 'Language'}</Label>
                      <Select value={formData.locale} onValueChange={(value) => setFormData({ ...formData, locale: value })}>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="en-US">English (US)</SelectItem>
                          <SelectItem value="it-IT">Italiano (IT)</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    
                    <div className="flex items-center justify-between p-3 bg-muted/50 rounded-lg">
                      <div>
                        <Label className="font-medium">{t('users.sendInvite') || 'Send Invite Email'}</Label>
                        <p className="text-xs text-muted-foreground">
                          {formData.sendInvite 
                            ? (t('users.sendInviteDesc') || 'User will receive an email to set their password')
                            : (t('users.tempPasswordDesc') || 'Generate a temporary password')}
                        </p>
                      </div>
                      <Switch
                        checked={formData.sendInvite}
                        onCheckedChange={(checked) => setFormData({ ...formData, sendInvite: checked })}
                      />
                    </div>
                    
                    <div className="flex justify-end gap-2 pt-4 border-t">
                      <Button type="button" variant="outline" onClick={() => setIsDialogOpen(false)}>
                        {t('common.cancel') || 'Cancel'}
                      </Button>
                      <Button type="submit">
                        {t('common.create') || 'Create User'}
                      </Button>
                    </div>
                  </form>
                )}
              </DialogContent>
            </Dialog>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {users.map((user) => (
              <Card key={user.id} className={`p-4 ${user.isDisabled ? 'opacity-50' : ''}`}>
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <h4 className="font-semibold">{user.displayName}</h4>
                      <Badge className={getRoleBadge(user.roleKey)}>
                        {t(`users.roles.${user.roleKey}`) || user.roleKey}
                      </Badge>
                      {user.isDisabled && (
                        <Badge variant="outline" className="text-red-600 border-red-600">
                          {t('users.disabled') || 'Disabled'}
                        </Badge>
                      )}
                    </div>
                    <p className="text-sm text-muted-foreground">{user.email}</p>
                    <p className="text-xs text-muted-foreground mt-1">
                      {t('users.locale')}: {user.locale || 'en-US'}
                      {user.lastLoginAt && ` • ${t('users.lastLogin')}: ${new Date(user.lastLoginAt).toLocaleDateString()}`}
                    </p>
                  </div>
                  
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleEdit(user)}
                      data-testid={`edit-user-${user.id}`}
                    >
                      <Edit className="h-4 w-4" />
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleToggleDisabled(user.id, user.isDisabled)}
                      data-testid={`toggle-user-${user.id}`}
                    >
                      {user.isDisabled ? <UserCheck className="h-4 w-4" /> : <UserX className="h-4 w-4" />}
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleResetPassword(user.id, user.email)}
                      data-testid={`reset-password-${user.id}`}
                    >
                      <Key className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </Card>
            ))}
            
            {users.length === 0 && (
              <div className="text-center py-12 text-muted-foreground">
                <AlertCircle className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>{t('users.noData') || 'No users found'}</p>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Edit User Dialog */}
      <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('users.edit') || 'Edit User'}</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleUpdate} className="space-y-4">
            <div>
              <Label htmlFor="edit-displayName">{t('users.displayName') || 'Display Name'}</Label>
              <Input
                id="edit-displayName"
                value={editFormData.displayName}
                onChange={(e) => setEditFormData({ ...editFormData, displayName: e.target.value })}
              />
            </div>
            
            <div>
              <Label>{t('users.role') || 'Role'}</Label>
              <Select value={editFormData.roleKey} onValueChange={(value) => setEditFormData({ ...editFormData, roleKey: value })}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="admin">{t('users.roles.admin') || 'Admin'}</SelectItem>
                  <SelectItem value="manager">{t('users.roles.manager') || 'Manager'}</SelectItem>
                  <SelectItem value="waiter">{t('users.roles.waiter') || 'Staff'}</SelectItem>
                </SelectContent>
              </Select>
            </div>
            
            <div>
              <Label>{t('users.locale') || 'Language'}</Label>
              <Select value={editFormData.locale} onValueChange={(value) => setEditFormData({ ...editFormData, locale: value })}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="en-US">English (US)</SelectItem>
                  <SelectItem value="it-IT">Italiano (IT)</SelectItem>
                </SelectContent>
              </Select>
            </div>
            
            <div className="flex justify-end gap-2 pt-4 border-t">
              <Button type="button" variant="outline" onClick={() => setIsEditDialogOpen(false)}>
                {t('common.cancel') || 'Cancel'}
              </Button>
              <Button type="submit">
                {t('common.update') || 'Update'}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}

export default UsersTab;
